"""MOCK diagnostic scenarios: no model downloads, API calls, or real QA edits."""

from __future__ import annotations

from dataclasses import replace

import pytest

from eval.metrics import QAItem
from ragkit.contracts import Chunk, Document, RetrievedChunk


def question(qid="Q1", quote="gold evidence", category="answerable"):
    return QAItem(
        qid, "Where is the evidence?", "gold", "doc" if quote else "", quote, category, ""
    )


def source(text="prefix gold evidence suffix"):
    return Document("doc", "MOCK source", text, "https://example.test/doc", "TEST")


def piece(doc, start=0, end=None, index=0):
    end = len(doc.text) if end is None else end
    return Chunk(
        f"doc#{index:04d}",
        doc.doc_id,
        doc.text[start:end],
        start,
        end,
        "fixed",
        index,
        doc.title,
        doc.source_uri,
        doc.license,
        {"chunk_size": 600, "chunk_overlap": 80, "chunk_overlap_actual": 0},
    )


class RecordedStore:
    """MOCK already-ranked retrieval, including independent roundtrip faults."""

    def __init__(self, chunks, scores=None):
        self.chunks = {c.chunk_id: c for c in chunks}
        self.hits = [
            RetrievedChunk(c, s, i + 1)
            for i, (c, s) in enumerate(zip(chunks, scores or [0.8] * len(chunks), strict=True))
        ]

    def count(self):
        return len(self.hits)

    def search(self, query_vector, k):
        return self.hits[: max(0, k)]

    def get_chunk(self, chunk_id):
        return self.chunks.get(chunk_id)

    def upsert(self, chunks, vectors):
        raise AssertionError("diagnostic must not write to the store")


class RecordedEmbedder:
    name = "MOCK-recorded"
    dimension = 2

    def __init__(self):
        self.calls = []

    def embed(self, texts):
        self.calls.append(list(texts))
        return [[1.0, 0.0] for _ in texts]


def test_diagnostic_records_gold_rank_beyond_top_k_and_roundtrip():
    from eval.retrieval_diagnostics import diagnose_retrieval

    doc = source()
    gold = piece(doc)
    distractor = replace(
        gold, chunk_id="other#0000", doc_id="other", text="other", char_start=0, char_end=5
    )
    store = RecordedStore([distractor, gold], [0.9, 0.7])
    other_doc = Document("other", gold.title, "other", gold.source_uri, gold.license)
    report = diagnose_retrieval(
        [question()],
        [doc, other_doc],
        [gold, distractor],
        RecordedEmbedder(),
        store,
        strategy="fixed",
        collection="chunks_fixed",
        top_k=1,
    )
    row = report["items"][0]
    assert row["diagnosis"] == "ranking_below_top_k"
    assert row["first_evidence_rank"] == 2
    assert row["gold"]["char_start"] == 7
    assert row["top_k_hit"] is False
    assert row["retrieved"][0]["score"] == 0.9
    assert row["retrieved"][0]["roundtrip"]["ok"] is True
    assert report["index_audit"]["unexpected_count"] == 0
    assert "hit@1" not in report and "hit@3" not in report


def test_unanswerable_is_not_scored_as_a_retrieval_failure():
    from eval.retrieval_diagnostics import diagnose_retrieval

    doc = source()
    chunk = piece(doc)
    report = diagnose_retrieval(
        [question(quote="", category="unanswerable")],
        [doc],
        [chunk],
        RecordedEmbedder(),
        RecordedStore([chunk]),
        strategy="fixed",
        collection="chunks_fixed",
    )
    row = report["items"][0]
    assert row["diagnosis"] == "unanswerable_label"
    assert row["gold"] is None and row["top_k_hit"] is None
    assert row["label_review"] == "pending_human_review"
    assert row["retrieved"]  # Nearest neighbours do not prove answerability.


@pytest.mark.parametrize("missing", [False, True])
def test_boundary_failure_requires_verified_complete_index(missing):
    from eval.retrieval_diagnostics import diagnose_retrieval

    doc = source("abcdefghijkl")
    chunks = [piece(doc, start, start + 4, i) for i, start in enumerate([0, 4, 8])]
    actual = chunks[:-1] if missing else chunks
    report = diagnose_retrieval(
        [question(quote=doc.text)],
        [doc],
        chunks,
        RecordedEmbedder(),
        RecordedStore(actual),
        strategy="fixed",
        collection="chunks_fixed",
        top_k=1,
    )
    row = report["items"][0]
    assert row["diagnosis"] == (
        "index_incomplete_or_mismatched" if missing else "chunk_boundary_fragmentation"
    )
    assert row["first_evidence_rank"] is None
    assert row["max_index_coverage"] == pytest.approx(1 / 3)
    assert row["gold_union_coverage"] == pytest.approx(2 / 3 if missing else 1.0)
    assert row["top_k_hit"] is False


@pytest.mark.parametrize("fault", ["roundtrip", "source_text", "source_uri"])
def test_diagnostic_reports_untrusted_provenance_instead_of_a_valid_hit(fault):
    from eval.retrieval_diagnostics import diagnose_retrieval

    doc = source()
    chunk = piece(doc)
    store = RecordedStore([chunk])
    if fault == "roundtrip":
        store.chunks[chunk.chunk_id] = replace(chunk, license="tampered")
    elif fault == "source_text":
        chunk = replace(chunk, text="x" * len(chunk.text))
        store = RecordedStore([chunk])
    else:
        chunk = replace(chunk, source_uri="https://example.test/wrong")
        store = RecordedStore([chunk])
    report = diagnose_retrieval(
        [question()],
        [doc],
        [chunk],
        RecordedEmbedder(),
        store,
        strategy="fixed",
        collection="chunks_fixed",
    )
    row = report["items"][0]
    assert row["diagnosis"] == "roundtrip_or_provenance_error"
    assert row["top_k_hit"] is None
    assert row["retrieved"][0]["roundtrip"]["ok"] is (fault != "roundtrip")
    assert bool(row["retrieved"][0]["source_problems"]) is (fault != "roundtrip")


def test_unlocated_gold_stays_unknown_not_corpus_absence():
    from eval.retrieval_diagnostics import diagnose_retrieval

    doc = source()
    chunk = piece(doc)
    report = diagnose_retrieval(
        [question(quote="not in source")],
        [doc],
        [chunk],
        RecordedEmbedder(),
        RecordedStore([chunk]),
        strategy="fixed",
        collection="chunks_fixed",
    )
    row = report["items"][0]
    assert row["diagnosis"] == "unknown_gold_unlocated"
    assert row["gold"] is None and row["top_k_hit"] is None
    assert "not verbatim" in row["gold_error"]


def test_empty_items_does_not_invoke_embedding():
    from eval.retrieval_diagnostics import diagnose_retrieval

    embedder = RecordedEmbedder()
    report = diagnose_retrieval(
        [], [], [], embedder, RecordedStore([]), strategy="fixed", collection="chunks_fixed"
    )
    assert report["items"] == []
    assert embedder.calls == []


@pytest.mark.parametrize(
    "options",
    [
        {"top_k": -1},
        {"top_k": True},
        {"top_k": 1.5},
        {"min_coverage": 0},
        {"min_coverage": float("nan")},
        {"min_coverage": 1.1},
    ],
)
def test_invalid_options_fail_even_on_empty_input(options):
    from eval.retrieval_diagnostics import diagnose_retrieval

    with pytest.raises(ValueError):
        diagnose_retrieval(
            [],
            [],
            [],
            RecordedEmbedder(),
            RecordedStore([]),
            strategy="fixed",
            collection="chunks_fixed",
            **options,
        )


def test_top_k_zero_and_empty_index_have_unambiguous_behavior():
    from eval.retrieval_diagnostics import diagnose_retrieval

    doc = source()
    chunk = piece(doc)
    common = dict(strategy="fixed", collection="chunks_fixed")
    report = diagnose_retrieval(
        [question()], [doc], [chunk], RecordedEmbedder(), RecordedStore([chunk]), top_k=0, **common
    )
    assert report["items"][0]["retrieved"] == []
    assert report["items"][0]["first_evidence_rank"] == 1
    empty = diagnose_retrieval(
        [question()], [doc], [chunk], RecordedEmbedder(), RecordedStore([]), **common
    )
    assert empty["items"][0]["diagnosis"] == "index_incomplete_or_mismatched"


def test_score_distribution_retains_negative_values_and_empty_semantics():
    from eval.retrieval_diagnostics import score_distribution

    summary = score_distribution([-1.0, 0.0, 1.0])
    assert summary["n"] == 3
    assert (summary["min"], summary["max"], summary["mean"], summary["median"]) == (-1, 1, 0, 0)
    assert sum(bin_["count"] for bin_ in summary["histogram"]) == 3
    empty = score_distribution([])
    assert empty["n"] == 0 and empty["mean"] is None
    assert empty["min"] is None and empty["max"] is None
    with pytest.raises(ValueError, match="finite"):
        score_distribution([float("nan")])


@pytest.mark.parametrize("invalid", ["qid", "doc_id", "chunk_id", "category", "question"])
def test_importable_diagnostic_rejects_ambiguous_inputs_before_search(invalid):
    from eval.retrieval_diagnostics import diagnose_retrieval

    doc = source()
    chunk = piece(doc)
    items, documents, chunks = [question()], [doc], [chunk]
    if invalid == "qid":
        items *= 2
    elif invalid == "doc_id":
        documents *= 2
    elif invalid == "chunk_id":
        chunks *= 2
    elif invalid == "category":
        items = [replace(question(), category="unverified")]
    else:
        items = [replace(question(), question="  ")]
    embedder = RecordedEmbedder()
    with pytest.raises(ValueError):
        diagnose_retrieval(
            items,
            documents,
            chunks,
            embedder,
            RecordedStore([chunk]),
            strategy="fixed",
            collection="chunks_fixed",
        )
    assert embedder.calls == []


@pytest.mark.parametrize("edge_index", range(11))
def test_histogram_decimal_edges_follow_documented_left_closed_bins(edge_index):
    import math

    from eval.retrieval_diagnostics import score_distribution

    edge = (edge_index - 5) / 5
    expected = min(edge_index, 9)
    result = score_distribution([edge])
    assert result["histogram"][expected]["count"] == 1
    assert sum(b["count"] for b in result["histogram"]) == 1
    if 0 < edge_index < 10:
        below = score_distribution([math.nextafter(edge, -math.inf)])
        assert below["histogram"][edge_index - 1]["count"] == 1


def test_cli_writes_reproducible_snapshots_csv_and_svg_without_network(tmp_path, monkeypatch):
    import csv
    import hashlib
    import json
    from xml.etree import ElementTree

    from eval import retrieval_diagnostics as mod
    from ragkit.config import load_settings

    doc = source()
    chunk = piece(doc)
    (tmp_path / "doc.txt").write_text(doc.text)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            [
                dict(
                    doc_id=doc.doc_id,
                    title=doc.title,
                    path="doc.txt",
                    source_uri=doc.source_uri,
                    license=doc.license,
                )
            ]
        )
    )
    qa = tmp_path / "qa.csv"
    item = question()
    with qa.open("w", newline="") as f:
        from dataclasses import asdict

        writer = csv.DictWriter(f, fieldnames=list(asdict(item)))
        writer.writeheader()
        writer.writerow(asdict(item))
    settings = replace(load_settings(), manifest=manifest, index_dir=tmp_path / "index")
    monkeypatch.setattr(mod, "load_settings", lambda _: settings)
    monkeypatch.setattr(mod, "build_store", lambda _: RecordedStore([chunk]))
    embedder = RecordedEmbedder()
    monkeypatch.setattr(mod, "build_embedder", lambda _: embedder)
    out = tmp_path / "out"
    argv = ["--qa", str(qa), "--output-dir", str(out)]
    assert mod.main(argv) == 0
    report = json.loads((out / "diagnostics.json").read_text())
    assert report["data_status"] == "DEVELOPMENT"
    assert report["execution"] == "MOCK"
    assert report["provenance"]["qa_sha256"] == hashlib.sha256(qa.read_bytes()).hexdigest()
    assert len(report["provenance"]["corpus_snapshot_sha256"]) == 64
    assert "eval.retrieval_diagnostics" in report["command"]
    assert report["items"][0]["diagnosis"] == "hit"
    with (out / "retrieved.csv").open() as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1 and rows[0]["chunk_id"] == chunk.chunk_id
    assert report["score_distributions"]["all_top_k"]["n"] == 1
    ElementTree.parse(out / "score_histogram.svg")
    assert "DEVELOPMENT" in (out / "run.md").read_text()
    assert mod.main(argv) == 2  # Never overwrite another run silently.
    assert len(embedder.calls) == 1  # Refuse before repeating model work.


def test_cli_refuses_api_config_before_building_any_client(tmp_path, monkeypatch, capsys):
    from eval import retrieval_diagnostics as mod
    from ragkit.config import load_settings

    monkeypatch.setattr(
        mod, "load_settings", lambda _: replace(load_settings(), embedding_provider="api")
    )

    def forbidden(_):
        raise AssertionError("an embedding or store client must not be created")

    monkeypatch.setattr(mod, "build_embedder", forbidden)
    monkeypatch.setattr(mod, "build_store", forbidden)
    assert mod.main(["--output-dir", str(tmp_path)]) == 2
    assert "only permits local" in capsys.readouterr().err


def test_partial_search_cannot_be_claimed_as_a_complete_deep_ranking():
    from eval.retrieval_diagnostics import diagnose_retrieval

    doc = source()
    gold = piece(doc)
    other_doc = Document("other", gold.title, "other", gold.source_uri, gold.license)
    other = replace(
        gold, chunk_id="other#0000", doc_id="other", text="other", char_start=0, char_end=5
    )
    store = RecordedStore([other, gold])
    store.hits = store.hits[:1]
    store.count = lambda: 2
    report = diagnose_retrieval(
        [question()],
        [doc, other_doc],
        [gold, other],
        RecordedEmbedder(),
        store,
        strategy="fixed",
        collection="chunks_fixed",
        top_k=1,
    )
    row = report["items"][0]
    assert row["diagnosis"] == "unknown_needs_review"
    assert row["searched_count"] == 1
    assert row["ranking_complete"] is False
    assert row["first_evidence_rank"] is None


def test_help_does_not_build_models_and_diagnostics_defines_no_metrics(monkeypatch, capsys):
    import ast
    from pathlib import Path

    from eval import retrieval_diagnostics as mod

    monkeypatch.setattr(mod, "load_settings", lambda _: pytest.fail("help must not load config"))
    with pytest.raises(SystemExit) as exc:
        mod.main(["--help"])
    assert exc.value.code == 0
    assert "--min-coverage" in capsys.readouterr().out
    names = {
        node.name
        for node in ast.walk(ast.parse(Path(mod.__file__).read_text()))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert not names.intersection(
        {"retrieval_hit_rate", "answer_correctness", "abstention_rates", "citation_structure_rate"}
    )

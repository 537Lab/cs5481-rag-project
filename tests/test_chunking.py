"""M2 tests. The verbatim-slice invariant is the foundation of verifiable citations."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from eval.chunking_experiment import (
    DEVELOPMENT_LABEL,
    build_payload,
    compare_retrieval,
    development_note,
    length_stats,
    main,
    resolve_destination,
    settings_for_strategy,
    write_result,
)
from eval.evidence import locate_evidence
from eval.metrics import DEFAULT_QA, SUMMARY_DIR, QAItem, QASetError, load_qa, retrieval_hit_rate
from ragkit.chunking import (
    ChunkConfig,
    FixedSizeChunker,
    ParagraphChunker,
    build_chunker,
)
from ragkit.config import ROOT, load_settings
from ragkit.contracts import Chunk, Document, RetrievedChunk
from ragkit.loaders import load_documents


@pytest.fixture
def real_doc() -> Document:
    return load_documents(ROOT / "data" / "raw" / "manifest.json")[0]


@pytest.mark.parametrize("chunker_class", [FixedSizeChunker, ParagraphChunker])
def test_every_chunk_is_a_verbatim_slice_of_the_source(real_doc, chunker_class):
    chunks = chunker_class(ChunkConfig(size=400, overlap=50)).split(real_doc)
    assert chunks
    for chunk in chunks:
        assert real_doc.text[chunk.char_start : chunk.char_end] == chunk.text
        assert chunk.text.strip()
        assert chunk.title == real_doc.title
        assert chunk.source_uri == real_doc.source_uri


@pytest.mark.parametrize("chunker_class", [FixedSizeChunker, ParagraphChunker])
def test_chunk_ids_are_unique_stable_and_ordered(real_doc, chunker_class):
    chunker = chunker_class(ChunkConfig(size=400, overlap=50))
    first = chunker.split(real_doc)
    second = chunker.split(real_doc)
    ids = [chunk.chunk_id for chunk in first]
    assert ids == [chunk.chunk_id for chunk in second], "chunking must be deterministic"
    assert len(ids) == len(set(ids))
    assert [chunk.index for chunk in first] == list(range(len(first)))
    assert all(chunk.chunk_id.startswith(f"{real_doc.doc_id}#") for chunk in first)


def test_overlap_yields_more_chunks_than_no_overlap(real_doc):
    no_overlap = FixedSizeChunker(ChunkConfig(size=400, overlap=0)).split(real_doc)
    with_overlap = FixedSizeChunker(ChunkConfig(size=400, overlap=120)).split(real_doc)
    assert len(with_overlap) > len(no_overlap)


def test_two_strategies_are_actually_different(real_doc):
    fixed = FixedSizeChunker(ChunkConfig(size=400, overlap=50)).split(real_doc)
    paragraph = ParagraphChunker(ChunkConfig(size=400, overlap=50)).split(real_doc)
    assert [c.char_start for c in fixed] != [c.char_start for c in paragraph]
    assert {c.strategy for c in fixed} == {"fixed"}
    assert {c.strategy for c in paragraph} == {"paragraph"}


def test_oversized_paragraph_is_still_split():
    doc = Document(doc_id="long", title="Long", text="word " * 500)
    chunks = ParagraphChunker(ChunkConfig(size=200, overlap=0)).split(doc)
    assert len(chunks) > 1
    assert all(len(chunk.text) <= 200 for chunk in chunks)
    assert all(doc.text[c.char_start : c.char_end] == c.text for c in chunks)


@pytest.mark.parametrize("chunker_class", [FixedSizeChunker, ParagraphChunker])
def test_empty_document_produces_no_chunks(chunker_class):
    doc = Document(doc_id="empty", title="Empty", text="  \n ")
    assert chunker_class().split(doc) == []


@pytest.fixture
def paragraphs_doc() -> Document:
    body = "The alpha service listens on port 8080. " + ("word " * 60)
    text = "\n\n".join(f"P{i}. {body}" for i in range(8))
    return Document(doc_id="paras", title="Paragraphs", text=text)


@pytest.mark.parametrize("chunker_class", [FixedSizeChunker, ParagraphChunker])
def test_overlap_is_really_applied_and_metadata_is_truthful(
    paragraphs_doc, chunker_class
):
    """Regression: ParagraphChunker used to ignore overlap but claim it in meta."""
    config = ChunkConfig(size=400, overlap=80)
    chunks = chunker_class(config).split(paragraphs_doc)
    assert len(chunks) >= 3
    for previous, current in zip(chunks, chunks[1:], strict=False):
        actual = previous.char_end - current.char_start
        assert actual == config.overlap, f"{chunker_class.name}: wrong real overlap"
        assert current.meta["chunk_overlap"] == config.overlap
        assert current.meta["chunk_overlap_actual"] == actual
        assert current.char_start > previous.char_start
        assert paragraphs_doc.text[current.char_start : current.char_end] == current.text


def test_paragraph_overlap_is_no_longer_a_no_op(paragraphs_doc):
    without = ParagraphChunker(ChunkConfig(size=400, overlap=0)).split(paragraphs_doc)
    with_overlap = ParagraphChunker(ChunkConfig(size=400, overlap=80)).split(paragraphs_doc)
    assert len(with_overlap) == len(without)
    assert [c.char_start for c in with_overlap] != [c.char_start for c in without]
    assert all(c.meta["chunk_overlap_actual"] == 0 for c in without[1:])
    assert all(c.meta["chunk_overlap_actual"] == 80 for c in with_overlap[1:])
    assert all(c.char_start >= 0 and c.char_end <= len(paragraphs_doc.text)
               for c in with_overlap)


def test_invalid_config_is_rejected():
    with pytest.raises(ValueError):
        ChunkConfig(size=0)
    with pytest.raises(ValueError):
        ChunkConfig(size=100, overlap=100)


def test_build_chunker_factory():
    assert isinstance(build_chunker("fixed"), FixedSizeChunker)
    assert isinstance(build_chunker("paragraph"), ParagraphChunker)
    with pytest.raises(ValueError, match="unknown chunking strategy"):
        build_chunker("magic")


def test_length_stats_match_the_chunks():
    doc = Document(doc_id="stats", title="Stats", text="word " * 80)
    chunks = FixedSizeChunker(ChunkConfig(size=50, overlap=0)).split(doc)
    stats = length_stats(chunks)
    lengths = [len(chunk.text) for chunk in chunks]
    assert stats == {
        "chunk_count": len(chunks),
        "length_min": min(lengths),
        "length_max": max(lengths),
        "length_mean": round(sum(lengths) / len(lengths), 4),
    }


def test_both_strategies_share_size_overlap_and_top_k():
    base = load_settings()
    fixed = settings_for_strategy(base, "fixed", size=400, overlap=40, top_k=3)
    paragraph = settings_for_strategy(base, "paragraph", size=400, overlap=40, top_k=3)
    assert fixed.chunk_size == paragraph.chunk_size == 400
    assert fixed.chunk_overlap == paragraph.chunk_overlap == 40
    assert fixed.top_k == paragraph.top_k == 3
    assert fixed.embedding_provider == paragraph.embedding_provider
    assert fixed.collection_name == "chunks_fixed"
    assert paragraph.collection_name == "chunks_paragraph"


def _slice(doc: Document, start: int, end: int, strategy: str, index: int) -> Chunk:
    return Chunk(
        chunk_id=f"{doc.doc_id}#{index:04d}",
        doc_id=doc.doc_id,
        text=doc.text[start:end],
        char_start=start,
        char_end=end,
        strategy=strategy,
        index=index,
        title=doc.title,
    )


def _hit(chunk: Chunk, score: float, rank: int) -> RetrievedChunk:
    return RetrievedChunk(chunk=chunk, score=score, rank=rank)


def test_comparison_copies_hit_rates_and_reports_disagreement():
    text = "The alpha service listens on port 8080. The beta service does not."
    doc = Document(doc_id="svc", title="Svc", text=text)
    alpha = "The alpha service listens on port 8080."
    beta = "The beta service does not."
    spans = {
        "Q1": locate_evidence([doc], "svc", alpha),
        "Q2": locate_evidence([doc], "svc", beta),
    }
    items = [
        QAItem("Q1", "Which port does alpha use?", "8080", "svc", alpha, "answerable", ""),
        QAItem("Q2", "What does the beta sentence say?", "does not", "svc", beta, "answerable", ""),
    ]
    alpha_end = len(alpha)
    beta_start = text.index(beta)
    cover_alpha = _slice(doc, 0, alpha_end, "fixed", 0)
    cover_beta = _slice(doc, beta_start, len(text), "fixed", 1)
    miss = _slice(doc, beta_start, len(text), "paragraph", 0)
    hits = {
        "fixed": {
            "Q1": [_hit(cover_alpha, 0.9, 1)],
            "Q2": [_hit(cover_beta, 0.8, 1)],
        },
        "paragraph": {
            "Q1": [_hit(miss, 0.7, 1), _hit(miss, 0.6, 2), _hit(miss, 0.5, 3)],
            "Q2": [_hit(cover_beta, 0.9, 1)],
        },
    }
    stats = {
        "fixed": {"chunk_count": 2, "length_min": 10, "length_max": 20, "length_mean": 15.0},
        "paragraph": {"chunk_count": 4, "length_min": 8, "length_max": 30, "length_mean": 16.0},
    }
    min_coverage = 0.5
    comparison = compare_retrieval(
        items, spans, hits, stats, hit_levels=(1, 3), min_coverage=min_coverage
    )
    by_strategy = {row["strategy"]: row for row in comparison["strategies"]}
    for strategy, retrieved in hits.items():
        direct = retrieval_hit_rate(
            items, spans, retrieved, hit_levels=(1, 3), min_coverage=min_coverage
        )
        assert by_strategy[strategy]["hit@1"] == direct["rates"]["hit@1"]
        assert by_strategy[strategy]["hit@3"] == direct["rates"]["hit@3"]
        assert by_strategy[strategy]["chunk_count"] == stats[strategy]["chunk_count"]
    assert comparison["min_coverage"] == min_coverage
    assert by_strategy["fixed"]["hit@1"] == {"hits": 2, "n": 2, "rate": 1.0}
    assert by_strategy["paragraph"]["hit@1"] == {"hits": 1, "n": 2, "rate": 0.5}
    cases = [case for case in comparison["disagreements"] if case["qid"] == "Q1"]
    assert {case["level"] for case in cases} == {"hit@1", "hit@3"}
    assert all(case["by_strategy"]["fixed"]["hit"] for case in cases)
    assert all(not case["by_strategy"]["paragraph"]["hit"] for case in cases)
    assert cases[0]["gold_span"] == [spans["Q1"].char_start, spans["Q1"].char_end]


def test_help_exits_zero():
    with pytest.raises(SystemExit) as caught:
        main(["--help"])
    assert caught.value.code == 0


def test_development_destination_does_not_create_summary(tmp_path):
    summary = tmp_path / "summary" / "chunking_comparison"
    raw = tmp_path / "raw" / "chunking_comparison"
    destination = resolve_destination(
        formal=False,
        settings=load_settings(),
        items=load_qa(),
        summary_dir=summary,
        raw_dir=raw,
    )
    assert destination == raw
    assert raw.is_dir()
    assert not summary.exists()


def test_formal_creates_summary_after_review_gate_opens(tmp_path):
    summary = tmp_path / "summary" / "chunking_comparison"
    raw = tmp_path / "raw"
    destination = resolve_destination(
        formal=True,
        settings=load_settings(),
        items=load_qa(),
        summary_dir=summary,
        raw_dir=raw,
    )
    assert destination == summary
    assert summary.is_dir()
    assert not raw.exists()


def test_summary_dir_without_formal_is_refused(tmp_path):
    summary = tmp_path / "summary" / "chunking_comparison"
    assert main(["--summary-dir", str(summary)]) == 2
    assert not summary.exists()


def test_development_writer_does_not_emit_a_summary_bundle(tmp_path):
    payload = {
        "label": DEVELOPMENT_LABEL,
        "formal": False,
        "note": "开发用",
        "generated_at": "2026-11-17T00:00:00+00:00",
        "command": "python -m eval.chunking_experiment",
        "shared": {},
        "configs": {},
        "strategies": [],
        "disagreements": [],
        "judge": "not applicable",
    }
    written = write_result(payload, tmp_path / "raw" / "chunking_comparison", formal=False)
    assert [path.name for path in written] == ["comparison.json"]
    assert not (tmp_path / "summary").exists()
    with pytest.raises(QASetError, match="non-formal"):
        write_result(payload, tmp_path / "summary" / "chunking_comparison", formal=True)
    assert not (tmp_path / "summary").exists()


def test_development_note_follows_the_corpus_snapshot():
    frozen = development_note(
        {
            "corpus_ref": "cs5481-k8s-v135-16docs-36fd3eedf33f@bddfe3601885",
            "corpus_frozen": True,
            "qa_set_status": "development set",
        }
    )
    assert "cs5481-k8s-v135-16docs-36fd3eedf33f@bddfe3601885 is frozen" in frozen
    assert "Not a formal experiment result" in frozen
    unfrozen = development_note(
        {"corpus_ref": "data/raw/manifest.json@abc", "corpus_frozen": False, "qa_set_status": "dev"}
    )
    assert "data/raw/manifest.json@abc is not frozen" in unfrozen


def test_payload_rejects_strategies_that_do_not_share_parameters():
    comparison = {"strategies": [], "disagreements": []}
    configs = {
        "fixed": {"size": 400, "overlap": 40, "top_k": 3, "min_coverage": 0.5,
                  "embedding": "local:all-MiniLM-L6-v2", "qa_set_ref": "qa@abc"},
        "paragraph": {"size": 200, "overlap": 40, "top_k": 3, "min_coverage": 0.5,
                      "embedding": "local:all-MiniLM-L6-v2", "qa_set_ref": "qa@abc"},
    }
    with pytest.raises(QASetError, match="size"):
        build_payload(
            comparison,
            configs,
            command="python -m eval.chunking_experiment",
            formal=False,
        )


def test_development_out_cannot_land_inside_summary():
    relative = Path("eval") / "results" / "summary" / "chunking_comparison"
    nested = Path("eval") / "results" / "raw" / ".." / "summary" / "chunking_comparison"
    published = ROOT / "eval" / "results" / "summary" / "chunking_comparison"
    for target in (relative, nested, SUMMARY_DIR / "chunking_comparison"):
        before = _snapshot(published)
        with pytest.raises(QASetError, match="cannot write a development run"):
            resolve_destination(
                formal=False,
                settings=load_settings(),
                items=load_qa(),
                summary_dir=SUMMARY_DIR / "chunking_comparison",
                raw_dir=target,
            )
        assert _snapshot(published) == before
    before = _snapshot(published)
    assert main(["--out", str(relative)]) == 2
    assert _snapshot(published) == before


def test_development_out_rejects_a_symlink_into_summary(tmp_path):
    link = tmp_path / "summary-link"
    try:
        link.symlink_to(SUMMARY_DIR, target_is_directory=True)
    except OSError:
        import subprocess

        created = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(SUMMARY_DIR)],
            capture_output=True,
            text=True,
            check=False,
        )
        if created.returncode != 0:
            pytest.skip("this machine does not allow the test to create a symlink")
    with pytest.raises(QASetError, match="cannot write a development run"):
        resolve_destination(
            formal=False,
            settings=load_settings(),
            items=load_qa(),
            summary_dir=SUMMARY_DIR / "chunking_comparison",
            raw_dir=link,
        )


def _snapshot(directory: Path) -> list[tuple[str, bytes]]:
    if not directory.exists():
        return []
    return sorted(
        (path.relative_to(directory).as_posix(), path.read_bytes())
        for path in directory.rglob("*")
        if path.is_file()
    )


def test_formal_rejects_dev_and_arbitrary_qa_paths(tmp_path):
    summary = tmp_path / "summary" / "chunking_comparison"
    body = DEFAULT_QA.read_text(encoding="utf-8")
    for name in ("qa_set_dev_v0.csv", "arbitrary_questions.csv"):
        qa_file = tmp_path / name
        qa_file.write_text(body, encoding="utf-8")
        with pytest.raises(QASetError, match="committed set"):
            resolve_destination(
                formal=True,
                settings=load_settings(),
                items=load_qa(qa_file),
                summary_dir=summary,
                raw_dir=tmp_path / "raw",
                qa_path=qa_file,
            )
        assert not summary.exists()
    summary = SUMMARY_DIR / "chunking_comparison"
    before = _snapshot(summary)
    assert main(["--formal", "--qa", str(tmp_path / "qa_set_dev_v0.csv")]) == 2
    assert _snapshot(summary) == before


def _assert_chart_labels_clear_the_bars(chart: str) -> None:
    width = int(re.search(r'width="(\d+)"', chart).group(1))
    rects = [
        (float(x), float(y), float(w))
        for x, y, w in re.findall(r'<rect x="([\d.]+)" y="([\d.]+)" width="([\d.]+)"', chart)
    ]
    labels = re.findall(r'<text x="([\d.]+)" y="([\d.]+)"[^>]*>([^<]*\([^)]*\))</text>', chart)
    assert labels
    for raw_x, raw_y, text in labels:
        x, y = float(raw_x), float(raw_y)
        end = x + 7.0 * len(text)
        assert end <= width
        for rect_x, rect_y, rect_w in rects:
            if abs((rect_y + 12) - y) > 8:
                continue
            if rect_x >= x:
                assert rect_x >= end
            else:
                assert x >= rect_x + rect_w


def test_formal_bundle_keeps_the_hit_rate_objects(tmp_path):
    hit_at_1 = {"hits": 1, "n": 2, "rate": 0.5}
    hit_at_3 = {"hits": 2, "n": 2, "rate": 1.0}
    payload = {
        "label": "FORMAL",
        "formal": True,
        "note": None,
        "generated_at": "2026-11-17T00:00:00+00:00",
        "command": "python -m eval.chunking_experiment --formal",
        "shared": {
            "size": 600,
            "overlap": 80,
            "top_k": 3,
            "min_coverage": 0.5,
            "embedding": "local:all-MiniLM-L6-v2",
            "corpus_ref": "fixture",
            "corpus_frozen": True,
            "qa_set_ref": "fixture",
            "qa_set_status": "test",
        },
        "configs": {},
        "strategies": [
            {
                "strategy": "fixed",
                "chunk_count": 2,
                "length_min": 10,
                "length_max": 20,
                "length_mean": 15.0,
                "hit@1": hit_at_1,
                "hit@3": hit_at_3,
            }
        ],
        "disagreements": [],
        "judge": "not applicable: retrieval-only comparison",
    }
    directory = tmp_path / "chunking_comparison"
    write_result(payload, directory, formal=True)
    metrics = json.loads((directory / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["strategies"][0]["hit@1"] == hit_at_1
    assert metrics["strategies"][0]["hit@3"] == hit_at_3
    assert "answer_correctness" not in metrics
    chart = (directory / "hit_rates.svg").read_text(encoding="utf-8")
    assert "1/2 (0.5)" in chart
    assert "2/2 (1.0)" in chart
    _assert_chart_labels_clear_the_bars(chart)

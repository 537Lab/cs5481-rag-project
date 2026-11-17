"""T3 retrieval diagnostics; shared evidence predicates, never a second metric engine.

Import ``diagnose_retrieval`` with caller-owned documents/chunks/embedding/store.
The CLI uses the real local ONNX + Chroma path; no generation or paid API calls.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import math
import os
import shlex
import statistics
import subprocess
import sys
from bisect import bisect_right
from collections.abc import Sequence
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path

from eval.evidence import EvidenceSpan, evidence_coverage, is_retrieval_hit, locate_evidence
from eval.metrics import CATEGORIES, DEFAULT_QA, QA_SET_STATUS, QAItem, load_qa
from ragkit.chunking import ChunkConfig, build_chunker
from ragkit.config import DEFAULT_CONFIG, ROOT, load_settings
from ragkit.contracts import Chunk, Document, Embedder, RetrievedChunk, VectorStore
from ragkit.embeddings import build_embedder
from ragkit.loaders import load_documents
from ragkit.store import build_store


def _differences(expected: Chunk, actual: Chunk | None) -> list[str]:
    if actual is None:
        return ["missing"]
    left, right = asdict(expected), asdict(actual)
    return [key for key in left if left[key] != right[key]]


def _source_problems(chunk: Chunk, documents: Sequence[Document]) -> list[str]:
    doc = next((d for d in documents if d.doc_id == chunk.doc_id), None)
    if doc is None:
        return ["unknown_doc_id"]
    problems = []
    if not 0 <= chunk.char_start < chunk.char_end <= len(doc.text):
        problems.append("char_range")
    if doc.text[chunk.char_start : chunk.char_end] != chunk.text:
        problems.append("text_slice")
    problems.extend(
        key
        for key in ("title", "source_uri", "license")
        if getattr(doc, key) != getattr(chunk, key)
    )
    return problems


def _require_unique(values: Sequence[str], label: str) -> None:
    if any(not isinstance(value, str) or not value.strip() for value in values):
        raise ValueError(f"{label} must be a nonempty string")
    if len(set(values)) != len(values):
        raise ValueError(f"duplicate {label}")


def audit_index(expected_chunks: Sequence[Chunk], store: VectorStore) -> dict:
    """Compare the current chunker output with persisted records, not just counts."""
    _require_unique([c.chunk_id for c in expected_chunks], "chunk_id")
    missing, mismatches = [], []
    for expected in expected_chunks:
        actual = store.get_chunk(expected.chunk_id)
        changed = _differences(expected, actual)
        if actual is None:
            missing.append(expected.chunk_id)
        elif changed:
            mismatches.append({"chunk_id": expected.chunk_id, "fields": changed})
    total = store.count()
    return {
        "expected_count": len(expected_chunks),
        "actual_count": total,
        "missing_ids": missing,
        "mismatches": mismatches,
        "unexpected_count": max(0, total - (len(expected_chunks) - len(missing))),
    }


def _record(hit: RetrievedChunk, store: VectorStore, documents: Sequence[Document]) -> dict:
    changed = _differences(hit.chunk, store.get_chunk(hit.chunk.chunk_id))
    return {
        **asdict(hit.chunk),
        "score": hit.score,
        "rank": hit.rank,
        "source_problems": _source_problems(hit.chunk, documents),
        "roundtrip": {"ok": not changed, "fields": changed},
    }


def _union_coverage(chunks: Sequence[Chunk], span: EvidenceSpan) -> float:
    intervals = sorted(
        (max(c.char_start, span.char_start), min(c.char_end, span.char_end))
        for c in chunks
        if c.doc_id == span.doc_id and c.char_start < span.char_end and c.char_end > span.char_start
    )
    covered, end = 0, span.char_start
    for left, right in intervals:
        covered += max(0, right - max(left, end))
        end = max(end, right)
    return covered / span.length


def diagnose_retrieval(
    items: Sequence[QAItem],
    documents: Sequence[Document],
    expected_chunks: Sequence[Chunk],
    embedder: Embedder,
    store: VectorStore,
    *,
    strategy: str,
    collection: str,
    top_k: int = 3,
    min_coverage: float = 0.5,
) -> dict:
    """Record actual ranking and evidence positions without aggregating hit rates."""
    if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k < 0:
        raise ValueError("top_k must be a non-negative integer")
    if not 0 < min_coverage <= 1:
        raise ValueError("min_coverage must be in (0, 1]")
    _require_unique([item.qid for item in items], "qid")
    _require_unique([doc.doc_id for doc in documents], "doc_id")
    if any(item.category not in CATEGORIES or not item.question.strip() for item in items):
        raise ValueError(
            "QA category must be answerable/unanswerable and question must be nonempty"
        )
    audit = audit_index(expected_chunks, store)
    indexed = [
        c
        for e in expected_chunks
        if (c := store.get_chunk(e.chunk_id)) is not None
        and not _differences(e, c)
        and not _source_problems(c, documents)
    ]
    index_ok = not (audit["missing_ids"] or audit["mismatches"] or audit["unexpected_count"])
    rows = []
    for item in items:
        vector = embedder.embed([item.question])[0]
        requested_depth = store.count()
        hits = store.search(vector, requested_depth)
        observation = {
            "requested_depth": requested_depth,
            "searched_count": len(hits),
            "ranking_complete": len({h.chunk.chunk_id for h in hits}) == requested_depth,
        }
        records = [_record(h, store, documents) for h in hits]
        integrity_error = any(not r["roundtrip"]["ok"] or r["source_problems"] for r in records)
        if not item.is_answerable:
            rows.append(
                {
                    "qid": item.qid,
                    **observation,
                    "question": item.question,
                    "strategy": strategy,
                    "collection": collection,
                    "gold": None,
                    "top_k_hit": None,
                    "first_evidence_rank": None,
                    "diagnosis": "unanswerable_label",
                    "label_review": item.reviewed_by or "pending_human_review",
                    "retrieved": records[:top_k],
                    "evidence_candidates": [],
                }
            )
            continue
        try:
            span = locate_evidence(documents, item.evidence_doc_id, item.evidence_quote)
        except ValueError as exc:
            rows.append(
                {
                    "qid": item.qid,
                    **observation,
                    "question": item.question,
                    "strategy": strategy,
                    "collection": collection,
                    "gold": None,
                    "top_k_hit": None,
                    "first_evidence_rank": None,
                    "gold_error": str(exc),
                    "diagnosis": "unknown_gold_unlocated",
                    "retrieved": records[:top_k],
                    "evidence_candidates": [],
                }
            )
            continue
        first = next((h.rank for h in hits if is_retrieval_hit([h], span, min_coverage)), None)
        for hit, record in zip(hits, records, strict=True):
            record["coverage"] = evidence_coverage(hit.chunk, span)
            record["meets_coverage"] = is_retrieval_hit([hit], span, min_coverage)
        top_hit = is_retrieval_hit(hits[:top_k], span, min_coverage)
        max_coverage = max((evidence_coverage(c, span) for c in indexed), default=0.0)
        union = _union_coverage(indexed, span)
        if integrity_error:
            diagnosis = "roundtrip_or_provenance_error"
            top_hit, first = None, None
        elif not index_ok:
            diagnosis = "index_incomplete_or_mismatched"
        elif top_hit:
            diagnosis = "hit"
        elif first is not None:
            diagnosis = "ranking_below_top_k"
        elif max_coverage < min_coverage and union == 1.0:
            diagnosis = "chunk_boundary_fragmentation"
        elif union < 1.0:
            diagnosis = "chunk_coverage_gap"
        else:
            diagnosis = "unknown_needs_review"
        rows.append(
            {
                "qid": item.qid,
                **observation,
                "question": item.question,
                "strategy": strategy,
                "collection": collection,
                "gold": asdict(span),
                "first_evidence_rank": first,
                "top_k_hit": top_hit,
                "max_index_coverage": max_coverage,
                "gold_union_coverage": union,
                "diagnosis": diagnosis,
                "retrieved": records[:top_k],
                "evidence_candidates": [
                    {**record, "coverage": evidence_coverage(h.chunk, span)}
                    for h, record in zip(hits, records, strict=True)
                    if evidence_coverage(h.chunk, span) > 0
                ],
            }
        )
    return {"index_audit": audit, "items": rows}


def score_distribution(scores: Sequence[float]) -> dict:
    """Descriptive statistics, NOT accuracy or a hit-rate metric.

    Histogram covers cosine [-1,1]; tiny numeric excursions are reported in
    underflow/overflow counters without clipping the actual observations.
    """
    values = [float(s) for s in scores]
    if not all(math.isfinite(s) for s in values):
        raise ValueError("scores must be finite")
    edges = [i / 5 for i in range(-5, 6)]
    bins = [{"left": edges[i], "right": edges[i + 1], "count": 0} for i in range(10)]
    for score in values:
        if -1 <= score <= 1:
            bins[min(9, bisect_right(edges, score) - 1)]["count"] += 1
    return {
        "n": len(values),
        "min": min(values) if values else None,
        "max": max(values) if values else None,
        "mean": statistics.mean(values) if values else None,
        "median": statistics.median(values) if values else None,
        "histogram": bins,
        "underflow_count": sum(s < -1 for s in values),
        "overflow_count": sum(s > 1 for s in values),
    }


def _score_groups(rows: Sequence[dict]) -> dict:
    groups = {
        "all_top_k": [],
        "answerable_supporting": [],
        "answerable_other": [],
        "unanswerable_label": [],
    }
    for row in rows:
        for hit in row["retrieved"]:
            groups["all_top_k"].append(hit["score"])
            if row["diagnosis"] == "unanswerable_label":
                group = "unanswerable_label"
            elif row["gold"] is None or row["diagnosis"] == "roundtrip_or_provenance_error":
                continue
            else:
                group = "answerable_supporting" if hit.get("meets_coverage") else "answerable_other"
            groups[group].append(hit["score"])
    return {name: score_distribution(values) for name, values in groups.items()}


def _histogram_svg(groups: dict) -> str:
    # Static labels only; source documents are never interpreted as markup.
    names = ["answerable_supporting", "answerable_other", "unanswerable_label"]
    colors = ["#18794e", "#c75a10", "#5366ab"]
    maximum = max((b["count"] for n in names for b in groups[n]["histogram"]), default=0)
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="900" height="390" '
        'viewBox="0 0 900 390" role="img" aria-labelledby="title desc">',
        '<title id="title">DEVELOPMENT cosine score distribution</title>',
        '<desc id="desc">Top-k observations, grouped by shared evidence coverage. '
        "Not accuracy, probability, or a formal evaluation.</desc>",
        '<rect width="900" height="390" fill="white"/>',
        '<g font-family="sans-serif" font-size="13" fill="#20252b">',
        '<text x="42" y="25">DEVELOPMENT · top-k cosine scores (not probabilities)</text>',
    ]
    for g, (name, color) in enumerate(zip(names, colors, strict=True)):
        parts.append(
            f'<text x="42" y="{48 + 18 * g}" fill="{color}">{name}: n={groups[name]["n"]}</text>'
        )
        for i, bin_ in enumerate(groups[name]["histogram"]):
            height = 190 * bin_["count"] / max(1, maximum)
            x = 58 + i * 80 + g * 19
            parts.append(
                f'<rect x="{x}" y="{300 - height:.2f}" width="17" '
                f'height="{height:.2f}" fill="{color}"/>'
            )
            parts.append(
                f'<text x="{x}" y="{294 - height:.2f}" font-size="10">{bin_["count"]}</text>'
            )
    parts.append('<path d="M45 105V300H870" fill="none" stroke="#333"/>')
    for i in range(11):
        parts.append(f'<text x="{48 + i * 80}" y="324">{-1 + i / 5:.1f}</text>')
    parts.extend(
        [
            '<text x="42" y="353">Bins [left,right); last bin includes 1. '
            "Under/overflow counts are recorded separately in JSON.</text>",
            '<text x="42" y="376">Single-chunk gold coverage is a diagnostic label; '
            "unanswerable labels still need human review.</text>",
            "</g></svg>",
        ]
    )
    return "\n".join(parts) + "\n"


OUTPUT_FILES = ("diagnostics.json", "retrieved.csv", "score_histogram.svg", "run.md")


def _check_output(target: Path, overwrite: bool) -> None:
    if not overwrite and any((target / name).exists() for name in OUTPUT_FILES):
        raise FileExistsError(
            f"output already exists: {target}; choose a new directory or --overwrite"
        )


def write_outputs(report: dict, output_dir: str | Path, *, overwrite: bool = False) -> None:
    """Write the raw diagnostic bundle; refuse silent replacement of a prior run."""
    target = Path(output_dir)
    names = OUTPUT_FILES
    _check_output(target, overwrite)
    target.mkdir(parents=True, exist_ok=True)
    (target / names[0]).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    columns = [
        "qid",
        "question",
        "strategy",
        "collection",
        "diagnosis",
        "rank",
        "score",
        "chunk_id",
        "doc_id",
        "title",
        "source_uri",
        "license",
        "char_start",
        "char_end",
        "coverage",
        "roundtrip_ok",
        "source_problems",
        "text",
    ]
    with (target / names[1]).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in report["items"]:
            for hit in row["retrieved"]:
                record = {
                    k: row[k] for k in ["qid", "question", "strategy", "collection", "diagnosis"]
                }
                record.update({k: hit.get(k, "") for k in columns if k not in record})
                record["roundtrip_ok"] = hit["roundtrip"]["ok"]
                record["source_problems"] = ";".join(hit["source_problems"])
                writer.writerow(record)
    (target / names[2]).write_text(_histogram_svg(report["score_distributions"]), encoding="utf-8")
    provenance = report["provenance"]
    (target / names[3]).write_text(
        f"# T3 DEVELOPMENT retrieval diagnostics\n\nExecution: {report['execution']}\n\n"
        f"Generated UTC: {report['generated_at']}\n\n```sh\n{report['command']}\n```\n\n"
        f"Corpus snapshot SHA256: `{provenance['corpus_snapshot_sha256']}`\n\n"
        f"QA SHA256: `{provenance['qa_sha256']}`\n\n"
        "No formal hit rates, correctness, refusal rates or LLM generation.\n"
        "See diagnostics.json for exact configuration, package versions, code digests,\n"
        "deep ranks, source checks and roundtrip failures.\n"
        "See retrieved.csv and score_histogram.svg.\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _provenance(settings, documents: Sequence[Document], qa: Path, config_path: Path) -> dict:
    snapshot = [
        {
            "doc_id": d.doc_id,
            "title": d.title,
            "source_uri": d.source_uri,
            "license": d.license,
            "loaded_text_sha256": hashlib.sha256(d.text.encode("utf-8")).hexdigest(),
        }
        for d in sorted(documents, key=lambda d: d.doc_id)
    ]
    digest = hashlib.sha256(
        json.dumps(snapshot, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        commit = None
    code = [
        "ragkit/store.py",
        "ragkit/embeddings.py",
        "ragkit/chunking.py",
        "ragkit/contracts.py",
        "ragkit/pipeline.py",
        "ragkit/config.py",
        "ragkit/loaders.py",
        "eval/evidence.py",
        "eval/metrics.py",
        "eval/retrieval_diagnostics.py",
    ]
    packages = {}
    for name in ("chromadb", "openai", "onnxruntime", "numpy"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    return {
        "git_commit": commit,
        "python": sys.version.split()[0],
        "packages": packages,
        "code_sha256": {name: _sha256(ROOT / name) for name in code},
        "manifest": str(settings.manifest),
        "manifest_sha256": _sha256(settings.manifest),
        "qa": str(qa),
        "qa_sha256": _sha256(qa),
        "qa_status": QA_SET_STATUS,
        "config": str(config_path),
        "config_sha256": _sha256(config_path),
        "corpus_snapshot_sha256": digest,
        "documents": snapshot,
        "frozen_manifest_present": (settings.manifest.parent / "frozen_manifest.json").is_file(),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m eval.retrieval_diagnostics",
        description="T3 DEVELOPMENT diagnostics using local ONNX + Chroma; never formal metrics.",
    )
    parser.add_argument("--config", help="alternate config.toml (or RAGKIT_CONFIG)")
    parser.add_argument("--qa", type=Path, default=DEFAULT_QA, help="existing T4-format QA CSV")
    parser.add_argument(
        "--strategy", choices=("fixed", "paragraph"), help="select existing collection"
    )
    parser.add_argument("--top-k", type=int, default=None, help="observed top-k, 0 is allowed")
    parser.add_argument("--min-coverage", type=float, default=0.5, help="shared evidence threshold")
    parser.add_argument(
        "--output-dir", type=Path, help="raw output directory (default: gitignored)"
    )
    parser.add_argument(
        "--overwrite", action="store_true", help="explicitly replace a previous bundle"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    args = build_parser().parse_args(argv)
    try:
        settings = load_settings(args.config)
        # A config override must never accidentally authorize a paid embedding call.
        if settings.embedding_provider != "local":
            raise ValueError(
                "diagnostic CLI only permits local embeddings; API calls are not authorized"
            )
        if args.strategy:
            settings = replace(settings, chunk_strategy=args.strategy)
        output = (
            args.output_dir
            or ROOT / "eval/results/raw" / f"retrieval_diagnostics_{settings.chunk_strategy}"
        )
        _check_output(output, args.overwrite)
        top_k = settings.top_k if args.top_k is None else args.top_k
        documents = load_documents(settings.manifest)
        items = load_qa(args.qa)
        chunker = build_chunker(
            settings.chunk_strategy, ChunkConfig(settings.chunk_size, settings.chunk_overlap)
        )
        chunks = [c for d in documents for c in chunker.split(d)]
        embedder, store = build_embedder(settings), build_store(settings)
        report = diagnose_retrieval(
            items,
            documents,
            chunks,
            embedder,
            store,
            strategy=settings.chunk_strategy,
            collection=settings.collection_name,
            top_k=top_k,
            min_coverage=args.min_coverage,
        )
        config_path = Path(args.config or os.environ.get("RAGKIT_CONFIG", DEFAULT_CONFIG))
        if not config_path.is_absolute():
            config_path = ROOT / config_path
        report.update(
            {
                "schema_version": 1,
                "data_status": "DEVELOPMENT",
                "execution": "MOCK"
                if any(w in embedder.name.lower() for w in ("mock", "fake", "stub"))
                else "REAL_LOCAL",
                "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
                "command": shlex.join(["python", "-m", "eval.retrieval_diagnostics", *argv]),
                "provenance": _provenance(settings, documents, args.qa, config_path),
                "parameters": {
                    "strategy": settings.chunk_strategy,
                    "collection": settings.collection_name,
                    "index_dir": str(settings.index_dir),
                    "top_k": top_k,
                    "min_coverage": args.min_coverage,
                    "size": settings.chunk_size,
                    "overlap": settings.chunk_overlap,
                    "embedding_model": settings.local_model,
                    "embedder": embedder.name,
                    "dimension": embedder.dimension,
                    "threshold_applied": False,
                    "pipeline_min_score": settings.min_score,
                    "llm": "not_used",
                    "rank_depth": "requested_entire_collection",
                },
                "score_distributions": _score_groups(report["items"]),
            }
        )
        write_outputs(report, output, overwrite=args.overwrite)
        print(
            f"[DEVELOPMENT / {report['execution']}] {len(items)} QA items; "
            f"collection={settings.collection_name}; output={output}"
        )
        return 0
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"retrieval diagnostics: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

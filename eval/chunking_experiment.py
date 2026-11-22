"""T2 - compare the two chunking strategies on one QA set.

WHAT THIS DOES
--------------
Indexes ``fixed`` and ``paragraph`` separately, retrieves the same questions
against each index, and reports chunk counts, length stats, hit@k, and the
questions where the strategies disagree.

Hit rates are copied from ``eval.metrics.retrieval_hit_rate``. This file does
not implement hit@k, answer correctness, or abstention. Those stay with T4
and T5. No LLM is called.

OUTPUT
------
A default run is a development run. It prints a development banner and writes
JSON under ``eval/results/raw/chunking_comparison/`` (gitignored). ``--out``
may choose another development directory, but not anywhere inside
``eval/results/summary/`` (relative paths and symlinks included).

``--formal`` asks ``eval.metrics.assert_formal_inputs`` first and passes the
QA path that was actually loaded. Only the committed ``eval/qa_set.csv`` can
enter that gate. Only if the gate accepts does this write
``eval/results/summary/chunking_comparison/``. There is no bypass.

COMMANDS (repository root)
--------------------------
    python -m eval.chunking_experiment --help
    python -m eval.chunking_experiment
    python -m eval.chunking_experiment --formal
"""

from __future__ import annotations

import argparse
import inspect
import json
import sys
from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from eval.metrics import (
    DEFAULT_QA,
    RAW_RESULTS_DIR,
    SUMMARY_DIR,
    QAItem,
    QASetError,
    _config_snapshot,
    _git_user,
    assert_formal_inputs,
    load_qa,
    parse_hits,
    retrieval_hit_rate,
    validate_qa_set,
)
from ragkit.chunking import ChunkConfig, build_chunker
from ragkit.config import ROOT, Settings, load_settings
from ragkit.contracts import Chunk, Document, RetrievedChunk
from ragkit.loaders import load_documents

STRATEGIES = ("fixed", "paragraph")
COMPARISON_DIR = "chunking_comparison"
DEVELOPMENT_LABEL = "DEVELOPMENT"
FORMAL_SUMMARY = SUMMARY_DIR / COMPARISON_DIR


def length_stats(chunks: Sequence[Chunk]) -> dict[str, object]:
    """Descriptive chunk lengths. Not a retrieval metric."""
    lengths = [len(chunk.text) for chunk in chunks]
    if not lengths:
        return {"chunk_count": 0, "length_min": 0, "length_max": 0, "length_mean": None}
    return {
        "chunk_count": len(lengths),
        "length_min": min(lengths),
        "length_max": max(lengths),
        "length_mean": round(sum(lengths) / len(lengths), 4),
    }


def settings_for_strategy(
    settings: Settings, strategy: str, *, size: int, overlap: int, top_k: int
) -> Settings:
    """One strategy, same size / overlap / top_k as the other arm of the run."""
    if strategy not in STRATEGIES:
        raise ValueError(f"unknown chunking strategy: {strategy!r}")
    if size <= 0 or not 0 <= overlap < size:
        raise ValueError("chunk size and overlap must satisfy 0 <= overlap < size")
    if top_k <= 0:
        raise ValueError("top_k must be positive")
    return replace(
        settings,
        chunk_strategy=strategy,
        chunk_size=size,
        chunk_overlap=overlap,
        top_k=top_k,
    )


def _hit_at(row: dict[str, object], level: int) -> bool:
    rank = row.get("first_hit_rank")
    return isinstance(rank, int) and rank <= level


def compare_retrieval(
    items: Sequence[QAItem],
    spans: dict,
    hits_by_strategy: dict[str, dict[str, Sequence[RetrievedChunk]]],
    stats_by_strategy: dict[str, dict[str, object]],
    *,
    hit_levels: Sequence[int] = (1, 3),
    min_coverage: float = 0.5,
) -> dict[str, object]:
    """Score every strategy with ``retrieval_hit_rate`` and list disagreements.

    The hit@k objects on each row are the dicts returned by that function.
    Nothing here recomputes a rate.
    """
    if len(hits_by_strategy) < 2:
        raise QASetError("a comparison needs at least two strategies")
    strategies = tuple(hits_by_strategy)
    per_item: dict[str, dict[str, dict[str, object]]] = {}
    rows: list[dict[str, object]] = []
    for strategy in strategies:
        summary = retrieval_hit_rate(
            items,
            spans,
            hits_by_strategy[strategy],
            hit_levels=hit_levels,
            min_coverage=min_coverage,
        )
        per_item[strategy] = summary["per_item"]
        stats = stats_by_strategy.get(strategy)
        if stats is None:
            raise QASetError(f"no chunk stats for strategy {strategy!r}")
        rows.append({"strategy": strategy, **stats, **summary["rates"]})

    qids = set(per_item[strategies[0]])
    for strategy in strategies[1:]:
        if set(per_item[strategy]) != qids:
            raise QASetError("strategies were scored on different question sets")

    disagreements: list[dict[str, object]] = []
    for qid in sorted(qids):
        for level in hit_levels:
            flags = {strategy: _hit_at(per_item[strategy][qid], level) for strategy in strategies}
            if len(set(flags.values())) == 1:
                continue
            sample = per_item[strategies[0]][qid]
            disagreements.append(
                {
                    "qid": qid,
                    "level": f"hit@{level}",
                    "gold_span": sample["gold_span"],
                    "by_strategy": {
                        strategy: {
                            "hit": flags[strategy],
                            "first_hit_rank": per_item[strategy][qid]["first_hit_rank"],
                            "max_coverage": per_item[strategy][qid]["max_coverage"],
                            "top_chunks": per_item[strategy][qid]["top_chunks"],
                        }
                        for strategy in strategies
                    },
                }
            )
    return {
        "min_coverage": min_coverage,
        "hit_levels": list(hit_levels),
        "strategies": rows,
        "disagreements": disagreements,
        "per_item": per_item,
    }


def _resolved(path: str | Path) -> Path:
    """Absolute path from the repo root, with ``..`` and symlinks resolved."""
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    return candidate.resolve()


def _inside(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents


def development_destination_allowed(path: str | Path) -> bool:
    """Development output must stay out of the formal summary tree."""
    return not _inside(_resolved(path), SUMMARY_DIR.resolve())


def _require_committed_qa(qa_path: str | Path) -> None:
    """A formal comparison can only score the committed QA file.

    T4's gate checks whichever path it is given. Passing the default while
    ``--qa`` pointed somewhere else would let a development set through.
    """
    resolved = _resolved(qa_path)
    committed = DEFAULT_QA.resolve()
    if resolved != committed:
        raise QASetError(
            "--formal refused: QA file must be the committed set "
            f"{_relative(committed)}, got {_relative(resolved)}. "
            "A development or ad-hoc file cannot be published as FORMAL."
        )


def _assert_formal(settings: Settings, items: Sequence[QAItem], qa_path: str | Path) -> None:
    _require_committed_qa(qa_path)
    if "qa_path" in inspect.signature(assert_formal_inputs).parameters:
        assert_formal_inputs(settings, items, qa_path=qa_path)
        return
    assert_formal_inputs(settings, items)


def resolve_destination(
    *,
    formal: bool,
    settings: Settings,
    items: Sequence[QAItem],
    summary_dir: Path,
    raw_dir: Path,
    qa_path: str | Path = DEFAULT_QA,
) -> Path:
    """Formal output is created only after the frozen-input check succeeds."""
    if formal:
        _assert_formal(settings, items, qa_path)
        summary_dir.mkdir(parents=True, exist_ok=True)
        return summary_dir
    if not development_destination_allowed(raw_dir):
        raise QASetError(
            "--out cannot write a development run inside "
            f"{_relative(SUMMARY_DIR)} ({_relative(_resolved(raw_dir))}). "
            "Development numbers stay in eval/results/raw/."
        )
    raw_dir.mkdir(parents=True, exist_ok=True)
    return raw_dir


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def _relative(path: str | Path) -> str:
    try:
        return Path(path).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def development_note(shared: dict[str, object]) -> str:
    """Say which snapshot this development run used. Do not call it formal."""
    frozen = "frozen" if shared.get("corpus_frozen") else "not frozen"
    return (
        "开发用 / development. Not a formal experiment result. "
        f"Corpus {shared.get('corpus_ref')} is {frozen}. "
        f"QA status: {shared.get('qa_set_status')}."
    )


def build_payload(
    comparison: dict[str, object],
    configs_by_strategy: dict[str, dict[str, object]],
    *,
    command: str,
    formal: bool,
) -> dict[str, object]:
    """One record for both arms. Shared I5 fields are taken from T4's snapshot."""
    configs = list(configs_by_strategy.values())
    if not configs:
        raise QASetError("comparison payload needs a config snapshot per strategy")
    shared_keys = (
        "size",
        "overlap",
        "top_k",
        "min_coverage",
        "embedding",
        "llm",
        "corpus_ref",
        "corpus_frozen",
        "qa_set_ref",
        "qa_set_status",
    )
    shared = {key: configs[0].get(key) for key in shared_keys}
    for config in configs[1:]:
        for key in ("size", "overlap", "top_k", "min_coverage", "embedding", "qa_set_ref"):
            if config.get(key) != shared[key]:
                raise QASetError(
                    f"strategies differ on {key}: {shared[key]!r} vs {config.get(key)!r}"
                )
    return {
        "label": "FORMAL" if formal else DEVELOPMENT_LABEL,
        "mode": "chunking_comparison",
        "formal": formal,
        "note": None if formal else development_note(shared),
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "command": command,
        "shared": shared,
        "configs": configs_by_strategy,
        "strategies": comparison["strategies"],
        "disagreements": comparison["disagreements"],
        "judge": (
            "not applicable: retrieval-only comparison. "
            "hit@k is retrieval_hit_rate(); it is not answer correctness"
        ),
    }


def _xml(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


_BAR_MAX = 96
_TEXT_SLOT = 124
_TEXT_GAP = 8
_NAME_WIDTH = 108
_CHART_COLUMNS = (("hit@1", "#3b6ea5"), ("hit@3", "#c47b2b"))


def _comparison_svg(strategies: object) -> str:
    """Bar chart of the hit-rate objects already on each strategy row.

    Each number sits in its own slot to the right of a fixed-width track, so a
    long label cannot run into the next bar.
    """
    rows: list[dict[str, object]] = []
    if isinstance(strategies, list):
        rows = [row for row in strategies if isinstance(row, dict)]
    bar_x: list[int] = []
    cursor = _NAME_WIDTH
    for _column in _CHART_COLUMNS:
        bar_x.append(cursor)
        cursor += _BAR_MAX + _TEXT_GAP + _TEXT_SLOT + 20
    width = cursor - 8
    height = 28 + 36 * max(len(rows), 1)
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
    ]
    for left, (key, _color) in zip(bar_x, _CHART_COLUMNS, strict=True):
        lines.append(f'<text x="{left}" y="16" font-size="12" fill="#333">{key}</text>')
    for index, row in enumerate(rows):
        top = 28 + index * 36
        lines.append(
            f'<text x="8" y="{top + 18}" font-size="12" fill="#222">'
            f'{_xml(str(row.get("strategy", "")))}</text>'
        )
        for left, (key, color) in zip(bar_x, _CHART_COLUMNS, strict=True):
            rate = row.get(key)
            value = rate.get("rate") if isinstance(rate, dict) else None
            fraction = float(value) if isinstance(value, (int, float)) else 0.0
            filled = max(0.0, min(fraction, 1.0)) * _BAR_MAX
            lines.append(
                f'<rect x="{left}" y="{top + 6}" width="{_BAR_MAX}" height="14" fill="#ececec"/>'
            )
            lines.append(
                f'<rect x="{left}" y="{top + 6}" width="{filled:.1f}" height="14" fill="{color}"/>'
            )
            lines.append(
                f'<text x="{left + _BAR_MAX + _TEXT_GAP}" y="{top + 18}" font-size="11" '
                f'fill="#222">{_xml(_format_rate(rate))}</text>'
            )
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def write_result(payload: dict[str, object], directory: Path, *, formal: bool) -> list[Path]:
    """Development: one JSON file. Formal: the summary bundle, and only then."""
    if formal and payload.get("label") != "FORMAL":
        raise QASetError("refusing to write a non-formal payload into summary/")
    if not formal and payload.get("label") == "FORMAL":
        raise QASetError("formal payload cannot be written as a development run")
    directory.mkdir(parents=True, exist_ok=True)
    if not formal:
        return [_write_json(directory / "comparison.json", payload)]
    config = {
        "experiment_id": directory.name,
        "shared": payload["shared"],
        "configs": payload["configs"],
    }
    metrics = {
        "experiment_id": directory.name,
        "generated_at": payload["generated_at"],
        "command": payload["command"],
        "config_ref": "config.json",
        "corpus_ref": payload["shared"].get("corpus_ref"),
        "qa_set_ref": payload["shared"].get("qa_set_ref"),
        "label": payload["label"],
        "strategies": payload["strategies"],
        "disagreement_count": len(payload["disagreements"]),
        "disagreements": payload["disagreements"],
        "judge": payload["judge"],
    }
    written = [
        _write_json(directory / "config.json", config),
        _write_json(directory / "metrics.json", metrics),
    ]
    lines = [
        f"# {directory.name}",
        "",
        f"- command: `{payload['command']}`",
        f"- date: {payload['generated_at']}",
        f"- corpus: {payload['shared'].get('corpus_ref')} "
        f"(frozen: {payload['shared'].get('corpus_frozen')})",
        f"- QA set: {payload['shared'].get('qa_set_ref')} "
        f"({payload['shared'].get('qa_set_status')})",
        f"- size / overlap / top_k / min_coverage: "
        f"{payload['shared'].get('size')} / {payload['shared'].get('overlap')} / "
        f"{payload['shared'].get('top_k')} / {payload['shared'].get('min_coverage')}",
        f"- embedding: {payload['shared'].get('embedding')}",
        f"- executor: {_git_user()}",
        "- exit: 0",
        "- chart: `hit_rates.svg` (drawn from the hit@1 / hit@3 objects below)",
        "",
        "Retrieval hit rates below are the objects returned by "
        "`eval.metrics.retrieval_hit_rate`. This comparison does not score answers.",
        "",
        "| strategy | chunks | length min | length max | length mean | hit@1 | hit@3 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in payload["strategies"]:
        hit1 = _format_rate(row.get("hit@1"))
        hit3 = _format_rate(row.get("hit@3"))
        lines.append(
            f"| `{row['strategy']}` | {row['chunk_count']} | {row['length_min']} | "
            f"{row['length_max']} | {row['length_mean']} | {hit1} | {hit3} |"
        )
    lines.extend(["", f"Disagreements: {len(payload['disagreements'])}", ""])
    run_md = directory / "run.md"
    run_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    chart = directory / "hit_rates.svg"
    chart.write_text(_comparison_svg(payload["strategies"]), encoding="utf-8")
    return [*written, run_md, chart]


def _format_rate(value: object) -> str:
    if not isinstance(value, dict) or "rate" not in value:
        return "-"
    return f"{value['hits']}/{value['n']} ({value['rate']})"


def _chunks_for(settings: Settings, documents: Sequence[Document]) -> list[Chunk]:
    chunker = build_chunker(
        settings.chunk_strategy,
        ChunkConfig(size=settings.chunk_size, overlap=settings.chunk_overlap),
    )
    chunks: list[Chunk] = []
    for document in documents:
        chunks.extend(chunker.split(document))
    return chunks


def index_and_retrieve(
    settings: Settings,
    documents: Sequence[Document],
    items: Sequence[QAItem],
    *,
    k: int,
) -> tuple[dict[str, object], dict[str, list[RetrievedChunk]]]:
    """Rebuild one strategy collection and retrieve every question at ``k``."""
    from ragkit.pipeline import build_pipeline

    chunks = _chunks_for(settings, documents)
    stats = length_stats(chunks)
    pipeline = build_pipeline(settings)
    ingested = pipeline.ingest(manifest=str(settings.manifest), clear=True)
    if ingested.chunks != stats["chunk_count"]:
        raise RuntimeError(
            f"{settings.chunk_strategy}: indexed {ingested.chunks} chunks, "
            f"counted {stats['chunk_count']}"
        )
    if ingested.collection != settings.collection_name:
        raise RuntimeError(
            f"{settings.chunk_strategy}: wrote {ingested.collection}, "
            f"expected {settings.collection_name}"
        )
    hits = {item.qid: pipeline.retrieve(item.question, k=k) for item in items}
    return stats, hits


def print_report(payload: dict[str, object]) -> None:
    label = payload["label"]
    shared = payload["shared"]
    print("=" * 78)
    if label == DEVELOPMENT_LABEL:
        print("[DEVELOPMENT] chunking comparison — 开发用，非正式实验结果")
        print(payload["note"])
    else:
        print("[FORMAL] chunking comparison")
    print("=" * 78)
    print(f"corpus       : {shared.get('corpus_ref')} (frozen={shared.get('corpus_frozen')})")
    print(f"qa set       : {shared.get('qa_set_ref')}")
    print(f"qa status    : {shared.get('qa_set_status')}")
    print(
        "held constant: "
        f"size={shared.get('size')} overlap={shared.get('overlap')} "
        f"top_k={shared.get('top_k')} min_coverage={shared.get('min_coverage')} "
        f"embedding={shared.get('embedding')}"
    )
    print()
    print(f"{'strategy':<12} {'chunks':>7} {'min':>6} {'max':>6} {'mean':>8}  hit@1          hit@3")
    for row in payload["strategies"]:
        print(
            f"{row['strategy']:<12} {row['chunk_count']:>7} {row['length_min']:>6} "
            f"{row['length_max']:>6} {row['length_mean']:>8}  "
            f"{_format_rate(row.get('hit@1')):<14} {_format_rate(row.get('hit@3'))}"
        )
    print()
    disagreements = payload["disagreements"]
    print(f"disagreements: {len(disagreements)}")
    for case in disagreements:
        bits = [
            f"{name}={'hit' if detail['hit'] else 'miss'}(rank={detail['first_hit_rank']})"
            for name, detail in case["by_strategy"].items()
        ]
        print(f"  {case['qid']} {case['level']} gold={case['gold_span']} {', '.join(bits)}")
    print()
    print(payload["judge"])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m eval.chunking_experiment",
        description="Compare fixed and paragraph chunking with eval.metrics.retrieval_hit_rate",
    )
    parser.add_argument("--config", default=None, help="alternate config.toml")
    parser.add_argument("--qa", type=Path, default=DEFAULT_QA, help="QA csv")
    parser.add_argument(
        "--strategies",
        default="fixed,paragraph",
        help="comma-separated strategies; both arms share size, overlap, and top_k",
    )
    parser.add_argument("--size", type=int, default=None, help="override config chunk size")
    parser.add_argument("--overlap", type=int, default=None, help="override config chunk overlap")
    parser.add_argument("--top-k", type=int, default=None, help="override config retrieval top_k")
    parser.add_argument("--hits", default="1,3", help="comma-separated k levels")
    parser.add_argument("--min-coverage", type=float, default=0.5)
    parser.add_argument("--min-items", type=int, default=20)
    parser.add_argument(
        "--formal",
        action="store_true",
        help="publish under eval/results/summary/ only if frozen inputs pass the T4 check",
    )
    parser.add_argument(
        "--summary-dir",
        type=Path,
        default=None,
        help="formal bundle directory; requires --formal",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="development JSON directory (default eval/results/raw/chunking_comparison)",
    )
    return parser


def _parse_strategies(spec: str) -> tuple[str, ...]:
    names = tuple(dict.fromkeys(part.strip() for part in spec.split(",") if part.strip()))
    if len(names) < 2:
        raise QASetError("a comparison needs at least two strategies, for example fixed,paragraph")
    unknown = [name for name in names if name not in STRATEGIES]
    if unknown:
        raise QASetError(f"unknown chunking strategy: {', '.join(unknown)}")
    return names


def _command_line(argv: Sequence[str]) -> str:
    parts = ["python", "-m", "eval.chunking_experiment", *(_relative(part) for part in argv)]
    return " ".join(parts)


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    recorded = sys.argv[1:] if argv is None else list(argv)
    try:
        return _run(args, recorded)
    except QASetError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


def _run(args: argparse.Namespace, recorded: Sequence[str]) -> int:
    if args.summary_dir is not None and not args.formal:
        raise QASetError(
            "--summary-dir needs --formal: development numbers stay in eval/results/raw/"
        )
    settings = load_settings(args.config)
    items = load_qa(args.qa)
    documents = load_documents(settings.manifest)
    spans = validate_qa_set(items, documents, min_items=args.min_items)
    strategies = _parse_strategies(args.strategies)
    hit_levels = parse_hits(args.hits)
    size = settings.chunk_size if args.size is None else args.size
    overlap = settings.chunk_overlap if args.overlap is None else args.overlap
    top_k = settings.top_k if args.top_k is None else args.top_k
    if top_k < max(hit_levels):
        raise QASetError(
            f"top_k ({top_k}) must be at least the largest hit level ({max(hit_levels)})"
        )

    summary_dir = args.summary_dir or FORMAL_SUMMARY
    raw_dir = args.out or (RAW_RESULTS_DIR / COMPARISON_DIR)
    # Check the formal gate before the embedding work, matching eval.metrics.
    destination = resolve_destination(
        formal=args.formal,
        settings=settings,
        items=items,
        summary_dir=summary_dir,
        raw_dir=raw_dir,
        qa_path=args.qa,
    )

    hits_by_strategy: dict[str, dict[str, list[RetrievedChunk]]] = {}
    stats_by_strategy: dict[str, dict[str, object]] = {}
    configs: dict[str, dict[str, object]] = {}
    for strategy in strategies:
        tuned = settings_for_strategy(settings, strategy, size=size, overlap=overlap, top_k=top_k)
        configs[strategy] = _config_snapshot(
            tuned, items, qa_path=args.qa, min_coverage=args.min_coverage
        )
        stats, hits = index_and_retrieve(tuned, documents, items, k=max(hit_levels))
        stats_by_strategy[strategy] = stats
        hits_by_strategy[strategy] = hits

    comparison = compare_retrieval(
        items,
        spans,
        hits_by_strategy,
        stats_by_strategy,
        hit_levels=hit_levels,
        min_coverage=args.min_coverage,
    )
    payload = build_payload(
        comparison,
        configs,
        command=_command_line(recorded),
        formal=args.formal,
    )
    print_report(payload)
    for path in write_result(payload, destination, formal=args.formal):
        print(f"wrote {_relative(path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

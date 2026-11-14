"""T4 - Evaluation set, metric computation, and abstention scoring.

WHAT THIS MODULE DOES
---------------------
1. Validates ``eval/qa_set.csv``: every gold quote must be verbatim text of a
   real document, so it resolves to a character span through
   ``eval.evidence.locate_evidence``. Unanswerable items must declare
   ``ABSENT_TOKENS`` that really do not occur anywhere in the corpus.
2. Computes **retrieval hit rate** with ``is_retrieval_hit()`` from recorded or
   freshly-run retrieval results. This needs no API key: the local ONNX
   embedder and Chroma do all the work.
3. Scores a previously captured answer run (JSON file written by T5):
   abstention behaviour, citation STRUCTURE rate, hit@k of the context that was
   actually used, and - only if a human grading file is supplied - answer
   correctness.

WHAT IT NEVER DOES
------------------
* It never invents a number. Metrics are always ``(numerator, denominator)``
  pairs taken from the rows that were actually processed.
* It never reports answer correctness without a grading file. With no grades,
  correctness is reported as ``"pending human grading"`` and is excluded from
  every other metric, exactly as ``eval/judge_protocol.md`` requires.
* It never treats ``verify_citation_structure()`` as correctness. That function
  checks citation ids and verbatim quotes only (levels 1 + 2).
* It downloads no model and calls no paid API unless you explicitly run a
  command that needs the real index (which was already built by ``cli ingest``).

ANSWER RUN FILE FORMAT (produced by T5, read by ``score``)
----------------------------------------------------------
Either a bare list or ``{"items": [...]}``, one record per question::

    {
      "qid": "A01",
      "abstained": false,
      "answer_text": "RAG is ... [rag_wikipedia#0000]",
      "citations": [{"chunk_id": "rag_wikipedia#0000",
                     "doc_id": "rag_wikipedia",
                     "quote": "Retrieval-augmented generation (RAG) is a ..."}],
      "retrieved_ids": ["rag_wikipedia#0000", "rag_wikipedia#0006"]
    }

``retrieved_ids`` are re-fetched from the vector store with ``get_chunk()``,
which doubles as a provenance roundtrip check.

COMMANDS (run from the repository root)
---------------------------------------
    python -m eval.metrics --help
    python -m eval.metrics validate
    python -m eval.metrics retrieval --hits 1,3 --out eval/results/retrieval.json
    python -m eval.metrics score --outputs eval/results/run.json --grades eval/results/grades.csv
    python -m eval.metrics mock-demo
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path

from eval.evidence import EvidenceSpan, evidence_coverage, is_retrieval_hit, locate_evidence
from ragkit.config import ROOT, Settings, load_settings
from ragkit.contracts import Answer, Chunk, Citation, Document, RetrievedChunk
from ragkit.generation import verify_citation_structure
from ragkit.loaders import load_documents

QA_COLUMNS = [
    "qid",
    "question",
    "reference_answer",
    "evidence_doc_id",
    "evidence_quote",
    "category",
    "notes",
]
CATEGORIES = ("answerable", "unanswerable")
ABSENT_MARKER = "ABSENT_TOKENS:"
DEFAULT_QA = ROOT / "eval" / "qa_set.csv"
PENDING_CORRECTNESS = "pending human grading (no --grades file supplied)"


class QASetError(ValueError):
    """The QA set is malformed: bad columns, bad labels, or non-verbatim gold."""


@dataclass(frozen=True)
class QAItem:
    qid: str
    question: str
    reference_answer: str
    evidence_doc_id: str
    evidence_quote: str
    category: str
    notes: str

    @property
    def is_answerable(self) -> bool:
        return self.category == "answerable"

    @property
    def absent_tokens(self) -> tuple[str, ...]:
        """Tokens declared absent from the corpus (unanswerable items only)."""
        if ABSENT_MARKER not in self.notes:
            return ()
        _, _, tail = self.notes.partition(ABSENT_MARKER)
        return tuple(part.strip().lower() for part in tail.split(";") if part.strip())


# ---------------------------------------------------------------------------
# Loading and validating
# ---------------------------------------------------------------------------


def load_qa(path: str | Path = DEFAULT_QA) -> list[QAItem]:
    file_path = Path(path)
    if not file_path.is_file():
        raise QASetError(f"QA file not found: {file_path}")
    with file_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != QA_COLUMNS:
            raise QASetError(
                f"{file_path} header must be exactly {QA_COLUMNS}, got {reader.fieldnames}"
            )
        items: list[QAItem] = []
        seen: set[str] = set()
        for line_number, row in enumerate(reader, start=2):
            item = _item_from_row(row, line_number, file_path)
            if item.qid in seen:
                raise QASetError(f"{file_path}:{line_number}: duplicate qid {item.qid!r}")
            seen.add(item.qid)
            items.append(item)
    if not items:
        raise QASetError(f"{file_path} contains no data rows")
    return items


def _item_from_row(row: dict[str, str], line_number: int, path: Path) -> QAItem:
    where = f"{path}:{line_number}"
    values = {key: (row.get(key) or "").strip() for key in QA_COLUMNS}
    if not values["qid"] or not values["question"]:
        raise QASetError(f"{where}: qid and question are required")
    if values["category"] not in CATEGORIES:
        raise QASetError(f"{where}: category must be one of {CATEGORIES}, got {values!r}")
    has_evidence = bool(values["evidence_doc_id"] or values["evidence_quote"])
    if values["category"] == "answerable":
        if not (values["evidence_doc_id"] and values["evidence_quote"]):
            raise QASetError(f"{where}: answerable items need evidence_doc_id and evidence_quote")
        if not values["reference_answer"]:
            raise QASetError(f"{where}: answerable items need a reference_answer")
    elif has_evidence:
        raise QASetError(f"{where}: unanswerable items must carry no gold evidence")
    return QAItem(**values)


def validate_qa_set(
    items: Sequence[QAItem], documents: Sequence[Document], *, min_items: int = 20
) -> dict[str, EvidenceSpan]:
    """Resolve every gold quote and check the labels. Raises QASetError if invalid."""
    corpus = " ".join(document.text for document in documents).lower()
    errors: list[str] = []
    spans: dict[str, EvidenceSpan] = {}
    for item in items:
        if item.is_answerable:
            try:
                spans[item.qid] = locate_evidence(
                    documents, item.evidence_doc_id, item.evidence_quote
                )
            except ValueError as exc:
                errors.append(f"{item.qid}: {exc}")
            continue
        if not item.absent_tokens:
            errors.append(f"{item.qid}: unanswerable but declares no ABSENT_TOKENS")
        for token in item.absent_tokens:
            if token in corpus:
                errors.append(f"{item.qid}: token {token!r} occurs in the corpus")
    if len(items) < min_items:
        errors.append(f"only {len(items)} items, the assignment needs at least {min_items}")
    if not any(item.is_answerable for item in items):
        errors.append("no answerable items")
    if all(item.is_answerable for item in items):
        errors.append("no unanswerable items, so abstention cannot be measured")
    if errors:
        raise QASetError("\n".join(errors))
    return spans


# ---------------------------------------------------------------------------
# Pure metric kernels
# ---------------------------------------------------------------------------


def _command_line() -> str:
    """The invocation, rebuilt without this machine's absolute interpreter path.

    ``sys.argv[0]`` is the resolved module file when run through ``-m``, so the
    raw join would leak a local path and differ on every laptop.
    """
    return " ".join(["python", "-m", "eval.metrics", *sys.argv[1:]])


def _relative(path: str | Path) -> str:
    """Repo-relative when possible, so result files diff across machines."""
    file_path = Path(path).resolve()
    try:
        return file_path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(file_path)


@dataclass
class EvalResult:
    """One evaluation run: labels, config, aggregate metrics, and per-item rows."""

    label: str
    mode: str
    config: dict[str, object]
    metrics: dict[str, object] = field(default_factory=dict)
    items: list[dict[str, object]] = field(default_factory=list)

    def to_payload(self) -> dict[str, object]:
        return {
            "label": self.label,
            "mode": self.mode,
            "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "command": _command_line(),
            "config": self.config,
            "metrics": self.metrics,
            "items": self.items,
        }

    def write(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(self.to_payload(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        return target


def _rate(numerator: int, denominator: int) -> dict[str, object]:
    """Always show numerator and denominator: a bare rate is unauditable."""
    return {
        "hits": numerator,
        "n": denominator,
        "rate": round(numerator / denominator, 4) if denominator else None,
    }


def evaluate_retrieval(
    items: Sequence[QAItem],
    spans: dict[str, EvidenceSpan],
    hits_by_qid: dict[str, Sequence[RetrievedChunk]],
    *,
    hit_levels: Sequence[int] = (1, 3),
    min_coverage: float = 0.5,
) -> EvalResult:
    """hit@k over answerable items only, using is_retrieval_hit().

    Unanswerable items are excluded by design: there is no gold span to hit, so
    counting them would silently deflate the rate. They are scored for
    abstention in evaluate_answers() instead.
    """
    answerable = [item for item in items if item.is_answerable]
    missing = [item.qid for item in answerable if item.qid not in hits_by_qid]
    if missing:
        raise QASetError(f"no retrieval result for qid(s): {', '.join(missing)}")
    counters = {level: 0 for level in hit_levels}
    rows: list[dict[str, object]] = []
    for item in answerable:
        span = spans[item.qid]
        hits = list(hits_by_qid[item.qid])
        first_hit_rank = _first_hit_rank(hits, span, min_coverage)
        for level in hit_levels:
            if is_retrieval_hit(hits[:level], span, min_coverage=min_coverage):
                counters[level] += 1
        rows.append(
            {
                "qid": item.qid,
                "gold_span": [span.char_start, span.char_end],
                "span_length": span.length,
                "n_hits": len(hits),
                "first_hit_rank": first_hit_rank,
                "max_coverage": round(
                    max((evidence_coverage(hit.chunk, span) for hit in hits), default=0.0), 4
                ),
                "top_chunks": [
                    {"chunk_id": hit.chunk.chunk_id, "score": round(hit.score, 4)}
                    for hit in hits[: max(hit_levels)]
                ],
            }
        )
    metrics: dict[str, object] = {
        "min_coverage": min_coverage,
        "n_items": len(items),
        "n_answerable": len(answerable),
        "n_unanswerable": len(items) - len(answerable),
    }
    for level in hit_levels:
        metrics[f"hit@{level}"] = _rate(counters[level], len(answerable))
    return EvalResult(label="", mode="retrieval", config={}, metrics=metrics, items=rows)


def _first_hit_rank(
    hits: Sequence[RetrievedChunk], span: EvidenceSpan, min_coverage: float
) -> int | None:
    """Rank of the first retrieved chunk that covers enough gold evidence."""
    return next(
        (
            hit.rank
            for hit in hits
            if is_retrieval_hit([hit], span, min_coverage=min_coverage)
        ),
        None,
    )


def citations_from_record(
    record: dict[str, object], chunk_of: Callable[[str], Chunk | None]
) -> tuple[list[Citation], list[str]]:
    """Rebuild Citations exactly as recorded. Empty quotes are a hard error."""
    problems: list[str] = []
    citations: list[Citation] = []
    raw = record.get("citations") or []
    if isinstance(raw, dict):  # tolerate a single citation given as an object
        raw = [raw]
    for entry in raw:
        chunk_id = str(entry.get("chunk_id", ""))
        quote = str(entry.get("quote", "")).strip()
        if not chunk_id:
            problems.append("citation without chunk_id")
            continue
        if not quote:
            problems.append(f"{chunk_id}: no quote recorded, level 2 cannot be checked")
            continue
        chunk = chunk_of(chunk_id)
        if chunk is None:
            problems.append(f"{chunk_id}: unknown chunk id")
        citations.append(
            Citation(
                chunk_id=chunk_id,
                doc_id=str(entry.get("doc_id") or (chunk.doc_id if chunk else "")),
                quote=quote,
                title=chunk.title if chunk else str(entry.get("title", "")),
                source_uri=chunk.source_uri if chunk else "",
            )
        )
    return citations, problems


def evaluate_answers(
    items: Sequence[QAItem],
    spans: dict[str, EvidenceSpan],
    outputs: dict[str, dict[str, object]],
    *,
    chunk_of: Callable[[str], Chunk | None],
    hit_levels: Sequence[int] = (1, 3),
    min_coverage: float = 0.5,
    grades: dict[str, str] | None = None,
) -> EvalResult:
    """Abstention, citation structure, hit@k of the used context, and correctness.

    ``grades`` maps qid -> correct|incorrect|unsure. Correctness is reported only
    when a grading file was supplied; otherwise it stays pending.
    """
    grades = grades or {}
    rows: list[dict[str, object]] = []
    absent_qids = [item.qid for item in items if item.qid not in outputs]
    if absent_qids:
        raise QASetError(f"outputs file has no record for qid(s): {', '.join(absent_qids)}")

    counters = {level: 0 for level in hit_levels}
    n_answerable = n_unanswerable = 0
    correct_abst = wrong_abst = expected_abst = answered = 0
    structure_ok = structure_checked = 0
    graded = correct = 0

    for item in items:
        record = outputs[item.qid]
        abstained = bool(record.get("abstained"))
        retrieved = _retrieved_from_record(record, chunk_of)
        citations, structure_problems = citations_from_record(record, chunk_of)
        answer = Answer(
            question=item.question,
            answer_text=str(record.get("answer_text", "")),
            citations=tuple(citations),
            abstained=abstained,
            model=str(record.get("model", "unknown")),
            raw=str(record.get("raw", record.get("answer_text", ""))),
        )
        span = spans.get(item.qid)
        first_hit_rank = None
        if span is not None and retrieved:
            first_hit_rank = _first_hit_rank(retrieved, span, min_coverage)
            for level in hit_levels:
                if is_retrieval_hit(retrieved[:level], span, min_coverage=min_coverage):
                    counters[level] += 1

        if item.is_answerable:
            n_answerable += 1
            if abstained:
                wrong_abst += 1
            else:
                answered += 1
        else:
            n_unanswerable += 1
            expected_abst += 1
            correct_abst += int(abstained)

        structural: bool | None = None
        if not abstained:
            structure_checked += 1
            structural = not structure_problems and verify_citation_structure(answer, retrieved)
            if structural:
                structure_ok += 1
            else:
                structure_problems = structure_problems or ["ids or quote failed structure check"]

        grade = grades.get(item.qid)
        if grade is not None:
            graded += 1
            correct += int(grade == "correct")

        rows.append(
            {
                "qid": item.qid,
                "category": item.category,
                "abstained": abstained,
                "expected_abstain": not item.is_answerable,
                "n_retrieved": len(retrieved),
                "first_hit_rank": first_hit_rank,
                "citation_ids": [citation.chunk_id for citation in citations],
                "citation_structure_valid": structural,
                "structure_problems": structure_problems,
                "grade": grade,
                "answer_text": answer.answer_text[:400],
            }
        )

    metrics: dict[str, object] = {
        "min_coverage": min_coverage,
        "n_items": len(items),
        "n_answerable": n_answerable,
        "n_unanswerable": n_unanswerable,
        "false_abstention_rate": _rate(wrong_abst, n_answerable),
        "correct_abstention_rate": _rate(correct_abst, expected_abst),
        "citation_structure_rate": _rate(structure_ok, structure_checked),
        "answer_correctness": _rate(correct, graded) if graded else PENDING_CORRECTNESS,
        "n_graded": graded,
    }
    for level in hit_levels:
        metrics[f"hit@{level}"] = _rate(counters[level], n_answerable)
    return EvalResult(
        label="",
        mode="answers",
        config={"graded": bool(graded), "n_answered": answered},
        metrics=metrics,
        items=rows,
    )


def _retrieved_from_record(
    record: dict[str, object], chunk_of: Callable[[str], Chunk | None]
) -> list[RetrievedChunk]:
    """Rebuild the context a run actually used, by round-tripping chunk ids.

    hit@k here depends on rank order only, so a run that recorded plain ids is
    still scorable. No score is ever invented: an unrecorded score stays 0.0.
    """
    hits: list[RetrievedChunk] = []
    for entry in record.get("retrieved_ids") or []:
        if isinstance(entry, dict):
            chunk_id = str(entry.get("chunk_id", ""))
            score = float(entry.get("score") or 0.0)
        else:
            chunk_id, score = str(entry), 0.0
        chunk = chunk_of(chunk_id)
        if chunk is None:
            continue
        hits.append(RetrievedChunk(chunk=chunk, score=score, rank=len(hits) + 1))
    return hits


# ---------------------------------------------------------------------------
# Human grading sheet
# ---------------------------------------------------------------------------

GRADE_COLUMNS = ["qid", "question", "reference_answer", "answer_text", "citations", "grade"]
ALLOWED_GRADES = ("correct", "incorrect", "unsure")


def write_grading_sheet(path: str | Path, items: Sequence[QAItem], outputs: dict) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(GRADE_COLUMNS)
        for item in items:
            record = outputs.get(item.qid, {})
            writer.writerow(
                [
                    item.qid,
                    item.question,
                    item.reference_answer,
                    str(record.get("answer_text", "")),
                    ",".join(
                        str(entry.get("chunk_id", ""))
                        for entry in (record.get("citations") or [])
                        if isinstance(entry, dict)
                    ),
                    "",
                ]
            )
    return target


def load_grades(path: str | Path) -> dict[str, str]:
    file_path = Path(path)
    if not file_path.is_file():
        raise QASetError(f"grading file not found: {file_path}")
    with file_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or "grade" not in reader.fieldnames:
            raise QASetError(f"{file_path} needs a 'grade' column, got {reader.fieldnames}")
        grades: dict[str, str] = {}
        for row in reader:
            grade = (row.get("grade") or "").strip().lower()
            if not grade:
                continue
            if grade not in ALLOWED_GRADES:
                raise QASetError(
                    f"{file_path}: grade must be one of {ALLOWED_GRADES}, got {grade!r}"
                )
            grades[str(row["qid"]).strip()] = grade
    if not grades:
        raise QASetError(f"{file_path} has no graded rows; every grade cell is empty")
    return grades


def load_outputs(path: str | Path) -> dict[str, dict[str, object]]:
    file_path = Path(path)
    if not file_path.is_file():
        raise QASetError(f"outputs file not found: {file_path}")
    payload = json.loads(file_path.read_text(encoding="utf-8"))
    records = payload.get("items") if isinstance(payload, dict) else payload
    if not isinstance(records, list):
        raise QASetError(f"{file_path} must be a list of records or {{'items': [...]}}")
    by_qid: dict[str, dict[str, object]] = {}
    for record in records:
        if not isinstance(record, dict) or "qid" not in record:
            raise QASetError(f"{file_path}: every record needs a qid")
        by_qid[str(record["qid"])] = record
    return by_qid


# ---------------------------------------------------------------------------
# CLI wiring (the only place that touches config, the store, or the network)
# ---------------------------------------------------------------------------


def _settings(args: argparse.Namespace) -> Settings:
    settings = load_settings(args.config)
    if getattr(args, "chunking", None):
        settings = replace(settings, chunk_strategy=args.chunking)
    return settings


def _config_snapshot(settings: Settings, items: Sequence[QAItem]) -> dict[str, object]:
    return {
        "corpus_manifest": _relative(settings.manifest),
        "chunking": settings.chunk_strategy,
        "chunk_size": settings.chunk_size,
        "chunk_overlap": settings.chunk_overlap,
        "collection": settings.collection_name,
        "embedding": f"{settings.embedding_provider}:{settings.embedding_dimension}d",
        "llm_model": settings.llm_model,
        "qa_items": len(items),
        "python": sys.version.split()[0],
    }


def cmd_validate(args: argparse.Namespace) -> int:
    qa_path = Path(args.qa)
    items = load_qa(qa_path)
    documents = load_documents(args.manifest)
    spans = validate_qa_set(items, documents, min_items=args.min_items)
    answerable = [item for item in items if item.is_answerable]
    per_doc: dict[str, int] = {}
    for item in answerable:
        per_doc[item.evidence_doc_id] = per_doc.get(item.evidence_doc_id, 0) + 1
    print(f"[REAL] validated {qa_path.name}: {len(items)} items "
          f"({len(answerable)} answerable, {len(items) - len(answerable)} unanswerable)")
    print(f"documents consulted: {len(documents)}; "
          f"all {len(spans)} gold quotes resolve to a source character span")
    for doc_id, count in sorted(per_doc.items()):
        print(f"  {doc_id:26} {count:3d} answerable items")
    print("gold span sample (strategy-independent):")
    for item in answerable[:3]:
        span = spans[item.qid]
        print(f"  {item.qid} {span.doc_id} chars {span.char_start}-{span.char_end}")
    print("unanswerable absence checks: "
          f"{sum(len(item.absent_tokens) for item in items if not item.is_answerable)} tokens "
          "confirmed absent from the corpus")
    return 0


def cmd_retrieval(args: argparse.Namespace) -> int:
    settings = _settings(args)
    items = load_qa(args.qa)
    spans = validate_qa_set(items, load_documents(settings.manifest), min_items=args.min_items)
    hit_levels = parse_hits(args.hits)
    from ragkit.pipeline import build_pipeline

    pipeline = build_pipeline(settings)
    if pipeline.store.count() == 0:
        print(
            f"Collection '{settings.collection_name}' is empty. "
            f"Run: python -m ragkit.cli ingest (or pass --chunking {settings.chunk_strategy})",
            file=sys.stderr,
        )
        return 2
    print("[REAL] retrieval evaluation: real corpus / real embeddings / real Chroma index")
    print(f"    collection : {settings.collection_name} "
          f"(chunks={pipeline.store.count()})")
    print(f"    embedding  : {settings.embedding_provider} dim={settings.embedding_dimension}")
    print(f"    hit@k      : levels {hit_levels}, min_coverage={args.min_coverage}\n")
    max_k = max(hit_levels)
    hits_by_qid = {item.qid: pipeline.retrieve(item.question, k=max_k) for item in items}
    result = evaluate_retrieval(
        items, spans, hits_by_qid, hit_levels=hit_levels, min_coverage=args.min_coverage
    )
    result.label = "REAL"
    result.config = _config_snapshot(settings, items)
    print_summary(result, print_items=args.print_items)
    if args.out:
        print(f"\nwrote {result.write(args.out)}")
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    settings = _settings(args)
    items = load_qa(args.qa)
    spans = validate_qa_set(items, load_documents(settings.manifest), min_items=args.min_items)
    outputs = load_outputs(args.outputs)
    grades = load_grades(args.grades) if args.grades else None
    hit_levels = parse_hits(args.hits)
    from ragkit.pipeline import build_pipeline

    store = build_pipeline(settings).store
    if store.count() == 0:
        print(f"Collection '{settings.collection_name}' is empty; run `cli ingest` first.",
              file=sys.stderr)
        return 2
    result = evaluate_answers(
        items,
        spans,
        outputs,
        chunk_of=store.get_chunk,
        hit_levels=hit_levels,
        min_coverage=args.min_coverage,
        grades=grades,
    )
    result.label = args.label
    result.config = _config_snapshot(settings, items) | {
        "outputs_file": _relative(args.outputs),
        "grades_file": _relative(args.grades) if args.grades else None,
    }
    print(f"[{result.label}] scoring answer run: {args.outputs}")
    print_summary(result, print_items=args.print_items)
    if args.grading_sheet:
        print(f"wrote grading sheet {write_grading_sheet(args.grading_sheet, items, outputs)}")
    if args.out:
        print(f"wrote {result.write(args.out)}")
    return 0


def cmd_mock_demo(args: argparse.Namespace) -> int:
    """MOCK end-to-end exercise of the metric code. NEVER a result for the report.

    Doubles come from tests/fakes.py, the corpus is tests/fixtures/, and the
    "answers" are scripted. This proves the metric maths and the CLI wiring work
    offline; every printed number is labelled MOCK.
    """
    import re

    from ragkit.chunking import ChunkConfig, FixedSizeChunker
    from ragkit.contracts import CITATION_PATTERN
    from ragkit.generation import AnswerGenerator
    from ragkit.pipeline import RAGPipeline
    from tests.fakes import FAKE_MANIFEST, FakeEmbedder, InMemoryStore, ScriptedLLM, settings_stub

    print("=" * 78)
    print("[MOCK] metric code exercise: fixtures + scripted doubles. NOT an experiment.")
    print("=" * 78)
    documents = load_documents(ROOT / FAKE_MANIFEST)
    chunker = FixedSizeChunker(ChunkConfig(size=120, overlap=20))
    chunks = [chunk for doc in documents for chunk in chunker.split(doc)]
    store = InMemoryStore()
    embedder = FakeEmbedder()
    store.upsert(chunks, embedder.embed([chunk.text for chunk in chunks]))

    items, spans = _mock_items(documents)
    hit_levels = parse_hits(args.hits)

    def scripted(system: str, user: str) -> str:
        context = user.split("QUESTION:")[0]
        ids = re.findall(CITATION_PATTERN, context)
        if "MOCK UNANSWERABLE" in user:
            return "NO_ANSWER"
        return f"Mocked answer from the fixture [{ids[0]}]" if ids else "NO_ANSWER"

    llm = ScriptedLLM(scripted)
    pipeline = RAGPipeline(
        settings=settings_stub(top_k=3),
        chunker=chunker,
        embedder=embedder,
        store=store,
        generator=AnswerGenerator(llm=llm),
        llm=llm,
    )
    outputs: dict[str, dict[str, object]] = {}
    for item in items:
        answer, hits = pipeline.ask(item.question)
        outputs[item.qid] = {
            "qid": item.qid,
            "abstained": answer.abstained,
            "answer_text": answer.answer_text,
            "model": answer.model,
            "citations": [
                {"chunk_id": c.chunk_id, "doc_id": c.doc_id, "quote": c.quote}
                for c in answer.citations
            ],
            "retrieved_ids": [hit.chunk.chunk_id for hit in hits],
        }
    result = evaluate_answers(
        items,
        spans,
        outputs,
        chunk_of=store.get_chunk,
        hit_levels=hit_levels,
        min_coverage=args.min_coverage,
        grades={item.qid: "correct" for item in items if item.is_answerable},
    )
    result.label = "MOCK"
    result.config = {"fixtures": _relative(ROOT / FAKE_MANIFEST), "chunks": len(chunks)}
    print_summary(result, print_items=True)
    print("\nThese numbers describe MOCK fixtures only. Do not put them in the report.")
    return 0


def _mock_items(documents: Sequence[Document]) -> tuple[list[QAItem], dict[str, EvidenceSpan]]:
    """Build a MOCK gold set from tests/fixtures so the maths can run offline.

    Gold quotes are taken from the second paragraph of each fixture, never from
    the shared "MOCK FIXTURE" banner, so the two documents stay distinguishable.
    """
    items: list[QAItem] = []
    spans: dict[str, EvidenceSpan] = {}
    for index, document in enumerate(documents, start=1):
        body = document.text.split("\n\n", 1)[1]
        stop = body.find(".")
        if stop < 0:
            raise QASetError(f"MOCK fixture {document.doc_id} has no usable sentence")
        quote = body[: stop + 1]
        item = QAItem(
            qid=f"MOCK{index:02d}",
            question=f"MOCK: what does {document.doc_id} say about its service?",
            reference_answer="the fixture's first service sentence",
            evidence_doc_id=document.doc_id,
            evidence_quote=quote,
            category="answerable",
            notes="MOCK item generated from tests/fixtures for plumbing checks only",
        )
        items.append(item)
        spans[item.qid] = locate_evidence(documents, document.doc_id, quote)
    items.append(
        QAItem(
            qid="MOCKN01",
            question="MOCK UNANSWERABLE: what is the menu on Mars?",
            reference_answer="",
            evidence_doc_id="",
            evidence_quote="",
            category="unanswerable",
            notes="MOCK refusal case. ABSENT_TOKENS: mars",
        )
    )
    return items, spans


def parse_hits(spec: str) -> tuple[int, ...]:
    try:
        levels = tuple(dict.fromkeys(int(part) for part in spec.split(",") if part.strip()))
    except ValueError as exc:
        raise QASetError(f"--hits must be positive integers, got {spec!r}") from exc
    if not levels or any(level <= 0 for level in levels):
        raise QASetError(f"--hits must be positive integers, got {spec!r}")
    return levels


def print_summary(result: EvalResult, *, print_items: bool) -> None:
    print(f"[{result.label}] {result.mode} metrics")
    for key, value in result.metrics.items():
        if isinstance(value, dict):
            numerator, denominator, rate = value["hits"], value["n"], value["rate"]
            shown = "n/a" if rate is None else f"{rate:.4f}"
            print(f"  {key:26} {numerator:3d}/{denominator:<3d} {shown}")
        else:
            print(f"  {key:26} {value}")
    if print_items:
        print("\nper item")
        for row in result.items:
            print(f"  {json.dumps(row, ensure_ascii=False)}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m eval.metrics",
        description="CS5481 Topic 5 T4: QA set validation and evaluation metrics",
    )
    parser.add_argument("--config", default=None, help="alternate config.toml")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(cmd: argparse.ArgumentParser, *, hits: bool = True) -> None:
        cmd.add_argument(
            "--qa", type=Path, default=DEFAULT_QA, help="QA csv (default eval/qa_set.csv)"
        )
        cmd.add_argument(
            "--min-items", type=int, default=20, help="required minimum item count"
        )
        if hits:
            cmd.add_argument("--hits", default="1,3", help="comma separated k levels")
        cmd.add_argument(
            "--min-coverage",
            type=float,
            default=0.5,
            help="share of the gold span a chunk must cover to count as a hit",
        )
        cmd.add_argument(
            "--print-items", action="store_true", help="dump the per-item table"
        )
        cmd.add_argument(
            "--out", type=Path, default=None, help="write the json report to this path"
        )

    validate = sub.add_parser("validate", help="check qa_set.csv gold quotes and labels")
    add_common(validate, hits=False)
    validate.add_argument("--manifest", default=str(ROOT / "data" / "raw" / "manifest.json"))
    validate.set_defaults(func=cmd_validate)

    retrieval = sub.add_parser(
        "retrieval", help="REAL hit@k over the built index (needs `cli ingest`, no API key)"
    )
    add_common(retrieval)
    retrieval.add_argument(
        "--chunking",
        choices=("fixed", "paragraph"),
        default=None,
        help="override config.toml for this run (used by the T2 comparison)",
    )
    retrieval.set_defaults(func=cmd_retrieval)

    score = sub.add_parser("score", help="abstention, citation structure, correctness from a run")
    add_common(score)
    score.add_argument(
        "--outputs",
        type=Path,
        required=True,
        help="answer run json, format documented at the top of this module",
    )
    score.add_argument(
        "--grades", type=Path, default=None, help="human grading csv (see judge_protocol.md)"
    )
    score.add_argument(
        "--grading-sheet", type=Path, default=None, help="write an empty grading sheet here"
    )
    score.add_argument("--chunking", choices=("fixed", "paragraph"), default=None)
    score.add_argument("--label", default="REAL", help="REAL or MOCK, printed and stored")
    score.set_defaults(func=cmd_score)

    demo = sub.add_parser("mock-demo", help="MOCK plumbing exercise, never an experiment")
    add_common(demo)
    demo.set_defaults(func=cmd_mock_demo)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except QASetError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

"""T4 - Evaluation set, the team's single metric implementation, abstention scoring.

PUBLIC METRIC API = INTERFACE I3 (`docs/PROJECT_PLAN.md` 6.1)
-------------------------------------------------------------
T2 / T3 / T5 import these four and must not re-derive the maths elsewhere::

    retrieval_hit_rate(items, spans, hits_by_qid, *, hit_levels, min_coverage)
    answer_correctness(items, grades)
    abstention_rates(items, outputs)
    citation_structure_rate(items, outputs, *, chunk_of)

``evaluate_retrieval()`` / ``evaluate_answers()`` are thin aggregators on top of
them: they add per-item rows and a provenance envelope, they do not define a
second formula.

WHAT THIS MODULE DOES
---------------------
1. Validates ``eval/qa_set.csv``: every gold quote must be verbatim text of a
   real document, so it resolves to a character span through
   ``eval.evidence.locate_evidence``.
2. Computes retrieval hit@k with ``is_retrieval_hit()`` from recorded or freshly
   run retrieval. No API key needed: the local ONNX embedder and Chroma do it.
3. Scores an answer artifact (interface I4, see below): abstention behaviour,
   citation STRUCTURE rate, hit@k of the context actually used, and answer
   correctness - the last one only from a human grading file.

WHAT IT NEVER DOES
------------------
* It never invents a number. Rates are ``(numerator, denominator)`` pairs taken
  from the rows actually processed.
* It never treats ``ABSENT_TOKENS`` as proof that a question is unanswerable.
  That marker only proves the declared strings do not occur in the corpus, a
  *necessary* condition. Whether the question is genuinely unanswerable is a
  human judgement, attested per item with ``REVIEWED_BY`` in ``notes``; items
  without it are counted as pending review and ``--require-reviewed`` turns that
  into a hard failure so an unreviewed set cannot be frozen as the formal one.
* It never reports answer correctness without a grading file: with no grades,
  correctness is the string ``"pending human grading"``. Its denominator is
  always the number of **answerable** items; unanswerable items are scored by
  the abstention rule, never as correctness.
* It never treats ``verify_citation_structure()`` as correctness - that function
  checks citation ids and verbatim quotes only (levels 1 + 2 of the three-level
  table in ``eval/README.md``).
* It downloads no model and calls no paid API unless you run a command that
  needs the real index (built once by ``cli ingest``).

ANSWER ARTIFACT FORMAT = INTERFACE I4
-------------------------------------
T5 writes ``eval/answers/<run_id>.jsonl``, one JSON object per line::

    {"qid": "A01",
     "answer": {"answer_text": "RAG is ... [rag_wikipedia#0000]",
                "abstained": false,
                "citations": [{"chunk_id": "rag_wikipedia#0000",
                               "doc_id": "rag_wikipedia",
                               "quote": "Retrieval-augmented generation ..."}],
                "model": "gpt-4o-mini", "raw": "..."},
     "retrieved_chunk_ids": ["rag_wikipedia#0000", "rag_wikipedia#0006"],
     "run_id": "20261115-fixed-top3", "config_ref": "eval/results/summary/x/config.json"}

Flat records (``answer_text`` / ``abstained`` at the top level), a ``.json``
list, a ``{"items": [...]}`` envelope and the older ``retrieved_ids`` key are
all still accepted, so nothing that already works has to be rewritten. Fields
are re-fetched from the vector store by chunk id through ``get_chunk()``, which
doubles as a provenance roundtrip check.

COMMANDS (run from the repository root)
---------------------------------------
    python -m eval.metrics --help
    python -m eval.metrics validate --require-reviewed
    python -m eval.metrics retrieval --hits 1,3 --out eval/results/raw/retrieval.json
    python -m eval.metrics score --run-id 20261115-fixed-top3 --grades eval/results/raw/grades.csv
    python -m eval.metrics mock-demo

``retrieval`` and ``score`` also take ``--summary-dir DIR --formal`` to write a
reproducible aggregate bundle (``config.json`` / ``metrics.json`` / ``run.md``)
into ``eval/results/summary/``, and ``--chunking`` to override config.toml for
one run without editing it (used by the T2 comparison).

WHERE RESULTS GO
----------------
Per-item output belongs to the gitignored ``eval/results/raw/``. Only real,
reproducible aggregates belong in ``eval/results/summary/`` (see
``eval/results/README.md``): ``--summary-dir`` refuses MOCK runs and refuses
anything that is not on frozen inputs. Two QA files are committed: the formal
Kubernetes set at ``eval/qa_set.csv`` (interface I2, the default for every
command) and the Wikipedia development set at ``eval/qa_set_dev_v0.csv``.
``qa_set_status`` is derived from which file it is and what its rows cite - see
``qa_set_status()`` - so a development number cannot be relabelled by a flag.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shlex
import subprocess
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

# The arguments `main()` was called with; recorded at import for the CLI case
# and overwritten whenever a caller passes an explicit argv.
_COMMAND_ARGS: list[str] = [str(part) for part in sys.argv[1:]]

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
REVIEW_MARKER = "REVIEWED_BY:"
DEFAULT_QA = ROOT / "eval" / "qa_set.csv"
# The 35 items written against CORPUS_V0 keep their own file instead of their
# old path: T2/T3/T5 can still exercise plumbing on them without an API key,
# while the single I2 path every tool reads by default now carries the formal
# Kubernetes set for the frozen snapshot.
DEV_QA = ROOT / "eval" / "qa_set_dev_v0.csv"
ANSWERS_DIR = ROOT / "eval" / "answers"
RAW_RESULTS_DIR = ROOT / "eval" / "results" / "raw"
SUMMARY_DIR = ROOT / "eval" / "results" / "summary"
FROZEN_MANIFEST = ROOT / "data" / "raw" / "frozen_manifest.json"
ARTIFACT_SUFFIXES = (".jsonl", ".ndjson", ".json")
PENDING_CORRECTNESS = "pending human grading (no --grades file supplied)"
# Which set a file holds is a property of the file, so it is written down per
# path rather than as one global constant. `qa_set_status()` appends what the
# rows themselves say (corpus binding, pending review) to these stems.
QA_SET_STATUS_BY_FILE = {
    "eval/qa_set.csv": (
        "formal Kubernetes QA set (interface I2), gold quotes verbatim in the "
        "frozen corpus snapshot"
    ),
    "eval/qa_set_dev_v0.csv": (
        "development QA set on the four CORPUS_V0 Wikipedia documents, not the "
        "formal evaluation set"
    ),
}
QA_SET_STATUS_OTHER = "ad-hoc QA file, not a team artifact"
REVIEW_TABLE = ROOT / "eval" / "review" / "formal_qa_review.md"
# Suffixes that keep a declared token an occurrence of the same word. Chosen
# small on purpose: it covers English inflection, not compound words, so
# `fee` still does not match `feedback` while `gpu` still matches `gpus`.
INFLECTION_SUFFIX = r"(?:s|es|ed|d|ing|ly|er|ers|est)?"
# I4 calls the field `retrieved_chunk_ids`; `retrieved_ids` stays accepted so the
# records already covered by the first round of tests keep working.
RETRIEVED_KEYS = ("retrieved_chunk_ids", "retrieved_ids")
# An I4 artifact records the model that produced each answer. If every record
# names a scripted double, the run is a plumbing test, not an experiment, so a
# REAL label on it is called out instead of printed in silence.
MOCK_MODEL_HINTS = ("mock", "scripted", "stub", "double", "fake")


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
        """Tokens declared absent from the corpus (unanswerable items only).

        Their absence is a *necessary* condition for the item being
        unanswerable, never proof of it - see ``reviewed_by``.
        """
        if ABSENT_MARKER not in self.notes:
            return ()
        _, _, tail = self.notes.partition(ABSENT_MARKER)
        tail = tail.split(REVIEW_MARKER)[0]
        return tuple(
            part.strip().rstrip(".").lower() for part in tail.split(";") if part.strip()
        )

    @property
    def reviewed_by(self) -> str:
        """Human attestation that no answer exists in the corpus; empty if pending."""
        if REVIEW_MARKER not in self.notes:
            return ""
        _, _, tail = self.notes.partition(REVIEW_MARKER)
        return tail.split(ABSENT_MARKER)[0].split(";")[0].strip().rstrip(".")


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


def token_occurs(token: str, corpus: str) -> bool:
    """Does ``token`` occur in ``corpus`` as itself, or only inside a longer word?

    A bare substring test reports ``fee`` as present because of ``feedback``, so
    whoever writes a refusal item has to dodge accidental collisions instead of
    stating the fact. Anchoring the start at a word boundary removes that whole
    class of false hits. The end is deliberately looser: a declared word also
    counts when the corpus inflects it (``hallucination`` is present in
    ``hallucinations``), because a corpus that discusses hallucinations can very
    well answer a question about them. Whitespace inside a phrase is matched as
    a run, so a line break between two words cannot hide an occurrence. Every
    choice here can only make an absence claim harder to keep, never easier.
    """
    parts = [re.escape(part) for part in token.split()]
    if not parts:
        return False
    pattern = r"\s+".join(parts)
    if parts[0][:1].isalnum() or parts[0][0] == "_":
        pattern = rf"\b{pattern}"
    if parts[-1][-1:].isalnum() or parts[-1][-1] == "_":
        pattern = rf"{pattern}{INFLECTION_SUFFIX}\b"
    return re.search(pattern, corpus) is not None


def unreviewed_items(items: Sequence[QAItem]) -> list[str]:
    """Unanswerable items no group member has attested as genuinely unanswerable.

    ``ABSENT_TOKENS`` is machine-checkable and only necessary: a corpus can
    lack the literal string yet still answer the question in other words, or
    answer it partly and tempt a hallucinated completion. Deciding that is
    human work, recorded per item as ``REVIEWED_BY: <name>`` in ``notes``.
    """
    return sorted(item.qid for item in items if not item.is_answerable and not item.reviewed_by)


def validate_qa_set(
    items: Sequence[QAItem],
    documents: Sequence[Document],
    *,
    min_items: int = 20,
    require_reviewed: bool = False,
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
            if token_occurs(token, corpus):
                errors.append(f"{item.qid}: token {token!r} occurs in the corpus")
    unreviewed = unreviewed_items(items)
    if require_reviewed and unreviewed:
        errors.append(
            "unanswerable item(s) without a human REVIEWED_BY attestation: "
            f"{', '.join(unreviewed)} - absent tokens are a necessary condition, "
            "not proof that the corpus cannot answer"
        )
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
    raw join would leak a local path and differ on every laptop. ``main()``
    replaces the recorded arguments with the ones it was actually given, so a
    caller that imports ``main()`` (T2's experiment script) still gets truthful
    provenance instead of the driver's own command line. Path arguments are
    shortened the same way as everywhere else in the envelope. Values are quoted
    because ``run.md`` tells the reader to reproduce with this exact line: a
    free-text ``--executor`` with spaces would otherwise read back as many
    separate arguments.
    """
    return shlex.join(
        ["python", "-m", "eval.metrics", *(_relative(part) for part in _COMMAND_ARGS)]
    )


def _relative(path: str | Path) -> str:
    """Repo-relative when possible, so result files diff across machines."""
    try:
        file_path = Path(path).resolve()
    except (OSError, ValueError):  # not a path at all, just a CLI value
        return str(path)
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


# ---------------------------------------------------------------------------
# Interface I3: the four public metric functions (the only implementation)
# ---------------------------------------------------------------------------


def _require_outputs(items: Sequence[QAItem], outputs: dict[str, dict[str, object]]) -> None:
    """A run that skipped a question is not a zero, it is a broken artifact."""
    missing = [item.qid for item in items if item.qid not in outputs]
    if missing:
        raise QASetError(f"outputs file has no record for qid(s): {', '.join(missing)}")


def retrieval_hit_rate(
    items: Sequence[QAItem],
    spans: dict[str, EvidenceSpan],
    hits_by_qid: dict[str, Sequence[RetrievedChunk]],
    *,
    hit_levels: Sequence[int] = (1, 3),
    min_coverage: float = 0.5,
) -> dict[str, object]:
    """I3 hit@k: does the top-k context cover the gold span?

    Only answerable items enter both numerator and denominator: an
    unanswerable item has no gold span to hit, so counting it would silently
    deflate the rate. Their behaviour is measured by ``abstention_rates()``.

    Returns ``{"rates": {"hit@k": _rate}, "per_item": {qid: row},
    "n_answerable": int, "min_coverage": float}``.
    """
    answerable = [item for item in items if item.is_answerable]
    missing = [item.qid for item in answerable if item.qid not in hits_by_qid]
    if missing:
        raise QASetError(f"no retrieval result for qid(s): {', '.join(missing)}")
    counters = {level: 0 for level in hit_levels}
    per_item: dict[str, dict[str, object]] = {}
    for item in answerable:
        span = spans[item.qid]
        hits = list(hits_by_qid[item.qid])
        for level in hit_levels:
            if is_retrieval_hit(hits[:level], span, min_coverage=min_coverage):
                counters[level] += 1
        per_item[item.qid] = {
            "gold_span": [span.char_start, span.char_end],
            "span_length": span.length,
            "n_hits": len(hits),
            "first_hit_rank": _first_hit_rank(hits, span, min_coverage),
            "max_coverage": round(
                max((evidence_coverage(hit.chunk, span) for hit in hits), default=0.0), 4
            ),
            "top_chunks": [
                {"chunk_id": hit.chunk.chunk_id, "score": round(hit.score, 4)}
                for hit in hits[: max(hit_levels)]
            ],
        }
    return {
        "rates": {f"hit@{level}": _rate(counters[level], len(answerable)) for level in hit_levels},
        "per_item": per_item,
        "n_answerable": len(answerable),
        "min_coverage": min_coverage,
    }


def evaluate_retrieval(
    items: Sequence[QAItem],
    spans: dict[str, EvidenceSpan],
    hits_by_qid: dict[str, Sequence[RetrievedChunk]],
    *,
    hit_levels: Sequence[int] = (1, 3),
    min_coverage: float = 0.5,
) -> EvalResult:
    """Aggregator over ``retrieval_hit_rate()``: same numbers, plus provenance.

    Kept because the CLI and the first round of tests use it; it defines no
    second formula, so importing either entry point gives identical rates.
    """
    summary = retrieval_hit_rate(
        items, spans, hits_by_qid, hit_levels=hit_levels, min_coverage=min_coverage
    )
    answerable = [item for item in items if item.is_answerable]
    rows = [{"qid": item.qid, **summary["per_item"][item.qid]} for item in answerable]
    metrics: dict[str, object] = {
        "min_coverage": min_coverage,
        "n_items": len(items),
        "n_answerable": summary["n_answerable"],
        "n_unanswerable": len(items) - summary["n_answerable"],
        **summary["rates"],
    }
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


def unpack_record(
    item: QAItem, record: dict[str, object], chunk_of: Callable[[str], Chunk | None]
) -> dict[str, object]:
    """Rebuild the contract objects a recorded run refers to. No metric maths.

    T5 records ids and quotes (interface I4); the chunk text comes back from the
    store by id, which doubles as the provenance roundtrip check. The nested
    I4 shape is flattened here as well, so a caller that parsed the artifact
    itself and one that went through ``load_outputs()`` get the same result.
    """
    record = _flatten_answer(record)
    abstained = bool(record.get("abstained"))
    retrieved = _retrieved_from_record(record, chunk_of)
    citations, problems = citations_from_record(record, chunk_of)
    answer = Answer(
        question=item.question,
        answer_text=str(record.get("answer_text", "")),
        citations=tuple(citations),
        abstained=abstained,
        model=str(record.get("model", "unknown")),
        raw=str(record.get("raw", record.get("answer_text", ""))),
    )
    return {
        "answer": answer,
        "citations": citations,
        "retrieved": retrieved,
        "abstained": abstained,
        "structure_problems": problems,
    }


def abstention_rates(
    items: Sequence[QAItem], outputs: dict[str, dict[str, object]]
) -> dict[str, object]:
    """I3 refusal behaviour, read from ``Answer.abstained`` only (T5 owns that flag).

    ``correct_abstention_rate`` divides by the unanswerable items, the two
    directions are reported separately on purpose: one number combining both
    would hide a system that refuses everything.
    """
    _require_outputs(items, outputs)
    per_item: dict[str, dict[str, object]] = {}
    n_answerable = correct = wrong = answered = 0
    for item in items:
        abstained = bool(_flatten_answer(outputs[item.qid]).get("abstained"))
        expected = not item.is_answerable
        per_item[item.qid] = {"abstained": abstained, "expected_abstain": expected}
        if expected:
            correct += int(abstained)
        else:
            n_answerable += 1
            wrong += int(abstained)
            answered += int(not abstained)
    n_unanswerable = len(items) - n_answerable
    return {
        "correct_abstention_rate": _rate(correct, n_unanswerable),
        "false_abstention_rate": _rate(wrong, n_answerable),
        "n_answerable": n_answerable,
        "n_unanswerable": n_unanswerable,
        "n_answered": answered,
        "per_item": per_item,
    }


def citation_structure_rate(
    items: Sequence[QAItem],
    outputs: dict[str, dict[str, object]],
    *,
    chunk_of: Callable[[str], Chunk | None],
) -> dict[str, object]:
    """I3 structure rate: levels 1 + 2 only, ids resolve and quotes are verbatim.

    A perfect score here says nothing about whether the quote supports the
    answer - that is what ``answer_correctness()`` needs a judge for. Abstained
    rows stay out of the denominator: a refusal cites nothing, so there is no
    structure to check.
    """
    _require_outputs(items, outputs)
    per_item: dict[str, dict[str, object]] = {}
    checked = ok = 0
    for item in items:
        unpacked = unpack_record(item, outputs[item.qid], chunk_of)
        problems = list(unpacked["structure_problems"])
        valid: bool | None = None
        if not unpacked["abstained"]:
            checked += 1
            valid = not problems and verify_citation_structure(
                unpacked["answer"], unpacked["retrieved"]
            )
            if not valid and not problems:
                problems = ["ids or quote failed structure check"]
            ok += int(bool(valid))
        per_item[item.qid] = dict(unpacked, valid=valid, structure_problems=problems)
    return {"rate": _rate(ok, checked), "n_checked": checked, "per_item": per_item}


def answer_correctness(items: Sequence[QAItem], grades: dict[str, str]) -> dict[str, object]:
    """I3 correctness: the one number that needs a judge, never a formula.

    The denominator is the **answerable** items a judge actually graded:

    * unanswerable items are excluded even when a grade cell names them - their
      behaviour belongs to ``abstention_rates()``, and crediting a good refusal
      here would inflate the rate;
    * ungraded answerable items are reported through ``grading_coverage``, so a
      1/1 sample is never mistaken for a result over the whole set.

    ``unsure`` counts as not correct, as fixed in ``eval/judge_protocol.md``.
    """
    known = {item.qid for item in items}
    stray = sorted(set(grades) - known)
    if stray:
        raise QASetError(f"grading file names qid(s) absent from the QA set: {', '.join(stray)}")
    gradable = {item.qid for item in items if item.is_answerable}
    graded = {qid: grade for qid, grade in grades.items() if qid in gradable}
    for qid, grade in graded.items():
        if grade not in ALLOWED_GRADES:
            raise QASetError(f"grade for {qid} must be one of {ALLOWED_GRADES}, got {grade!r}")
    counts: dict[str, int] = dict.fromkeys(ALLOWED_GRADES, 0)
    for grade in graded.values():
        counts[grade] += 1
    return {
        "correctness": _rate(counts["correct"], len(graded)) if graded else PENDING_CORRECTNESS,
        "n_graded": len(graded),
        "n_gradable": len(gradable),
        "grading_coverage": _rate(len(graded), len(gradable)),
        "grade_counts": counts,
        "excluded_unanswerable": sorted(set(grades) - set(graded)),
    }


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
    """Aggregator over the four I3 functions, adding one row per item.

    hit@k here rates the context a run actually used, recomputed with
    ``retrieval_hit_rate()`` - the very function T2/T3 import, so a number in a
    report and a number produced by another task cannot drift apart.
    """
    grades = grades or {}
    abstention = abstention_rates(items, outputs)
    structure = citation_structure_rate(items, outputs, chunk_of=chunk_of)
    hits_by_qid = {qid: row["retrieved"] for qid, row in structure["per_item"].items()}
    retrieval = retrieval_hit_rate(
        items, spans, hits_by_qid, hit_levels=hit_levels, min_coverage=min_coverage
    )
    correctness = answer_correctness(items, grades)

    rows: list[dict[str, object]] = []
    for item in items:
        detail = structure["per_item"][item.qid]
        hit_row = retrieval["per_item"].get(item.qid, {})
        rows.append(
            {
                "qid": item.qid,
                "category": item.category,
                "abstained": abstention["per_item"][item.qid]["abstained"],
                "expected_abstain": not item.is_answerable,
                "n_retrieved": len(detail["retrieved"]),
                "first_hit_rank": hit_row.get("first_hit_rank"),
                "citation_ids": [citation.chunk_id for citation in detail["citations"]],
                "citation_structure_valid": detail["valid"],
                "structure_problems": detail["structure_problems"],
                "grade": grades.get(item.qid),
                "answer_text": detail["answer"].answer_text[:400],
            }
        )

    metrics: dict[str, object] = {
        "min_coverage": min_coverage,
        "n_items": len(items),
        "n_answerable": abstention["n_answerable"],
        "n_unanswerable": abstention["n_unanswerable"],
        "correct_abstention_rate": abstention["correct_abstention_rate"],
        "false_abstention_rate": abstention["false_abstention_rate"],
        "citation_structure_rate": structure["rate"],
        "answer_correctness": correctness["correctness"],
        "n_graded": correctness["n_graded"],
        "n_gradable": correctness["n_gradable"],
        "grading_coverage": correctness["grading_coverage"],
        "grade_counts": correctness["grade_counts"],
        **retrieval["rates"],
    }
    if correctness["excluded_unanswerable"]:
        metrics["grades_dropped_as_unanswerable"] = correctness["excluded_unanswerable"]
    return EvalResult(
        label="",
        mode="answers",
        config={
            "graded": bool(correctness["n_graded"]),
            "n_answered": abstention["n_answered"],
        },
        metrics=metrics,
        items=rows,
    )


def _retrieved_from_record(
    record: dict[str, object], chunk_of: Callable[[str], Chunk | None]
) -> list[RetrievedChunk]:
    """Rebuild the context a run actually used, by round-tripping chunk ids.

    I4 names the field ``retrieved_chunk_ids``; the earlier ``retrieved_ids`` is
    still read so first-round records and tests stay valid. hit@k here depends
    on rank order only, so a run that recorded plain ids is still scorable. No
    score is ever invented: an unrecorded score stays 0.0.
    """
    recorded: Sequence[object] = ()
    for key in RETRIEVED_KEYS:
        value = record.get(key)
        if value:
            recorded = value
            break
    hits: list[RetrievedChunk] = []
    for entry in recorded:
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

GRADE_COLUMNS = [
    "qid",
    "category",
    "question",
    "reference_answer",
    "answer_text",
    "citations",
    "abstained",
    "grade",
]
ALLOWED_GRADES = ("correct", "incorrect", "unsure")


def write_grading_sheet(path: str | Path, items: Sequence[QAItem], outputs: dict) -> Path:
    """Emit the sheet the two judges fill in by hand (see judge_protocol.md).

    Every row is listed so nothing is silently skipped, but only ``answerable``
    rows get a grade: ``answer_correctness()`` drops a grade on an
    unanswerable qid, since a successful refusal belongs to the abstention
    rates. The ``category`` and ``abstained`` columns make that visible on the
    sheet itself instead of relying on the instructions being read.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(GRADE_COLUMNS)
        for item in items:
            record = _flatten_answer(outputs.get(item.qid, {}))
            writer.writerow(
                [
                    item.qid,
                    item.category,
                    item.question,
                    item.reference_answer,
                    str(record.get("answer_text", "")),
                    ",".join(
                        str(entry.get("chunk_id", ""))
                        for entry in (record.get("citations") or [])
                        if isinstance(entry, dict)
                    ),
                    bool(record.get("abstained")),
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


def _parse_jsonl(text: str, path: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise QASetError(f"{path}:{line_number}: not one JSON object per line ({exc})") from exc
    return records


def _read_answer_records(path: Path) -> list[dict[str, object]]:
    """Read interface I4: JSON Lines first, plain JSON envelopes still accepted."""
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".jsonl", ".ndjson"):
        return _parse_jsonl(text, path)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        # a JSONL artifact saved under a .json name is still a JSONL artifact
        return _parse_jsonl(text, path)
    records = payload.get("items") if isinstance(payload, dict) else payload
    if not isinstance(records, list):
        raise QASetError(f"{path} must be a list of records or {{'items': [...]}}")
    return records


def _flatten_answer(record: dict[str, object]) -> dict[str, object]:
    """Accept the nested I4 shape ``{"qid": .., "answer": {..}, ..}``.

    The outer run-level fields (``retrieved_chunk_ids``, ``run_id``,
    ``config_ref``) win over anything repeated inside ``answer``, so a record
    written by T5 and a flat record written by an earlier draft score the same.
    """
    answer = record.get("answer")
    if not isinstance(answer, dict):
        return record
    flat = dict(answer)
    flat.update({key: value for key, value in record.items() if key != "answer"})
    return flat


def load_outputs(path: str | Path) -> dict[str, dict[str, object]]:
    """Load an answer artifact (interface I4) keyed by qid."""
    file_path = Path(path)
    if not file_path.is_file():
        raise QASetError(f"outputs file not found: {file_path}")
    records = _read_answer_records(file_path)
    by_qid: dict[str, dict[str, object]] = {}
    for record in records:
        if not isinstance(record, dict) or "qid" not in record:
            raise QASetError(f"{file_path}: every record needs a qid")
        flat = _flatten_answer(record)
        qid = str(flat["qid"])
        if qid in by_qid:
            raise QASetError(f"{file_path}: duplicate record for qid {qid!r}")
        by_qid[qid] = flat
    if not by_qid:
        raise QASetError(f"{file_path} contains no answer records")
    return by_qid


def artifact_provenance(outputs: dict[str, dict[str, object]]) -> dict[str, object]:
    """Pull the run-level identifiers T5 writes into each I4 record.

    One artifact must describe one run: two different ``run_id`` values in the
    same file mean two runs were concatenated, and their metrics could not be
    attributed to a configuration any more.
    """
    run_ids = sorted({str(record["run_id"]) for record in outputs.values() if record.get("run_id")})
    if len(run_ids) > 1:
        raise QASetError(
            f"answer artifact mixes run_id(s): {', '.join(run_ids)}; score one run per file"
        )
    refs = sorted(
        {str(record["config_ref"]) for record in outputs.values() if record.get("config_ref")}
    )
    models = sorted({str(record["model"]) for record in outputs.values() if record.get("model")})
    return {
        "run_id": run_ids[0] if run_ids else None,
        "config_ref": refs[0] if len(refs) == 1 else (refs or None),
        "models": models,
        "n_records": len(outputs),
    }


def looks_scripted(models: Sequence[str]) -> bool:
    """True when every model name in an artifact advertises a scripted double."""
    return bool(models) and all(
        any(hint in str(model).lower() for hint in MOCK_MODEL_HINTS) for model in models
    )


def resolve_answer_path(run_id: str | None, outputs: str | Path | None) -> Path:
    """``--run-id`` looks the artifact up in eval/answers/; ``--outputs`` wins."""
    if outputs:
        return Path(outputs)
    if not run_id:
        raise QASetError("score needs --outputs PATH or --run-id ID (see eval/answers/)")
    for suffix in ARTIFACT_SUFFIXES:
        candidate = ANSWERS_DIR / f"{run_id}{suffix}"
        if candidate.is_file():
            return candidate
    expected = ", ".join(f"{run_id}{suffix}" for suffix in ARTIFACT_SUFFIXES)
    raise QASetError(
        f"no answer artifact for --run-id {run_id!r} in {_relative(ANSWERS_DIR)}: {expected}"
    )


# ---------------------------------------------------------------------------
# CLI wiring (the only place that touches config, the store, or the network)
# ---------------------------------------------------------------------------


def _settings(args: argparse.Namespace) -> Settings:
    settings = load_settings(args.config)
    if getattr(args, "chunking", None):
        settings = replace(settings, chunk_strategy=args.chunking)
    return settings


def _sha256(path: str | Path) -> str:
    """First 12 hex of a file: cheap identity, so a snapshot swap is visible."""
    file_path = Path(path)
    if not file_path.is_file():
        return ""
    return hashlib.sha256(file_path.read_bytes()).hexdigest()[:12]


def _frozen_payload() -> dict[str, object]:
    """Interface I1 as a dict, or ``{}`` when nothing is frozen yet."""
    if not FROZEN_MANIFEST.is_file():
        return {}
    try:
        payload = json.loads(FROZEN_MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def frozen_doc_ids() -> frozenset[str]:
    """Document ids the frozen snapshot declares; empty before I1 lands."""
    documents = _frozen_payload().get("documents")
    if not isinstance(documents, list):
        return frozenset()
    return frozenset(
        str(doc["doc_id"])
        for doc in documents
        if isinstance(doc, dict) and doc.get("doc_id")
    )


def _corpus_ref(settings: Settings) -> dict[str, object]:
    """Which corpus snapshot these numbers belong to (interface I1 / I5).

    Until T1 freezes `frozen_manifest.json`, the reference points at the
    development manifest and says so through `corpus_frozen: false`; a reader
    can then tell a development run from a formal one without asking anyone.
    """
    frozen = FROZEN_MANIFEST.is_file()
    ref = FROZEN_MANIFEST if frozen else settings.manifest
    corpus_id = _frozen_payload().get("corpus_id")
    label = str(corpus_id) if corpus_id else _relative(ref)
    return {"corpus_ref": f"{label}@{_sha256(ref)}", "corpus_frozen": frozen}


def qa_corpus_binding(items: Sequence[QAItem]) -> dict[str, object]:
    """Which documents a QA set cites, and whether the snapshot lists them.

    A gold quote that resolves in ``data/raw/`` proves the quote is verbatim,
    not that it belongs to the corpus version the run claims to describe: the
    file could have been swapped under it. Checking the cited ``doc_id`` values
    against ``frozen_manifest.json`` turns that claim into a machine test.
    """
    cited = sorted({item.evidence_doc_id for item in items if item.evidence_doc_id})
    frozen = frozen_doc_ids()
    outside = [doc_id for doc_id in cited if doc_id not in frozen]
    return {
        "qa_cited_docs": cited,
        "qa_cited_doc_count": len(cited),
        "qa_docs_outside_frozen_snapshot": outside,
        "qa_corpus_binding_verified": bool(frozen) and not outside,
    }


def qa_set_status(qa_path: str | Path = DEFAULT_QA, items: Sequence[QAItem] = ()) -> str:
    """What this QA file is, assembled from the file and its rows.

    One global constant cannot describe two committed sets, and a status copied
    from a flag is a claim nobody verified. The path fixes which set it is; the
    rows then fix whether their citations land inside the frozen snapshot and
    whether a human has signed off every refusal label.
    """
    label = _relative(qa_path)
    stem = QA_SET_STATUS_BY_FILE.get(label, QA_SET_STATUS_OTHER)
    if not items:
        return stem
    parts = [stem]
    binding = qa_corpus_binding(items)
    if not binding["qa_corpus_binding_verified"]:
        outside = binding["qa_docs_outside_frozen_snapshot"]
        parts.append(
            "frozen snapshot not found" if not outside else f"cites non-snapshot doc(s): {outside}"
        )
    pending = len(unreviewed_items(items))
    if pending:
        parts.append(f"{pending} refusal label(s) awaiting a human REVIEWED_BY")
    return "; ".join(parts)


def _qa_ref(qa_path: str | Path, items: Sequence[QAItem] = ()) -> dict[str, object]:
    """Which QA file, what it is, and whether its gold binds to the snapshot."""
    ref = {"qa_set_ref": f"{_relative(qa_path)}@{_sha256(qa_path)}"}
    if items:
        return ref | {"qa_set_status": qa_set_status(qa_path, items)} | qa_corpus_binding(items)
    return ref | {"qa_set_status": qa_set_status(qa_path)}


def _config_snapshot(
    settings: Settings,
    items: Sequence[QAItem],
    *,
    qa_path: str | Path = DEFAULT_QA,
    min_coverage: float | None = None,
) -> dict[str, object]:
    """Interface I5 field names, so a T2 row and a T4 row sit side by side."""
    embedding_model = (
        settings.local_model if settings.embedding_provider == "local" else settings.api_model
    )
    return {
        "strategy": settings.chunk_strategy,
        "size": settings.chunk_size,
        "overlap": settings.chunk_overlap,
        "top_k": settings.top_k,
        "min_coverage": min_coverage,
        "embedding": f"{settings.embedding_provider}:{embedding_model}",
        "embedding_dimension": settings.embedding_dimension,
        "llm": settings.llm_model,
        "temperature": settings.temperature,
        "max_tokens": settings.max_tokens,
        "collection": settings.collection_name,
        "python": sys.version.split()[0],
        "qa_items": len(items),
        **_corpus_ref(settings),
        **_qa_ref(qa_path, items),
    }


def assert_formal_inputs(
    settings: Settings, items: Sequence[QAItem], qa_path: str | Path = DEFAULT_QA
) -> None:
    """Refuse to publish a run as formal while the inputs are still moving.

    The flag is an assertion by the person running it; the checks below are
    what this machine can verify: the I1 snapshot exists, the gold quotes bind
    to documents that snapshot lists, the set read is the team artifact at the
    I2 path rather than the development file, and every refusal label carries a
    human attestation. They are deliberately not a proof that the QA set was
    reviewed by the whole group - that lives in the PR.
    """
    problems: list[str] = []
    label = _relative(qa_path)
    if not FROZEN_MANIFEST.is_file():
        problems.append(
            f"{_relative(FROZEN_MANIFEST)} is missing: the I1 corpus snapshot is not frozen yet"
        )
    if label not in QA_SET_STATUS_BY_FILE:
        problems.append(
            f"{label} is not a committed team QA artifact; the formal set "
            "lives at the single I2 path eval/qa_set.csv"
        )
    elif label != _relative(DEFAULT_QA):
        problems.append(f"{label} is the development set; a formal run reads eval/qa_set.csv")
    elif not qa_corpus_binding(items)["qa_corpus_binding_verified"]:
        problems.append(
            "gold quotes do not bind to the frozen snapshot: "
            f"{qa_corpus_binding(items)['qa_docs_outside_frozen_snapshot'] or 'no doc ids listed'}"
        )
    unreviewed = unreviewed_items(items)
    if unreviewed:
        problems.append(
            f"unanswerable item(s) without a REVIEWED_BY attestation: {', '.join(unreviewed)}"
        )
    if problems:
        raise QASetError(
            "--formal refused, this run is not on frozen inputs yet:\n"
            + "\n".join(f"  - {problem}" for problem in problems)
            + "\nDevelopment numbers belong in eval/results/raw/ via --out, not in summary/."
            + f"\nSign the refusal labels in {_relative(REVIEW_TABLE)} first."
        )


def _git_user() -> str:
    """The local git identity, or an explicit gap for whoever ran it to fill in."""
    try:
        completed = subprocess.run(
            ["git", "config", "user.name"], capture_output=True, text=True, timeout=5, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return "UNKNOWN - record who ran this by hand"
    return completed.stdout.strip() or "UNKNOWN - record who ran this by hand"


def write_summary(
    result: EvalResult, directory: str | Path, *, executor: str | None = None
) -> list[Path]:
    """Write the aggregate bundle `eval/results/README.md` asks for.

    Three files, one experiment directory: `config.json` (I5 snapshot),
    `metrics.json` (aggregates with command and refs) and `run.md` (how to
    reproduce). MOCK never gets here: a fixture number sitting next to a real
    one is how fabricated results end up in a report.
    """
    if result.label.upper() == "MOCK":
        raise QASetError(
            "--summary-dir refuses a MOCK run; MOCK numbers are not experiment results"
        )
    target = Path(directory)
    target.mkdir(parents=True, exist_ok=True)
    payload = result.to_payload()
    config = dict(payload["config"]) | {"label": result.label, "mode": result.mode}
    correctness = result.metrics.get("answer_correctness")
    judge = (
        "not applicable: retrieval-only run"
        if result.mode == "retrieval"
        else PENDING_CORRECTNESS
        if isinstance(correctness, str)
        else f"human grades on {result.metrics.get('n_graded')} answerable item(s); "
        "citation structure is reported separately and is not correctness"
    )
    metrics = {
        "experiment_id": target.name,
        "generated_at": payload["generated_at"],
        "command": payload["command"],
        "config_ref": "config.json",
        "corpus_ref": config.get("corpus_ref"),
        "qa_set_ref": config.get("qa_set_ref"),
        "label": result.label,
        "mode": result.mode,
        "metrics": result.metrics,
        "judge": judge,
    }
    written = [
        _write_json(target / "config.json", config),
        _write_json(target / "metrics.json", metrics),
    ]
    lines = [
        f"# {target.name}",
        "",
        f"- command: `{payload['command']}`",
        f"- date: {payload['generated_at']}",
        f"- executor: {executor or _git_user()}",
        "- exit code: 0 (this file is written by the run that produced it)",
        f"- corpus: {config.get('corpus_ref')} (frozen: {config.get('corpus_frozen')})",
        f"- QA set: {config.get('qa_set_ref')} ({config.get('qa_set_status')})",
        "",
        "Reproduce from the repository root with the command above; the index must",
        "already exist (`python -m ragkit.cli ingest`).",
        "",
        "| metric | hits | n | rate |",
        "| --- | --- | --- | --- |",
    ]
    for key, value in result.metrics.items():
        if isinstance(value, dict) and "rate" in value:
            lines.append(f"| `{key}` | {value['hits']} | {value['n']} | {value['rate']} |")
        else:
            lines.append(f"| `{key}` | - | - | {value} |")
    summary = target / "run.md"
    summary.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return [*written, summary]


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return path


def _summary_gate(args: argparse.Namespace, settings: Settings, items: Sequence[QAItem]) -> None:
    """Checked before the expensive work, so a refused run wastes nothing."""
    if getattr(args, "formal", False) and not getattr(args, "summary_dir", None):
        raise QASetError("--formal is only meaningful together with --summary-dir")
    if getattr(args, "summary_dir", None):
        if not getattr(args, "formal", False):
            raise QASetError(
                "--summary-dir needs --formal: development numbers stay in "
                "eval/results/raw/ (see eval/results/README.md)"
            )
        assert_formal_inputs(settings, items, qa_path=args.qa)


def _write_summary_if_asked(args: argparse.Namespace, result: EvalResult) -> None:
    directory = getattr(args, "summary_dir", None)
    if not directory:
        return
    for path in write_summary(result, directory, executor=getattr(args, "executor", None)):
        print(f"wrote {_relative(path)}")


def cmd_validate(args: argparse.Namespace) -> int:
    qa_path = Path(args.qa)
    items = load_qa(qa_path)
    documents = load_documents(args.manifest)
    spans = validate_qa_set(
        items, documents, min_items=args.min_items, require_reviewed=args.require_reviewed
    )
    answerable = [item for item in items if item.is_answerable]
    unanswerable = [item for item in items if not item.is_answerable]
    per_doc: dict[str, int] = {}
    for item in answerable:
        per_doc[item.evidence_doc_id] = per_doc.get(item.evidence_doc_id, 0) + 1
    print(f"[REAL] validated {qa_path.name}: {len(items)} items "
          f"({len(answerable)} answerable, {len(unanswerable)} unanswerable)")
    print(f"documents consulted: {len(documents)}; "
          f"all {len(spans)} gold quotes resolve to a source character span")
    for doc_id, count in sorted(per_doc.items()):
        print(f"  {doc_id:26} {count:3d} answerable items")
    print("gold span sample (strategy-independent):")
    for item in answerable[:3]:
        span = spans[item.qid]
        print(f"  {item.qid} {span.doc_id} chars {span.char_start}-{span.char_end}")
    print(f"unanswerable absence checks: "
          f"{sum(len(item.absent_tokens) for item in unanswerable)} tokens "
          "confirmed absent from the corpus as whole words - a NECESSARY condition "
          "only, the absence of a word does not prove the corpus cannot answer the question")
    unreviewed = unreviewed_items(items)
    print(f"human review of unanswerable labels: "
          f"{len(unanswerable) - len(unreviewed)}/{len(unanswerable)} carry REVIEWED_BY"
          + (f" (pending: {', '.join(unreviewed)})" if unreviewed else ""))
    if unreviewed and _relative(qa_path) == _relative(DEFAULT_QA) and REVIEW_TABLE.is_file():
        print(f"  checklist for the reviewers: {_relative(REVIEW_TABLE)}")
    binding = qa_corpus_binding(items)
    frozen_ids = frozen_doc_ids()
    print(f"corpus binding: {binding['qa_cited_doc_count']} doc(s) cited, "
          f"verified against the frozen snapshot: {binding['qa_corpus_binding_verified']}"
          + (f" (outside: {binding['qa_docs_outside_frozen_snapshot']})"
             if binding["qa_docs_outside_frozen_snapshot"] else ""))
    if frozen_ids:
        uncovered = sorted(frozen_ids - set(binding["qa_cited_docs"]))
        print(f"frozen documents with no answerable item ({len(uncovered)}/{len(frozen_ids)}): "
              f"{', '.join(uncovered) if uncovered else 'none'}")
    frozen_note = (
        "present" if FROZEN_MANIFEST.is_file() else f"absent: {_relative(FROZEN_MANIFEST)}"
    )
    print(f"corpus checked against: {_relative(args.manifest)}@{_sha256(args.manifest)}; "
          f"frozen snapshot (I1) {frozen_note}")
    print(f"QA set status: {qa_set_status(qa_path, items)}")
    return 0


def cmd_retrieval(args: argparse.Namespace) -> int:
    settings = _settings(args)
    items = load_qa(args.qa)
    spans = validate_qa_set(items, load_documents(settings.manifest), min_items=args.min_items)
    _summary_gate(args, settings, items)
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
    result.label = args.label
    result.config = _config_snapshot(
        settings, items, qa_path=args.qa, min_coverage=args.min_coverage
    )
    print_summary(result, print_items=args.print_items)
    if args.out:
        print(f"\nwrote {result.write(args.out)}")
    _write_summary_if_asked(args, result)
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    settings = _settings(args)
    items = load_qa(args.qa)
    spans = validate_qa_set(items, load_documents(settings.manifest), min_items=args.min_items)
    _summary_gate(args, settings, items)
    outputs_path = resolve_answer_path(args.run_id, args.outputs)
    outputs = load_outputs(outputs_path)
    provenance = artifact_provenance(outputs)
    if args.run_id and provenance["run_id"] and provenance["run_id"] != args.run_id:
        raise QASetError(
            f"--run-id {args.run_id!r} does not match the run_id "
            f"{provenance['run_id']!r} recorded in {_relative(outputs_path)}"
        )
    # ``append`` on --grades exists only to make a repeated flag visible; the
    # check itself runs in ``main()`` so it fires before any index or artifact
    # is touched. Correctness comes from ONE reconciled sheet.
    grade_files = list(args.grades or [])
    grades = load_grades(grade_files[0]) if grade_files else None
    if args.label == "REAL" and looks_scripted(provenance["models"]):
        print(
            "WARNING: --label REAL, but every record in this artifact names a scripted "
            f"double ({', '.join(provenance['models'])}). Pass --label MOCK: these numbers "
            "test the plumbing, they are not an experiment result.",
            file=sys.stderr,
        )
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
    result.config = _config_snapshot(
        settings, items, qa_path=args.qa, min_coverage=args.min_coverage
    ) | {
        "outputs_file": _relative(outputs_path),
        "grades_file": _relative(grade_files[0]) if grade_files else None,
        **provenance,
    }
    print(f"[{result.label}] scoring answer run: {_relative(outputs_path)} "
          f"(run_id={provenance['run_id']}, records={provenance['n_records']})")
    print_summary(result, print_items=args.print_items)
    if args.grading_sheet:
        print(f"wrote grading sheet {write_grading_sheet(args.grading_sheet, items, outputs)}")
    if args.out:
        print(f"wrote {result.write(args.out)}")
    _write_summary_if_asked(args, result)
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
            "retrieved_chunk_ids": [hit.chunk.chunk_id for hit in hits],
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
        if isinstance(value, dict) and "rate" in value:
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
    validate.add_argument(
        "--require-reviewed",
        action="store_true",
        help="fail unless every unanswerable item carries REVIEWED_BY in its notes",
    )
    validate.set_defaults(func=cmd_validate)

    def add_run_args(cmd: argparse.ArgumentParser) -> None:
        cmd.add_argument(
            "--chunking",
            choices=("fixed", "paragraph"),
            default=None,
            help="override config.toml for this run (used by the T2 comparison)",
        )
        cmd.add_argument("--label", default="REAL", help="REAL or MOCK, printed and stored")
        cmd.add_argument(
            "--summary-dir",
            type=Path,
            default=None,
            help="write config.json / metrics.json / run.md here; needs --formal",
        )
        cmd.add_argument(
            "--formal",
            action="store_true",
            help="assert frozen corpus (I1) and reviewed QA (I2); refuses if not verifiable",
        )
        cmd.add_argument(
            "--executor",
            default=None,
            help="who ran this, recorded in run.md (default: git config user.name)",
        )

    retrieval = sub.add_parser(
        "retrieval", help="REAL hit@k over the built index (needs `cli ingest`, no API key)"
    )
    add_common(retrieval)
    add_run_args(retrieval)
    retrieval.set_defaults(func=cmd_retrieval)

    score = sub.add_parser("score", help="abstention, citation structure, correctness from a run")
    add_common(score)
    add_run_args(score)
    score.add_argument(
        "--outputs",
        type=Path,
        default=None,
        help="answer artifact (interface I4): .jsonl, .json list or {'items': [...]}",
    )
    score.add_argument(
        "--run-id",
        default=None,
        help="look for eval/answers/<run-id>.jsonl instead of passing --outputs",
    )
    score.add_argument(
        "--grades",
        action="append",
        type=Path,
        metavar="CSV",
        help="human grading csv (see judge_protocol.md); exactly one, so a "
        "repeated flag fails instead of silently keeping the last sheet",
    )
    score.add_argument(
        "--grading-sheet", type=Path, default=None, help="write an empty grading sheet here"
    )
    score.set_defaults(func=cmd_score)

    demo = sub.add_parser("mock-demo", help="MOCK plumbing exercise, never an experiment")
    add_common(demo)
    demo.set_defaults(func=cmd_mock_demo)
    return parser


def _reject_duplicate_flags(args: argparse.Namespace) -> None:
    """Refuse a file flag that only makes sense once, instead of keeping the last.

    With the original single-value action, ``--grades a.csv --grades b.csv``
    silently scored only ``b.csv`` - the likeliest way for one person's sheet to
    reach the report as "two independent raters agreed". The two sheets must be
    reconciled first: disagreements go to a third reader, whose call becomes the
    single recorded grade (``eval/judge_protocol.md`` §1).
    """
    grades = getattr(args, "grades", None)
    if isinstance(grades, list) and len(grades) > 1:
        raise QASetError(
            "--grades takes exactly one csv, got "
            f"{len(grades)} ({', '.join(_relative(p) for p in grades)}). Reconcile "
            "the two sheets into one file per eval/judge_protocol.md before scoring; "
            "the reason they must be reconciled by a human is exactly why they are "
            "not accepted as two inputs here."
        )


def main(argv: Sequence[str] | None = None) -> int:
    global _COMMAND_ARGS
    if argv is not None:
        _COMMAND_ARGS = [str(part) for part in argv]
    args = build_parser().parse_args(argv)
    try:
        _reject_duplicate_flags(args)
        return int(args.func(args))
    except QASetError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

"""Tests for T4: the QA set, the metric kernel, and the grading plumbing.

Everything here is OFFLINE: no API key, no model download, no network.

Two kinds of assertions live in this file and they are deliberately different:
  * GOLD checks read eval/qa_set.csv against the real data/raw/ corpus. That is
    a file-consistency check, not an experiment - it proves the gold standard
    is verbatim and strategy-independent.
  * METRIC checks use synthetic hits/answers built from tests/fakes.py doubles.
    They are labelled MOCK and assert that a number follows from its inputs.
    No expected rate is ever hard-coded: each test computes what its own
    constructed data implies.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from eval.evidence import locate_evidence
from eval.metrics import (
    ALLOWED_GRADES,
    PENDING_CORRECTNESS,
    QA_COLUMNS,
    QAItem,
    QASetError,
    _relative,
    citations_from_record,
    evaluate_answers,
    evaluate_retrieval,
    load_grades,
    load_outputs,
    load_qa,
    parse_hits,
    validate_qa_set,
    write_grading_sheet,
)
from ragkit.config import ROOT
from ragkit.contracts import Chunk, RetrievedChunk
from ragkit.loaders import load_documents

QA_PATH = ROOT / "eval" / "qa_set.csv"
MANIFEST = ROOT / "data" / "raw" / "manifest.json"
DOC_ID = "rag_wikipedia"
QUOTE_2020 = (
    "The technique was first proposed in 2020 and has since become a widely "
    "adopted approach in modern AI systems."
)


@pytest.fixture(scope="module")
def documents():
    return load_documents(MANIFEST)


@pytest.fixture(scope="module")
def qa_items():
    return load_qa(QA_PATH)


def _write_qa(path: Path, rows: list[list[str]], columns=None) -> Path:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(columns or QA_COLUMNS)
        writer.writerows(rows)
    return path


def _answerable(qid: str, quote: str, doc_id: str = DOC_ID) -> QAItem:
    return QAItem(
        qid=qid,
        question=f"MOCK question {qid}?",
        reference_answer="MOCK reference",
        evidence_doc_id=doc_id,
        evidence_quote=quote,
        category="answerable",
        notes="MOCK fixture data, never an experiment",
    )


def _unanswerable(qid: str, tokens: str = "zzznotaword") -> QAItem:
    return QAItem(
        qid=qid,
        question=f"MOCK unanswerable {qid}?",
        reference_answer="",
        evidence_doc_id="",
        evidence_quote="",
        category="unanswerable",
        notes=f"MOCK refusal case. ABSENT_TOKENS: {tokens}",
    )


def _span(documents, quote: str):
    return locate_evidence(documents, DOC_ID, quote)


def _chunk(documents, start: int, end: int, chunk_id: str) -> Chunk:
    text = next(doc.text for doc in documents if doc.doc_id == DOC_ID)
    return Chunk(
        chunk_id=chunk_id,
        doc_id=DOC_ID,
        text=text[start:end],
        char_start=start,
        char_end=end,
        strategy="fixed",
        index=0,
        title="Retrieval-augmented generation",
        source_uri="https://example.invalid",
    )


def _hits(chunks: list[Chunk]) -> list[RetrievedChunk]:
    return [
        RetrievedChunk(chunk=chunk, score=0.5, rank=rank)
        for rank, chunk in enumerate(chunks, start=1)
    ]


def _record(qid: str, chunk: Chunk, *, answer_text: str = "MOCK answer.", abstained=False):
    return {
        "qid": qid,
        "abstained": abstained,
        "answer_text": answer_text,
        "citations": [
            {"chunk_id": chunk.chunk_id, "doc_id": chunk.doc_id, "quote": chunk.text[:40]}
        ],
        "retrieved_ids": [chunk.chunk_id],
    }


# ---------------------------------------------------------------------------
# GOLD: the committed QA set against the real corpus
# ---------------------------------------------------------------------------


def test_qa_set_is_large_enough_and_has_both_categories(qa_items):
    assert len(qa_items) >= 20, "the assignment needs at least 20 QA pairs"
    categories = {item.category for item in qa_items}
    assert categories == {"answerable", "unanswerable"}


def test_every_gold_quote_is_verbatim_source_text(qa_items, documents):
    spans = validate_qa_set(qa_items, documents)
    answerable = [item for item in qa_items if item.is_answerable]
    assert len(spans) == len(answerable)
    for item in answerable:
        span = spans[item.qid]
        source = next(doc.text for doc in documents if doc.doc_id == span.doc_id)
        assert source[span.char_start : span.char_end] == item.evidence_quote
        assert span.length == len(item.evidence_quote)


def test_gold_spans_are_unique_per_qid_and_cover_every_document(qa_items, documents):
    spans = validate_qa_set(qa_items, documents)
    assert len({(s.doc_id, s.char_start, s.char_end) for s in spans.values()}) == len(spans)
    covered = {span.doc_id for span in spans.values()}
    assert covered == {doc.doc_id for doc in documents}


def test_unanswerable_items_declare_tokens_that_are_really_absent(qa_items, documents):
    unanswerable = [item for item in qa_items if not item.is_answerable]
    assert len(unanswerable) >= 5, "abstention needs enough refusal cases to be measurable"
    corpus = " ".join(doc.text.lower() for doc in documents)
    for item in unanswerable:
        assert item.absent_tokens, f"{item.qid} declares no ABSENT_TOKENS"
        assert all(token not in corpus for token in item.absent_tokens)


def test_answerable_items_always_have_a_reference_answer(qa_items):
    assert all(item.reference_answer for item in qa_items if item.is_answerable)
    assert all(not item.reference_answer for item in qa_items if not item.is_answerable)


def test_quotes_with_internal_double_quotes_survive_csv_roundtrip(qa_items):
    quoted = [item for item in qa_items if '"' in item.evidence_quote]
    assert quoted, "qa_set.csv is expected to include at least one quoted gold quote"
    for item in quoted:
        assert '""' not in item.evidence_quote  # csv.reader must have unescaped it


# ---------------------------------------------------------------------------
# Rejected inputs: a malformed set must fail loudly, never silently
# ---------------------------------------------------------------------------


def test_non_verbatim_gold_quote_is_rejected(tmp_path, documents):
    path = _write_qa(
        tmp_path / "qa.csv",
        [["X01", "Q?", "A", DOC_ID, "RAG was invented in 1999 by nobody", "answerable", ""]],
    )
    items = load_qa(path)
    with pytest.raises(QASetError, match="not verbatim"):
        validate_qa_set(items, documents, min_items=1)


def test_unknown_doc_id_is_rejected(tmp_path, documents):
    rows = [["X01", "Q?", "A", "ghost_doc", QUOTE_2020, "answerable", ""]]
    with pytest.raises(QASetError, match="unknown evidence_doc_id"):
        validate_qa_set(load_qa(_write_qa(tmp_path / "qa.csv", rows)), documents, min_items=1)


def test_answerable_row_without_evidence_is_rejected(tmp_path, documents):
    path = _write_qa(tmp_path / "qa.csv", [["X01", "Q?", "A", "", "", "answerable", ""]])
    with pytest.raises(QASetError, match="need evidence_doc_id"):
        validate_qa_set(load_qa(path), documents, min_items=1)


def test_unanswerable_row_with_evidence_is_rejected(tmp_path, documents):
    path = _write_qa(
        tmp_path / "qa.csv", [["X01", "Q?", "", DOC_ID, QUOTE_2020, "unanswerable", ""]]
    )
    with pytest.raises(QASetError, match="must carry no gold evidence"):
        validate_qa_set(load_qa(path), documents, min_items=1)


def test_unanswerable_token_that_exists_in_the_corpus_is_rejected(tmp_path, documents):
    rows = [["X01", "Q?", "", "", "", "unanswerable", "ABSENT_TOKENS: hallucination"]]
    with pytest.raises(QASetError, match="occurs in the corpus"):
        validate_qa_set(load_qa(_write_qa(tmp_path / "qa.csv", rows)), documents, min_items=1)


def test_too_small_a_set_is_rejected(tmp_path, documents):
    path = _write_qa(
        tmp_path / "qa.csv", [["X01", "Q?", "A", DOC_ID, QUOTE_2020, "answerable", ""]]
    )
    with pytest.raises(QASetError, match="at least 20"):
        validate_qa_set(load_qa(path), documents, min_items=20)


def test_duplicate_qid_is_rejected(tmp_path):
    row = ["X01", "Q?", "", "", "", "unanswerable", "ABSENT_TOKENS: zzznotaword"]
    path = _write_qa(tmp_path / "qa.csv", [row, list(row)])
    with pytest.raises(QASetError, match="duplicate qid"):
        load_qa(path)


def test_bad_header_is_rejected(tmp_path):
    path = _write_qa(
        tmp_path / "qa.csv", [["X01", "Q?", "A", DOC_ID, QUOTE_2020, "answerable", ""]],
        columns=["qid", "question", "expected_chunk_ids", "category"],
    )
    with pytest.raises(QASetError, match="header must be exactly"):
        load_qa(path)


def test_unknown_category_is_rejected(tmp_path):
    path = _write_qa(
        tmp_path / "qa.csv", [["X01", "Q?", "A", DOC_ID, QUOTE_2020, "maybe", ""]]
    )
    with pytest.raises(QASetError, match="category must be one of"):
        load_qa(path)


def test_missing_file_is_rejected(tmp_path):
    with pytest.raises(QASetError, match="not found"):
        load_qa(tmp_path / "nope.csv")


# ---------------------------------------------------------------------------
# MOCK: retrieval metrics
# ---------------------------------------------------------------------------


def test_hit_at_1_and_hit_at_3_are_computed_from_rank_order(documents):
    span = _span(documents, QUOTE_2020)
    item = _answerable("M01", QUOTE_2020)
    gold = _chunk(documents, span.char_start, span.char_end, "rag_wikipedia#0007")
    noise = _chunk(documents, 0, 165, "rag_wikipedia#0000")
    hits = _hits([noise, gold])
    result = evaluate_retrieval([item], {item.qid: span}, {item.qid: hits}, hit_levels=(1, 3))
    assert result.metrics["hit@1"] == {"hits": 0, "n": 1, "rate": 0.0}
    assert result.metrics["hit@3"] == {"hits": 1, "n": 1, "rate": 1.0}
    assert result.items[0]["first_hit_rank"] == 2
    assert result.items[0]["max_coverage"] == 1.0


def test_unanswerable_items_never_enter_the_hit_denominator(documents):
    span = _span(documents, QUOTE_2020)
    gold = _chunk(documents, span.char_start, span.char_end, "rag_wikipedia#0007")
    items = [_answerable("M01", QUOTE_2020), _unanswerable("N01")]
    hits = _hits([gold])
    result = evaluate_retrieval(
        items, {items[0].qid: span}, {items[0].qid: hits}, hit_levels=(1,)
    )
    assert result.metrics["n_answerable"] == 1
    assert result.metrics["n_unanswerable"] == 1
    assert result.metrics["hit@1"]["n"] == 1
    assert len(result.items) == 1, "unanswerable rows are scored elsewhere, not here"


def test_partial_coverage_is_a_hit_only_above_min_coverage(documents):
    span = _span(documents, QUOTE_2020)
    partial_end = span.char_start + int(span.length * 0.6)
    partial = _chunk(documents, span.char_start, partial_end, "rag#0001")
    item = _answerable("M01", QUOTE_2020)
    hits = _hits([partial])
    loose = evaluate_retrieval(
        [item], {item.qid: span}, {item.qid: hits}, hit_levels=(1,), min_coverage=0.5
    )
    strict = evaluate_retrieval(
        [item], {item.qid: span}, {item.qid: hits}, hit_levels=(1,), min_coverage=0.9
    )
    assert loose.metrics["hit@1"]["rate"] == 1.0
    assert strict.metrics["hit@1"]["rate"] == 0.0
    assert strict.metrics["min_coverage"] == 0.9
    assert 0.5 < loose.items[0]["max_coverage"] < 0.9


def test_one_more_hit_raises_the_rate_nothing_else(documents):
    """Metrics follow their inputs: adding a hit changes the rate, all else equal."""
    span = _span(documents, QUOTE_2020)
    gold = _chunk(documents, span.char_start, span.char_end, "rag_wikipedia#0007")
    noise = _chunk(documents, 0, 165, "rag_wikipedia#0000")
    second = _answerable("M02", QUOTE_2020)
    items = [_answerable("M01", QUOTE_2020), second]
    spans = {item.qid: span for item in items}
    before = evaluate_retrieval(
        items, spans, {items[0].qid: _hits([gold]), items[1].qid: _hits([noise])}, hit_levels=(1,)
    )
    after = evaluate_retrieval(
        items, spans, {items[0].qid: _hits([gold]), items[1].qid: _hits([gold])}, hit_levels=(1,)
    )
    assert before.metrics["hit@1"]["rate"] == 0.5
    assert after.metrics["hit@1"]["rate"] == 1.0


def test_missing_retrieval_result_is_an_error_not_a_zero(documents):
    span = _span(documents, QUOTE_2020)
    item = _answerable("M01", QUOTE_2020)
    with pytest.raises(QASetError, match="no retrieval result"):
        evaluate_retrieval([item], {item.qid: span}, {}, hit_levels=(1,))


def test_parse_hits_dedupes_and_validates():
    assert parse_hits("1,3,3") == (1, 3)
    for bad in ("", "0", "-1", "a"):
        with pytest.raises(QASetError):
            parse_hits(bad)


# ---------------------------------------------------------------------------
# MOCK: answer scoring, abstention, citation structure, grading
# ---------------------------------------------------------------------------


def _answer_inputs(documents):
    span = _span(documents, QUOTE_2020)
    gold = _chunk(documents, span.char_start, span.char_end, "rag_wikipedia#0007")
    items = [_answerable("M01", QUOTE_2020), _unanswerable("N01")]
    outputs = {
        "M01": _record("M01", gold),
        "N01": {"qid": "N01", "abstained": True, "answer_text": "refused", "citations": []},
    }
    return items, {items[0].qid: span}, outputs, gold


def test_abstention_rates_are_separate_and_directional(documents):
    items, spans, outputs, _ = _answer_inputs(documents)
    result = evaluate_answers(items, spans, outputs, chunk_of=lambda cid: None)
    assert result.metrics["correct_abstention_rate"] == {"hits": 1, "n": 1, "rate": 1.0}
    assert result.metrics["false_abstention_rate"] == {"hits": 0, "n": 1, "rate": 0.0}
    flipped = dict(outputs, M01=dict(outputs["M01"], abstained=True))
    second = evaluate_answers(items, spans, flipped, chunk_of=lambda cid: None)
    assert second.metrics["false_abstention_rate"]["rate"] == 1.0


def test_citation_structure_can_pass_while_correctness_fails(documents):
    """The v1.1 rule, enforced at metric level: structure is not correctness."""
    items, spans, outputs, gold = _answer_inputs(documents)
    wrong = dict(outputs["M01"], answer_text="It was proposed in 9090.")
    result = evaluate_answers(
        items,
        spans,
        dict(outputs, M01=wrong),
        chunk_of={gold.chunk_id: gold}.__getitem__,
        grades={"M01": "incorrect"},
    )
    assert result.metrics["citation_structure_rate"]["rate"] == 1.0
    assert result.metrics["answer_correctness"] == {"hits": 0, "n": 1, "rate": 0.0}
    assert result.items[0]["citation_structure_valid"] is True


def test_correctness_is_pending_without_a_grading_file(documents):
    items, spans, outputs, gold = _answer_inputs(documents)
    result = evaluate_answers(
        items, spans, outputs, chunk_of={gold.chunk_id: gold}.get
    )
    assert result.metrics["answer_correctness"] == PENDING_CORRECTNESS
    assert result.metrics["n_graded"] == 0
    assert isinstance(result.metrics["answer_correctness"], str)


def test_fabricated_citation_fails_the_structure_check(documents):
    items, spans, outputs, _ = _answer_inputs(documents)
    ghost_entry = {"chunk_id": "ghost#9999", "doc_id": "ghost", "quote": "x"}
    ghost = dict(outputs["M01"], citations=[ghost_entry])
    result = evaluate_answers(items, spans, dict(outputs, M01=ghost), chunk_of=lambda cid: None)
    assert result.metrics["citation_structure_rate"]["rate"] == 0.0
    assert "unknown chunk id" in result.items[0]["structure_problems"][0]


def test_citation_without_a_recorded_quote_cannot_pass_level_2(documents):
    items, spans, outputs, gold = _answer_inputs(documents)
    no_quote = dict(outputs["M01"], citations=[{"chunk_id": gold.chunk_id, "doc_id": DOC_ID}])
    problems = citations_from_record(no_quote, {gold.chunk_id: gold}.__getitem__)[1]
    assert any("no quote recorded" in problem for problem in problems)
    result = evaluate_answers(
        items, spans, dict(outputs, M01=no_quote), chunk_of={gold.chunk_id: gold}.get
    )
    assert result.metrics["citation_structure_rate"]["rate"] == 0.0


def test_abstained_rows_are_not_counted_in_the_structure_denominator(documents):
    items, spans, outputs, gold = _answer_inputs(documents)
    result = evaluate_answers(
        items, spans, outputs, chunk_of={gold.chunk_id: gold}.get
    )
    assert result.metrics["citation_structure_rate"]["n"] == 1
    assert result.items[1]["citation_structure_valid"] is None


def test_outputs_missing_a_qid_is_an_error(documents):
    items, spans, outputs, gold = _answer_inputs(documents)
    outputs.pop("N01")
    with pytest.raises(QASetError, match="no record for qid"):
        evaluate_answers(items, spans, outputs, chunk_of={gold.chunk_id: gold}.__getitem__)


def test_hit_rate_of_the_used_context_is_scored_alongside_answers(documents):
    items, spans, outputs, gold = _answer_inputs(documents)
    noise = _chunk(documents, 0, 165, "rag_wikipedia#0000")
    record = dict(outputs["M01"], retrieved_ids=[noise.chunk_id, gold.chunk_id])
    result = evaluate_answers(
        items,
        spans,
        dict(outputs, M01=record),
        chunk_of={noise.chunk_id: noise, gold.chunk_id: gold}.get,
        hit_levels=(1, 2),
    )
    assert result.metrics["hit@1"]["rate"] == 0.0
    assert result.metrics["hit@2"]["rate"] == 1.0
    assert result.items[0]["first_hit_rank"] == 2


def test_unknown_retrieved_id_is_dropped_rather_than_invented(documents):
    items, spans, outputs, gold = _answer_inputs(documents)
    record = dict(outputs["M01"], retrieved_ids=["ghost#0001", gold.chunk_id])
    result = evaluate_answers(
        items, spans, dict(outputs, M01=record), chunk_of={gold.chunk_id: gold}.get
    )
    assert result.items[0]["n_retrieved"] == 1
    assert result.items[0]["first_hit_rank"] == 1


# ---------------------------------------------------------------------------
# MOCK: grading sheet round trip
# ---------------------------------------------------------------------------


def test_grading_sheet_round_trip_feeds_correctness_back_in(documents, tmp_path):
    items, spans, outputs, gold = _answer_inputs(documents)
    sheet = write_grading_sheet(tmp_path / "grades.csv", items, outputs)
    with sheet.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert [row["qid"] for row in rows] == [item.qid for item in items]
    assert all(row["grade"] == "" for row in rows), "the sheet must start ungraded"

    rows[0]["grade"] = "correct"
    with sheet.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    grades = load_grades(sheet)
    assert grades == {"M01": "correct"}
    result = evaluate_answers(
        items,
        spans,
        outputs,
        chunk_of={gold.chunk_id: gold}.__getitem__,
        grades=grades,
    )
    assert result.metrics["answer_correctness"] == {"hits": 1, "n": 1, "rate": 1.0}


def test_grades_file_is_validated(tmp_path):
    path = tmp_path / "grades.csv"
    path.write_text("qid,grade\nM01,maybe\n", encoding="utf-8")
    with pytest.raises(QASetError, match="grade must be one of"):
        load_grades(path)
    assert set(ALLOWED_GRADES) == {"correct", "incorrect", "unsure"}


def test_grades_file_without_any_grade_is_rejected(tmp_path):
    path = tmp_path / "grades.csv"
    path.write_text("qid,grade\nM01,\n", encoding="utf-8")
    with pytest.raises(QASetError, match="no graded rows"):
        load_grades(path)


def test_grades_file_without_grade_column_is_rejected(tmp_path):
    path = tmp_path / "grades.csv"
    path.write_text("qid,answer\nM01,ok\n", encoding="utf-8")
    with pytest.raises(QASetError, match="needs a 'grade' column"):
        load_grades(path)


def test_outputs_file_accepts_list_or_items_key(tmp_path):
    wrapped = tmp_path / "wrapped.json"
    wrapped.write_text(json.dumps({"items": [{"qid": "M01"}]}), encoding="utf-8")
    bare = tmp_path / "bare.json"
    bare.write_text(json.dumps([{"qid": "M01"}]), encoding="utf-8")
    assert load_outputs(wrapped) == load_outputs(bare) == {"M01": {"qid": "M01"}}


def test_outputs_file_without_qid_is_rejected(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps([{"answer_text": "orphan"}]), encoding="utf-8")
    with pytest.raises(QASetError, match="needs a qid"):
        load_outputs(path)


def test_reports_record_their_own_provenance(documents):
    items, spans, outputs, gold = _answer_inputs(documents)
    result = evaluate_answers(items, spans, outputs, chunk_of={gold.chunk_id: gold}.__getitem__)
    result.label = "MOCK"
    payload = result.to_payload()
    assert payload["label"] == "MOCK"
    assert payload["command"], "a report row without the command that produced it is unverifiable"
    assert payload["command"].startswith("python -m eval.metrics")
    assert str(ROOT) not in payload["command"], (
        "provenance must not embed one contributor's absolute path"
    )
    assert payload["generated_at"]


def test_relative_helper_keeps_paths_repo_relative():
    assert _relative(ROOT / "data" / "raw") == "data/raw"
    assert _relative(ROOT / "eval" / "qa_set.csv") == "eval/qa_set.csv"
    assert _relative(ROOT / "eval" / "results" / "run.json") == "eval/results/run.json"

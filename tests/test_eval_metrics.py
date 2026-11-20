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
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from eval import metrics as metrics_module
from eval.evidence import locate_evidence
from eval.metrics import (
    ALLOWED_GRADES,
    DEV_QA,
    PENDING_CORRECTNESS,
    QA_COLUMNS,
    QA_SET_STATUS_OTHER,
    REVIEW_TABLE,
    QAItem,
    QASetError,
    _config_snapshot,
    _relative,
    abstention_rates,
    answer_correctness,
    artifact_provenance,
    assert_formal_inputs,
    citation_structure_rate,
    citations_from_record,
    evaluate_answers,
    evaluate_retrieval,
    frozen_doc_ids,
    load_grades,
    load_outputs,
    load_qa,
    looks_scripted,
    parse_hits,
    qa_corpus_binding,
    qa_set_status,
    resolve_answer_path,
    retrieval_hit_rate,
    token_occurs,
    unreviewed_items,
    validate_qa_set,
    write_grading_sheet,
    write_summary,
)
from ragkit.config import ROOT
from ragkit.contracts import Chunk, RetrievedChunk
from ragkit.loaders import load_documents

QA_PATH = ROOT / "eval" / "qa_set.csv"
DEV_QA_PATH = DEV_QA
MANIFEST = ROOT / "data" / "raw" / "manifest.json"
DOC_ID = "rag_wikipedia"
CORPUS_V0_DOC_IDS = {
    "rag_wikipedia",
    "vector_db_wikipedia",
    "word_embedding_wikipedia",
    "bm25_wikipedia",
}
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
# GOLD: the committed QA sets against the real corpus
# ---------------------------------------------------------------------------

# Two QA files are committed and both are checked the same way: the formal
# Kubernetes set at the I2 path, and the Wikipedia development set the 35 items
# were moved into. Reading only the first would let the second rot in silence.
QA_SET_FILES = {"formal": QA_PATH, "dev": DEV_QA_PATH}


@pytest.fixture(scope="module", params=["formal", "dev"])
def committed_qa(request):
    """``(name, items)`` for each QA file the repository commits."""
    return request.param, load_qa(QA_SET_FILES[request.param])


def expected_covered_docs(name: str) -> set[str]:
    """Which documents each committed set must have gold quotes in."""
    if name == "formal":
        return frozen_doc_ids() - CORPUS_V0_DOC_IDS
    return set(CORPUS_V0_DOC_IDS)


def test_qa_set_is_large_enough_and_has_both_categories(committed_qa):
    _, items = committed_qa
    assert len(items) >= 20, "the assignment needs at least 20 QA pairs"
    categories = {item.category for item in items}
    assert categories == {"answerable", "unanswerable"}


def test_every_gold_quote_is_verbatim_source_text(committed_qa, documents):
    _, items = committed_qa
    spans = validate_qa_set(items, documents)
    answerable = [item for item in items if item.is_answerable]
    assert len(spans) == len(answerable)
    for item in answerable:
        span = spans[item.qid]
        source = next(doc.text for doc in documents if doc.doc_id == span.doc_id)
        assert source[span.char_start : span.char_end] == item.evidence_quote
        assert span.length == len(item.evidence_quote)


def test_gold_spans_are_unique_per_qid_and_cover_their_own_corpus(committed_qa, documents):
    name, items = committed_qa
    spans = validate_qa_set(items, documents)
    assert len({(s.doc_id, s.char_start, s.char_end) for s in spans.values()}) == len(spans)
    covered = {span.doc_id for span in spans.values()}
    assert covered == expected_covered_docs(name)


def test_the_two_committed_sets_together_cover_the_frozen_snapshot():
    """No document in the I1 snapshot is left without a gold quote."""
    covered = {
        item.evidence_doc_id
        for path in QA_SET_FILES.values()
        for item in load_qa(path)
        if item.evidence_doc_id
    }
    assert covered == set(frozen_doc_ids())


def test_committed_qa_files_stay_lf_so_multi_line_gold_survives_checkout():
    """A CRLF working copy silently breaks the gold quotes that span two lines.

    ``load_qa`` opens the csv with ``newline=""``, so a quoted field keeps whatever
    line ending the file has, while the corpus is read as text and always has ``\\n``.
    A gold quote covering two source lines therefore stops matching on a machine that
    checked the csv out with ``\\r\\n`` - only there, so CI on Linux would stay green.
    ``.gitattributes`` pins LF; this test keeps that promise from rotting.
    """
    for name, path in QA_SET_FILES.items():
        assert b"\r\n" not in path.read_bytes(), (
            f"{name} set is CRLF in this working copy, but the repository pins LF; "
            "the checkout predates .gitattributes - re-clone or re-checkout the file"
        )
    multiline = [
        item.qid
        for item in load_qa(QA_SET_FILES["formal"])
        if item.is_answerable and "\n" in item.evidence_quote
    ]
    assert multiline, "the formal set lost the gold quotes that span two lines"


def test_a_crlf_copy_of_the_formal_set_stops_matching_the_corpus(tmp_path, documents):
    """Negative control for the byte check above: the failure it prevents is real.

    Rewriting the committed csv with ``\\r\\n`` leaves every single-line quote matching
    and breaks only the quotes that span two source lines - so a platform-dependent
    checkout would look like a gold-standard bug rather than a line-ending one.
    """
    payload = QA_SET_FILES["formal"].read_bytes().replace(b"\n", b"\r\n")
    crlf_copy = tmp_path / "qa_set_crlf.csv"
    crlf_copy.write_bytes(payload)
    with pytest.raises(QASetError, match="not verbatim"):
        validate_qa_set(load_qa(crlf_copy), documents)


def test_unanswerable_items_declare_tokens_that_are_really_absent(committed_qa, documents):
    name, items = committed_qa
    unanswerable = [item for item in items if not item.is_answerable]
    assert len(unanswerable) >= 5, "abstention needs enough refusal cases to be measurable"
    corpus = " ".join(doc.text.lower() for doc in documents)
    for item in unanswerable:
        assert item.absent_tokens, f"{item.qid} declares no ABSENT_TOKENS"
        present = [token for token in item.absent_tokens if token_occurs(token, corpus)]
        assert not present, f"{name}/{item.qid} declares {present} absent, corpus has them"


def test_absence_is_judged_on_whole_words_not_substrings():
    """Reviewer point 4, pinned in both directions.

    ``fee`` must not be reported as present because of ``feedback``, and a
    declared word must still count when the corpus only inflects it. A rule
    that only ever loosens would make an unreviewed refusal item look proven.
    """
    assert not token_occurs("fee", "we read your feedback carefully")
    assert token_occurs("gpu", "two gpus are attached")
    assert token_occurs("hallucination", "fewer hallucinations in answers")
    assert token_occurs("cost per hour", "the cost\n   per hour is")
    assert not token_occurs("cost per hour", "the hourly cost of a node")
    assert not token_occurs("", "anything at all")


def test_answerable_items_always_have_a_reference_answer(committed_qa):
    _, items = committed_qa
    assert all(item.reference_answer for item in items if item.is_answerable)
    assert all(not item.reference_answer for item in items if not item.is_answerable)


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


def test_command_line_follows_the_arguments_main_was_given(monkeypatch):
    """Imported calls must not borrow the driver's argv or leak a local path."""
    monkeypatch.setattr(
        metrics_module,
        "_COMMAND_ARGS",
        ["retrieval", "--chunking", "paragraph", "--hits", "1,3", "--out",
         str(ROOT / "eval" / "results" / "raw" / "x.json")],
    )
    assert metrics_module._command_line() == (
        "python -m eval.metrics retrieval --chunking paragraph --hits 1,3 "
        "--out eval/results/raw/x.json"
    )


# ---------------------------------------------------------------------------
# Interface I3: the four public functions are THE implementation, not a copy
# ---------------------------------------------------------------------------


def test_i3_functions_are_importable_with_the_frozen_names():
    """T2 / T3 / T5 import exactly these four; a rename would break their PRs."""
    for func in (
        retrieval_hit_rate,
        answer_correctness,
        abstention_rates,
        citation_structure_rate,
    ):
        assert callable(func)
        assert func.__doc__, "the team's only metric implementation must explain itself"


def test_the_public_function_and_the_aggregator_return_the_same_numbers(documents):
    """One formula: the aggregator may add rows, it may not re-derive a rate."""
    span = _span(documents, QUOTE_2020)
    gold = _chunk(documents, span.char_start, span.char_end, "rag_wikipedia#0007")
    noise = _chunk(documents, 0, 165, "rag_wikipedia#0000")
    items = [_answerable("M01", QUOTE_2020), _answerable("M02", QUOTE_2020)]
    spans = {item.qid: span for item in items}
    hits = {"M01": _hits([gold]), "M02": _hits([noise, gold])}
    public = retrieval_hit_rate(items, spans, hits, hit_levels=(1, 3), min_coverage=0.5)
    aggregated = evaluate_retrieval(items, spans, hits, hit_levels=(1, 3), min_coverage=0.5)
    for level in (1, 3):
        assert public["rates"][f"hit@{level}"] == aggregated.metrics[f"hit@{level}"]
    assert public["n_answerable"] == aggregated.metrics["n_answerable"]


def test_hit_levels_are_reported_for_whatever_k_the_caller_asks(documents):
    span = _span(documents, QUOTE_2020)
    gold = _chunk(documents, span.char_start, span.char_end, "rag_wikipedia#0007")
    item = _answerable("M01", QUOTE_2020)
    rates = retrieval_hit_rate([item], {item.qid: span}, {item.qid: _hits([gold])},
                               hit_levels=(1, 2, 5))["rates"]
    assert set(rates) == {"hit@1", "hit@2", "hit@5"}, "T2 asks for its own k, we obey"
    assert all(value["rate"] == 1.0 for value in rates.values())


# ---------------------------------------------------------------------------
# Interface I3 boundary conditions required by the task card: empty / refusal
# ---------------------------------------------------------------------------


def test_empty_inputs_report_no_rate_instead_of_a_zero():
    """0/0 is undefined: a bare 0.0 would read like a measured failure."""
    assert retrieval_hit_rate([], {}, {}, hit_levels=(1,))["rates"]["hit@1"] == {
        "hits": 0, "n": 0, "rate": None
    }
    abstention = abstention_rates([], {})
    assert abstention["correct_abstention_rate"]["rate"] is None
    assert abstention["false_abstention_rate"]["rate"] is None
    assert citation_structure_rate([], {}, chunk_of=lambda cid: None)["rate"]["rate"] is None
    assert answer_correctness([], {})["correctness"] == PENDING_CORRECTNESS


def test_a_system_that_refuses_everything_scores_zero_on_answerable_items(documents):
    """All-refusal: the two abstention directions must not cancel each other."""
    items, spans, outputs, _ = _answer_inputs(documents)
    refused = {
        qid: dict(record, abstained=True) if not record.get("abstained") else record
        for qid, record in outputs.items()
    }
    result = abstention_rates(items, refused)
    assert result["false_abstention_rate"] == {"hits": 1, "n": 1, "rate": 1.0}
    assert result["correct_abstention_rate"]["rate"] == 1.0
    assert result["n_answered"] == 0
    structure = citation_structure_rate(items, refused, chunk_of=lambda cid: None)
    assert structure["rate"] == {"hits": 0, "n": 0, "rate": None}, "a refusal cites nothing"


def test_abstention_and_structure_need_no_store_at_all(documents):
    """Both are pure over the artifact: T5 can call them without a vector store."""
    items, _, outputs, _ = _answer_inputs(documents)
    assert abstention_rates(items, outputs)["n_unanswerable"] == 1
    assert citation_structure_rate(items, outputs, chunk_of=lambda cid: None)["n_checked"] == 1


# ---------------------------------------------------------------------------
# Reviewer point 3: the correctness denominator is answerable items only
# ---------------------------------------------------------------------------


def test_unanswerable_grades_never_enter_the_correctness_denominator(documents):
    items, spans, outputs, gold = _answer_inputs(documents)
    result = evaluate_answers(
        items,
        spans,
        outputs,
        chunk_of={gold.chunk_id: gold}.__getitem__,
        grades={"M01": "correct", "N01": "correct"},
    )
    assert result.metrics["answer_correctness"] == {"hits": 1, "n": 1, "rate": 1.0}
    assert result.metrics["n_gradable"] == 1, "the refusal case is not a correct answer"
    assert result.metrics["grades_dropped_as_unanswerable"] == ["N01"]


def test_grading_coverage_exposes_the_ungraded_remainder(documents):
    span = _span(documents, QUOTE_2020)
    gold = _chunk(documents, span.char_start, span.char_end, "rag_wikipedia#0007")
    items = [_answerable("M01", QUOTE_2020), _answerable("M02", QUOTE_2020)]
    outputs = {item.qid: _record(item.qid, gold) for item in items}
    result = evaluate_answers(
        items, {item.qid: span for item in items}, outputs,
        chunk_of={gold.chunk_id: gold}.__getitem__,
        grades={"M01": "correct"},
    )
    assert result.metrics["answer_correctness"]["n"] == 1
    assert result.metrics["n_gradable"] == 2
    assert result.metrics["grading_coverage"] == {"hits": 1, "n": 2, "rate": 0.5}


def test_unsure_counts_as_not_correct_and_stays_visible(documents):
    items, spans, outputs, gold = _answer_inputs(documents)
    result = evaluate_answers(
        items, spans, outputs,
        chunk_of={gold.chunk_id: gold}.__getitem__,
        grades={"M01": "unsure"},
    )
    assert result.metrics["answer_correctness"] == {"hits": 0, "n": 1, "rate": 0.0}
    assert result.metrics["grade_counts"] == {"correct": 0, "incorrect": 0, "unsure": 1}


def test_grading_an_unknown_qid_is_an_error_not_a_discarded_row(documents):
    items, _, _, _ = _answer_inputs(documents)
    with pytest.raises(QASetError, match="absent from the QA set"):
        answer_correctness(items, {"M99": "correct"})


def test_an_illegal_grade_reaches_the_metric_kernel_too():
    items = [_answerable("M01", QUOTE_2020)]
    with pytest.raises(QASetError, match="must be one of"):
        answer_correctness(items, {"M01": "maybe"})
    assert set(ALLOWED_GRADES) == {"correct", "incorrect", "unsure"}


def test_grading_sheet_shells_out_only_answerable_rows(documents, tmp_path):
    """The sheet itself shows why a refusal row has no grade to give."""
    items, _, outputs, _ = _answer_inputs(documents)
    sheet = write_grading_sheet(tmp_path / "grades.csv", items, outputs)
    with sheet.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert [row["category"] for row in rows] == ["answerable", "unanswerable"]
    assert rows[1]["abstained"] == "True", "rule-scored, so the grade cell stays empty"


# ---------------------------------------------------------------------------
# Reviewer point 4: ABSENT_TOKENS is necessary, a human makes it a label
# ---------------------------------------------------------------------------


def _refusal(qid: str, notes: str) -> QAItem:
    return QAItem(
        qid=qid,
        question=f"MOCK unanswerable {qid}?",
        reference_answer="",
        evidence_doc_id="",
        evidence_quote="",
        category="unanswerable",
        notes=notes,
    )


def test_absent_tokens_alone_leave_the_item_pending_review():
    item = _refusal("N01", "OUT-OF-DOMAIN. ABSENT_TOKENS: gpu")
    assert item.absent_tokens == ("gpu",)
    assert item.reviewed_by == ""
    assert unreviewed_items([item]) == ["N01"]


def test_review_markers_parse_in_whatever_order_they_are_written():
    first = _refusal("N01", "ABSENT_TOKENS: gpu; REVIEWED_BY: Li Wei")
    second = _refusal("N02", "REVIEWED_BY: Li Wei; ABSENT_TOKENS: gpu")
    third = _refusal("N03", "ABSENT_TOKENS: gpu. REVIEWED_BY: Li Wei.")
    for item in (first, second, third):
        assert item.absent_tokens == ("gpu",), item.notes
        assert item.reviewed_by == "Li Wei", item.notes
    assert unreviewed_items([first, second, third]) == []


def test_require_reviewed_fails_until_a_human_signs_off(documents):
    answerable = _answerable("M01", QUOTE_2020)
    pending = _refusal("N01", "OUT-OF-DOMAIN. ABSENT_TOKENS: gpu")
    signed = _refusal("N02", "OUT-OF-DOMAIN. ABSENT_TOKENS: gpu; REVIEWED_BY: Li Wei")
    with pytest.raises(QASetError, match="REVIEWED_BY"):
        validate_qa_set([answerable, pending], documents, min_items=1, require_reviewed=True)
    spans = validate_qa_set(
        [answerable, signed], documents, min_items=1, require_reviewed=True
    )
    assert set(spans) == {"M01"}, "unanswerable items have no gold to resolve"


def test_formal_review_gate_is_currently_closed_on_the_committed_set(qa_items, documents):
    """No named human has signed the refusal labels yet, so --require-reviewed fails.

    When the group does review them this test flips on purpose: update it in the
    same PR that adds the REVIEWED_BY names, do not simply delete it.
    """
    unanswerable = [item for item in qa_items if not item.is_answerable]
    assert unanswerable
    assert unreviewed_items(unanswerable)
    with pytest.raises(QASetError, match="REVIEWED_BY"):
        validate_qa_set(qa_items, documents, require_reviewed=True)


def test_review_table_lists_every_refusal_item_still_waiting_for_a_signature():
    """The sheet a human signs and the csv cannot drift apart.

    Signing is human work and no test may claim it happened. What this can prove
    is that every item still missing a REVIEWED_BY appears in the checklist, so
    nobody has to guess which rows are open.
    """
    table = REVIEW_TABLE.read_text(encoding="utf-8")
    pending = unreviewed_items(load_qa(QA_PATH))
    assert pending, "the formal set is expected to await review until the group signs it"
    for qid in pending:
        assert qid in table, f"{qid} needs a signature but is not in the review table"
    assert "REVIEWED_BY" in table


# ---------------------------------------------------------------------------
# Reviewer point 2: interface I4 answer artifacts (JSONL, retrieved_chunk_ids)
# ---------------------------------------------------------------------------


def _i4_record(chunk: Chunk, qid: str, *, abstained=False, answer_text="MOCK answer.") -> dict:
    """A record in the shape T5 was asked to write, nested ``answer`` and all."""
    return {
        "qid": qid,
        "answer": {
            "answer_text": answer_text,
            "abstained": abstained,
            "citations": [
                {"chunk_id": chunk.chunk_id, "doc_id": chunk.doc_id, "quote": chunk.text[:40]}
            ],
            "model": "mock-llm",
            "raw": answer_text,
        },
        "retrieved_chunk_ids": [chunk.chunk_id],
        "run_id": "20261115-mock-01",
        "config_ref": "eval/results/summary/mock/config.json",
    }


def test_jsonl_artifact_is_read_and_the_nested_answer_is_flattened(documents, tmp_path):
    span = _span(documents, QUOTE_2020)
    gold = _chunk(documents, span.char_start, span.char_end, "rag_wikipedia#0007")
    path = tmp_path / "20261115-mock-01.jsonl"
    lines = [
        json.dumps(_i4_record(gold, "M01")),
        "",
        json.dumps(_i4_record(gold, "N01", abstained=True, answer_text="refused")),
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    outputs = load_outputs(path)
    assert set(outputs) == {"M01", "N01"}
    assert outputs["M01"]["answer_text"] == "MOCK answer."
    assert outputs["M01"]["retrieved_chunk_ids"] == [gold.chunk_id]
    assert "answer" not in outputs["M01"], "the nested shape is normalised once, at load"
    assert artifact_provenance(outputs) == {
        "run_id": "20261115-mock-01",
        "config_ref": "eval/results/summary/mock/config.json",
        "models": ["mock-llm"],
        "n_records": 2,
    }


def test_a_scripted_artifact_admits_itself_through_the_model_field():
    """`--label REAL` on a double-produced artifact would print a warning.

    The predicate reads what T5 writes in `answer.model`, so the guard travels
    with the artifact instead of relying on whoever types the command.
    """
    assert looks_scripted(["mock-llm", "scripted-mock-generator"])
    assert not looks_scripted(["gpt-4o-mini"])
    assert not looks_scripted(["gpt-4o-mini", "mock-llm"]), "a mixed run is not a double"
    assert not looks_scripted([]), "absent model information proves nothing"


def test_an_i4_record_scores_exactly_like_the_earlier_flat_record(documents):
    """The new field name must not move a single number."""
    items, spans, outputs, gold = _answer_inputs(documents)
    chunk_of = {gold.chunk_id: gold}.__getitem__
    flat = evaluate_answers(items, spans, outputs, chunk_of=chunk_of, hit_levels=(1, 2))
    nested = {
        "M01": _i4_record(gold, "M01"),
        "N01": _i4_record(gold, "N01", abstained=True, answer_text="refused"),
    }
    recorded = evaluate_answers(items, spans, nested, chunk_of=chunk_of, hit_levels=(1, 2))
    assert recorded.metrics["hit@1"] == flat.metrics["hit@1"]
    assert recorded.metrics["hit@2"] == flat.metrics["hit@2"]
    assert recorded.metrics["citation_structure_rate"] == flat.metrics["citation_structure_rate"]
    assert recorded.metrics["false_abstention_rate"] == flat.metrics["false_abstention_rate"]
    assert recorded.items[0]["first_hit_rank"] == flat.items[0]["first_hit_rank"]


def test_two_runs_in_one_artifact_are_refused(tmp_path):
    path = tmp_path / "mixed.jsonl"
    path.write_text(
        json.dumps({"qid": "M01", "run_id": "run-a"}) + "\n"
        + json.dumps({"qid": "M02", "run_id": "run-b"}) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(QASetError, match="mixes run_id"):
        artifact_provenance(load_outputs(path))


def test_duplicate_record_for_one_qid_is_refused(tmp_path):
    path = tmp_path / "dup.jsonl"
    path.write_text('{"qid": "M01"}\n{"qid": "M01"}\n', encoding="utf-8")
    with pytest.raises(QASetError, match="duplicate record"):
        load_outputs(path)


def test_a_broken_jsonl_line_names_its_line_number(tmp_path):
    path = tmp_path / "broken.jsonl"
    path.write_text('{"qid": "M01"}\nnot json\n', encoding="utf-8")
    with pytest.raises(QASetError, match=r"broken\.jsonl:2"):
        load_outputs(path)


def test_resolve_answer_path_finds_the_run_artifact_by_id(tmp_path, monkeypatch):
    monkeypatch.setattr("eval.metrics.ANSWERS_DIR", tmp_path)
    artifact = tmp_path / "run-a.jsonl"
    artifact.write_text('{"qid": "M01"}\n', encoding="utf-8")
    assert resolve_answer_path("run-a", None) == artifact
    assert resolve_answer_path("run-b", artifact) == artifact, "--outputs still wins"
    with pytest.raises(QASetError, match="needs --outputs PATH or --run-id ID"):
        resolve_answer_path(None, None)
    with pytest.raises(QASetError, match="no answer artifact"):
        resolve_answer_path("missing", None)


# ---------------------------------------------------------------------------
# Interface I5: configuration snapshot and the summary/ directory contract
# ---------------------------------------------------------------------------


def _stub_settings(**overrides):
    defaults = {
        "root": ROOT,
        "raw_dir": ROOT / "data" / "raw",
        "manifest": ROOT / "data" / "raw" / "manifest.json",
        "chunk_strategy": "fixed",
        "chunk_size": 120,
        "chunk_overlap": 20,
        "embedding_provider": "local",
        "local_model": "all-MiniLM-L6-v2",
        "api_model": "text-embedding-3-small",
        "embedding_dimension": 384,
        "llm_model": "mock-llm",
        "temperature": 0.0,
        "max_tokens": 512,
        "top_k": 3,
        "collection_name": "chunks_fixed",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_config_snapshot_uses_the_frozen_i5_field_names():
    snapshot = _config_snapshot(
        _stub_settings(), [_answerable("M01", QUOTE_2020)], min_coverage=0.5
    )
    for key in (
        "strategy",
        "size",
        "overlap",
        "top_k",
        "min_coverage",
        "embedding",
        "llm",
        "corpus_ref",
        "qa_set_ref",
    ):
        assert key in snapshot, f"I5 froze this field name: {key}"
    assert snapshot["qa_set_status"], "development numbers must be labelled development"
    assert re.fullmatch(r".+@[0-9a-f]{12}", snapshot["corpus_ref"]), snapshot["corpus_ref"]
    assert "@" in snapshot["qa_set_ref"], "a QA reference without a hash cannot be pinned"


def test_config_snapshot_records_which_documents_the_rows_cite():
    """The binding is part of the provenance, not a verbal claim in a PR."""
    items = load_qa(QA_PATH)[:5]
    snapshot = _config_snapshot(_stub_settings(), items, min_coverage=0.5)
    assert set(snapshot["qa_cited_docs"]) == {
        item.evidence_doc_id for item in items if item.evidence_doc_id
    }
    assert set(snapshot["qa_cited_docs"]) <= frozen_doc_ids()
    assert snapshot["qa_corpus_binding_verified"] is True
    assert snapshot["qa_docs_outside_frozen_snapshot"] == []


def test_qa_set_status_is_derived_from_the_file_and_its_rows():
    formal = qa_set_status(QA_PATH, load_qa(QA_PATH))
    dev = qa_set_status(DEV_QA_PATH, load_qa(DEV_QA_PATH))
    assert formal.startswith("formal Kubernetes QA set")
    assert dev.startswith("development QA set")
    assert "not the formal evaluation set" in dev
    assert formal != dev, "two different sets cannot carry one status string"
    # the review clause reports what the rows say, so it flips when they sign
    for path, status in ((QA_PATH, formal), (DEV_QA_PATH, dev)):
        assert ("awaiting a human REVIEWED_BY" in status) == bool(
            unreviewed_items(load_qa(path))
        )
    assert qa_set_status(ROOT / "eval" / "scratch.csv") == QA_SET_STATUS_OTHER


def test_corpus_binding_flags_documents_the_snapshot_does_not_list():
    """A verbatim quote in some other file must not pass as frozen-corpus gold."""
    items = [_answerable("M01", QUOTE_2020, doc_id="not_in_the_snapshot")]
    binding = qa_corpus_binding(items)
    assert binding["qa_docs_outside_frozen_snapshot"] == ["not_in_the_snapshot"]
    assert binding["qa_corpus_binding_verified"] is False
    assert "cites non-snapshot doc" in qa_set_status(QA_PATH, items)


def test_summary_bundle_carries_the_five_required_parts(documents, tmp_path, monkeypatch):
    frozen = tmp_path / "frozen_manifest.json"
    frozen.write_text(json.dumps({"corpus_id": "cs5481-corpus-0001"}), encoding="utf-8")
    monkeypatch.setattr("eval.metrics.FROZEN_MANIFEST", frozen)
    span = _span(documents, QUOTE_2020)
    item = _answerable("M01", QUOTE_2020)
    result = evaluate_retrieval(
        [item], {item.qid: span}, {item.qid: _hits([])}, hit_levels=(1,)
    )
    result.label = "REAL"
    result.config = _config_snapshot(_stub_settings(), [item], min_coverage=0.5)
    directory = tmp_path / "summary" / "chunking_comparison"
    written = write_summary(result, directory, executor="A. Member")
    assert {path.name for path in written} == {"config.json", "metrics.json", "run.md"}
    metrics = json.loads((directory / "metrics.json").read_text(encoding="utf-8"))
    for key in (
        "experiment_id",
        "generated_at",
        "command",
        "config_ref",
        "corpus_ref",
        "qa_set_ref",
        "judge",
    ):
        assert key in metrics, f"eval/results/README.md asks for {key}"
    assert metrics["corpus_ref"].startswith("cs5481-corpus-0001@")
    assert metrics["judge"] == "not applicable: retrieval-only run"
    run_log = (directory / "run.md").read_text(encoding="utf-8")
    for fragment in ("command:", "date:", "executor: A. Member", "exit code:"):
        assert fragment in run_log


def test_summary_refuses_a_mock_run(documents, tmp_path):
    span = _span(documents, QUOTE_2020)
    item = _answerable("M01", QUOTE_2020)
    result = evaluate_retrieval(
        [item], {item.qid: span}, {item.qid: _hits([])}, hit_levels=(1,)
    )
    result.label = "MOCK"
    with pytest.raises(QASetError, match="MOCK"):
        write_summary(result, tmp_path / "summary" / "oops")


def test_formal_gate_refuses_while_the_inputs_are_still_moving(qa_items, tmp_path, monkeypatch):
    monkeypatch.setattr("eval.metrics.FROZEN_MANIFEST", tmp_path / "absent.json")
    with pytest.raises(QASetError, match="frozen"):
        assert_formal_inputs(_stub_settings(), qa_items)


def test_formal_gate_refuses_the_development_set_even_once_the_corpus_is_frozen():
    """Reading the wrong file is a problem on its own, hash or no hash."""
    with pytest.raises(QASetError, match="development set"):
        assert_formal_inputs(_stub_settings(), load_qa(DEV_QA_PATH), qa_path=DEV_QA_PATH)


def test_formal_gate_refuses_an_ad_hoc_qa_file(tmp_path):
    with pytest.raises(QASetError, match="not a committed team QA artifact"):
        assert_formal_inputs(_stub_settings(), load_qa(QA_PATH), qa_path=tmp_path / "qa.csv")

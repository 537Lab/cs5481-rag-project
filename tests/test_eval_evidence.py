"""Tests for the strategy-independent evidence standard (v1.1 fix).

These prove that gold labels live in ORIGINAL documents, not in chunk ids, so
`fixed` and `paragraph` can be compared on the same QA set.
"""

from __future__ import annotations

import pytest

from eval.evidence import (
    evidence_coverage,
    is_retrieval_hit,
    locate_evidence,
    overlap_characters,
)
from ragkit.config import ROOT
from ragkit.contracts import Chunk, RetrievedChunk
from ragkit.loaders import load_documents

QUOTE = (
    "The term retrieval-augmented generation (RAG) was introduced in a 2020 paper"
)
DOC_ID = "rag_wikipedia"


def _documents():
    return load_documents(ROOT / "data" / "raw" / "manifest.json")


def _chunk(start: int, end: int, chunk_id: str, strategy: str, doc_id: str = DOC_ID):
    documents = _documents()
    text = next(d.text for d in documents if d.doc_id == DOC_ID)
    return Chunk(
        chunk_id=chunk_id,
        doc_id=doc_id,
        text=text[start:end],
        char_start=start,
        char_end=end,
        strategy=strategy,
        index=0,
    )


def _hit(chunk: Chunk) -> RetrievedChunk:
    return RetrievedChunk(chunk=chunk, score=0.9, rank=1)


def test_gold_quote_resolves_to_a_real_source_span():
    span = locate_evidence(_documents(), DOC_ID, QUOTE)
    assert (span.char_start, span.char_end) == (1651, 1727)
    assert span.length == len(QUOTE)
    source = next(d.text for d in _documents() if d.doc_id == DOC_ID)
    assert source[span.char_start : span.char_end] == QUOTE


def test_fabricated_quote_is_rejected():
    with pytest.raises(ValueError, match="not verbatim"):
        locate_evidence(_documents(), DOC_ID, "RAG was invented in 1999")
    with pytest.raises(ValueError, match="unknown evidence_doc_id"):
        locate_evidence(_documents(), "no_such_doc", QUOTE)


def test_two_different_strategies_score_the_same_gold_evidence():
    span = locate_evidence(_documents(), DOC_ID, QUOTE)
    fixed = _chunk(1600, 1760, "rag_wikipedia#0001", "fixed")
    paragraph = _chunk(1500, 1800, "rag_wikipedia#0007", "paragraph")
    assert fixed.chunk_id != paragraph.chunk_id
    assert fixed.strategy != paragraph.strategy
    assert evidence_coverage(fixed, span) == evidence_coverage(paragraph, span) == 1.0
    assert is_retrieval_hit([_hit(fixed)], span)
    assert is_retrieval_hit([_hit(paragraph)], span)


def test_partial_coverage_and_threshold_are_explicit():
    span = locate_evidence(_documents(), DOC_ID, QUOTE)
    half = _chunk(span.char_start, span.char_start + span.length // 2, "x#0000", "fixed")
    assert overlap_characters(half, span) == span.length // 2
    assert 0.4 < evidence_coverage(half, span) < 0.6
    assert is_retrieval_hit([_hit(half)], span, min_coverage=0.5)
    assert not is_retrieval_hit([_hit(half)], span, min_coverage=0.8)


def test_wrong_document_can_never_hit():
    span = locate_evidence(_documents(), DOC_ID, QUOTE)
    other = _chunk(1600, 1760, "other#0000", "fixed", doc_id="other_doc")
    assert overlap_characters(other, span) == 0
    assert not is_retrieval_hit([_hit(other)], span)


def test_invalid_coverage_threshold_is_rejected():
    span = locate_evidence(_documents(), DOC_ID, QUOTE)
    with pytest.raises(ValueError, match="min_coverage"):
        is_retrieval_hit([], span, min_coverage=0.0)

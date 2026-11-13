"""Shared, chunking-strategy-independent gold standard for evaluation.

WHY THIS EXISTS
---------------
Chunk ids are an OUTPUT of a chunking strategy: `fixed` and `paragraph`, or two
different chunk sizes, produce different ids and different boundaries for the
same source text. Using `expected_chunk_ids` as gold labels makes the comparison
experiment meaningless (and would be comparing an index against itself).

Gold evidence is instead a VERBATIM QUOTE from an ORIGINAL document. It is
located as a character span [char_start, char_end) in that document, which is
the same for every strategy. Any chunk, from any strategy, can be scored by how
much of that span it covers.

This module provides only pure helper functions - no QA set, no metrics script,
no results. Those belong to the evaluation task package (T4).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ragkit.contracts import Chunk, Document, RetrievedChunk


@dataclass(frozen=True)
class EvidenceSpan:
    """A location in an ORIGINAL document, never in a chunk."""

    doc_id: str
    char_start: int
    char_end: int
    quote: str

    def __post_init__(self) -> None:
        if self.char_end <= self.char_start:
            raise ValueError("evidence span must have a positive length")

    @property
    def length(self) -> int:
        return self.char_end - self.char_start


def locate_evidence(
    documents: Sequence[Document], doc_id: str, quote: str
) -> EvidenceSpan:
    """Resolve a verbatim gold quote to a character span in the source document."""
    if not quote:
        raise ValueError("evidence quote must not be empty")
    for document in documents:
        if document.doc_id != doc_id:
            continue
        position = document.text.find(quote)
        if position < 0:
            raise ValueError(
                f"evidence quote is not verbatim source text of doc_id={doc_id!r}: {quote[:60]!r}"
            )
        return EvidenceSpan(doc_id, position, position + len(quote), quote)
    raise ValueError(f"unknown evidence_doc_id: {doc_id!r}")


def overlap_characters(chunk: Chunk, span: EvidenceSpan) -> int:
    """How many characters of the gold evidence this chunk actually contains."""
    if chunk.doc_id != span.doc_id:
        return 0
    return max(0, min(chunk.char_end, span.char_end) - max(chunk.char_start, span.char_start))


def evidence_coverage(chunk: Chunk, span: EvidenceSpan) -> float:
    """Fraction of the gold evidence span covered by one chunk, in [0, 1]."""
    return overlap_characters(chunk, span) / span.length


def is_retrieval_hit(
    hits: Sequence[RetrievedChunk], span: EvidenceSpan, min_coverage: float = 0.5
) -> bool:
    """A top-k result is a hit if any retrieved chunk covers enough gold evidence.

    `min_coverage` is a REPORTED evaluation parameter, not a tuned model
    hyper-parameter. Every strategy in a comparison must use the same value.
    """
    if not 0.0 < min_coverage <= 1.0:
        raise ValueError("min_coverage must be in (0, 1]")
    return any(evidence_coverage(hit.chunk, span) >= min_coverage for hit in hits)

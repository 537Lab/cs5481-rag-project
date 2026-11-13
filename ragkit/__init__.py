"""CS5481 Topic 5 - minimal RAG baseline.

Five independent modules, one shared contract file:

    loaders (M1) -> chunking (M2) -> embeddings (M3) -> store (M4) -> generation (M5)

This is deliberately a flat package run from the repository root; there is no
packaging, no framework, and no service to start.
"""

from ragkit.contracts import (
    ABSTAIN_MESSAGE,
    NO_ANSWER_TOKEN,
    Answer,
    Chunk,
    Citation,
    Document,
    RetrievedChunk,
)

__all__ = [
    "ABSTAIN_MESSAGE",
    "NO_ANSWER_TOKEN",
    "Answer",
    "Chunk",
    "Citation",
    "Document",
    "RetrievedChunk",
]

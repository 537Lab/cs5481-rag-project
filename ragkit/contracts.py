"""Shared data contracts and interfaces for all five modules.

WHY THIS FILE EXISTS
--------------------
Five people work in parallel. This is the ONLY place where cross-module data
types and interfaces are defined, so nobody has to guess field names.

OWNERSHIP: shared. Changing a field here changes everyone's code, so it needs
a PR with at least two approvals (see CONTRIBUTING.md).

HARD RULE: stdlib only. No third-party imports in this file.

The flow is strictly one-directional:

    Document -> Chunk -> (Chunk + vector) -> RetrievedChunk -> Answer
      M1          M2          M3 / M4            M4              M5
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Document:
    """One source document, produced by M1."""

    doc_id: str
    title: str
    text: str
    source_uri: str = ""
    license: str = ""
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Chunk:
    """A slice of a Document, produced by M2.

    Verifiability contract: ``doc.text[chunk.char_start:chunk.char_end] == chunk.text``
    must hold. This lets M5 prove that a citation really points at source text.
    """

    chunk_id: str  # stable, e.g. "rag_wikipedia#0003"
    doc_id: str
    text: str
    char_start: int
    char_end: int
    strategy: str
    index: int
    # Copied from the Document so M4/M5 never need to re-open the source file.
    title: str = ""
    source_uri: str = ""
    license: str = ""
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievedChunk:
    """A chunk plus its retrieval score, produced by M4."""

    chunk: Chunk
    score: float  # cosine similarity in [0, 1]; higher is better
    rank: int  # 1-based


@dataclass(frozen=True)
class Citation:
    """A verifiable pointer back to source text, produced by M5."""

    chunk_id: str
    doc_id: str
    quote: str  # verbatim excerpt of Chunk.text
    title: str = ""
    source_uri: str = ""


@dataclass(frozen=True)
class Answer:
    """Final result of M5."""

    question: str
    answer_text: str
    citations: tuple[Citation, ...]
    abstained: bool
    model: str
    raw: str = ""  # unmodified LLM output, kept for debugging

    @property
    def citation_ids(self) -> tuple[str, ...]:
        return tuple(c.chunk_id for c in self.citations)


# ---------------------------------------------------------------------------
# Interfaces (one per module; implementations live in that module's file)
# ---------------------------------------------------------------------------


class Chunker(Protocol):
    """M2: Document -> chunks. Pure function, stdlib only."""

    name: str

    def split(self, doc: Document) -> list[Chunk]: ...


class Embedder(Protocol):
    """M3: texts -> vectors. Does NOT read files, write to a DB, or build prompts."""

    name: str
    dimension: int

    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


class VectorStore(Protocol):
    """M4: persist (chunk, vector) pairs and retrieve by vector similarity.

    Does NOT compute embeddings and does NOT build prompts.
    """

    def upsert(self, chunks: Sequence[Chunk], vectors: Sequence[Sequence[float]]) -> None: ...

    def search(self, query_vector: Sequence[float], k: int) -> list[RetrievedChunk]: ...

    def get_chunk(self, chunk_id: str) -> Chunk | None: ...

    def count(self) -> int: ...


class LLMClient(Protocol):
    """M5: prompt in, text out. This is the ONLY place that calls an LLM API."""

    model: str

    def complete(self, system_prompt: str, user_prompt: str) -> str: ...


# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

ABSTAIN_MESSAGE = "I cannot answer this question from the provided documents."
NO_ANSWER_TOKEN = "NO_ANSWER"

# Citation markers in the LLM output look like [rag_wikipedia#0003].
CITATION_PATTERN = r"\[([A-Za-z0-9_.\-#]+)\]"

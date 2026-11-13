"""MOCK test doubles - NOT real implementations, NOT for experiments.

WHY THESE EXIST: CI and a first-time user must be able to run the whole
pipeline with zero network, zero API key and zero model download. These
doubles implement the same interfaces defined in ragkit/contracts.py, but
their vectors and answers are synthetic.

Rules:
  * These live under tests/ only. Production code never imports them,
    except `cli offline-demo` (which prints a MOCK banner).
  * Never use a Fake result as an experimental result.
  * `test_e2e_real.py` is the only test that uses real components.
"""

from __future__ import annotations

import math
import re
import zlib
from collections.abc import Callable, Sequence
from typing import Any

from ragkit.contracts import Chunk, RetrievedChunk

FAKE_MANIFEST = "tests/fixtures/manifest.json"


class FakeEmbedder:
    """Deterministic bag-of-words hashing vectors. Same text -> same vector."""

    name = "fake-hash-embedder"
    dimension = 32

    def __init__(self, dimension: int = 32) -> None:
        self.dimension = dimension

    def _vector(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        for token in re.findall(r"[a-z0-9]+", text.lower()):
            vector[zlib.crc32(token.encode()) % self.dimension] += 1.0
        norm = math.sqrt(sum(value * value for value in vector))
        return [value / norm for value in vector] if norm else vector

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]


class InMemoryStore:
    """Minimal cosine-similarity store implementing the VectorStore protocol."""

    def __init__(self) -> None:
        self._rows: dict[str, tuple[Chunk, list[float]]] = {}

    def upsert(self, chunks: Sequence[Chunk], vectors: Sequence[Sequence[float]]) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("one vector per chunk required")
        for chunk, vector in zip(chunks, vectors, strict=True):
            self._rows[chunk.chunk_id] = (chunk, list(vector))

    def _dot(self, left: Sequence[float], right: Sequence[float]) -> float:
        return sum(a * b for a, b in zip(left, right, strict=True))

    def search(self, query_vector: Sequence[float], k: int) -> list[RetrievedChunk]:
        scored = [
            (self._dot(vector, query_vector), chunk)
            for chunk, vector in self._rows.values()
        ]
        scored.sort(key=lambda pair: -pair[0])
        return [
            RetrievedChunk(chunk=chunk, score=score, rank=rank)
            for rank, (score, chunk) in enumerate(scored[:k], start=1)
        ]

    def get_chunk(self, chunk_id: str) -> Chunk | None:
        row = self._rows.get(chunk_id)
        return row[0] if row else None

    def count(self) -> int:
        return len(self._rows)

    def clear(self) -> None:
        self._rows.clear()


class ScriptedLLM:
    """Returns whatever the caller's handler decides. Records every call."""

    model = "mock-llm"

    def __init__(self, handler: Callable[[str, str], str]) -> None:
        self.handler = handler
        self.calls: list[tuple[str, str]] = []

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt))
        return self.handler(system_prompt, user_prompt)


def settings_stub(**overrides: Any):
    """Small stand-in for Settings in tests that do not call build_pipeline."""
    defaults: dict[str, Any] = {
        "top_k": 2,
        "min_score": 0.0,
        "chunk_strategy": "fixed",
        "chunk_size": 120,
        "chunk_overlap": 20,
        "embedding_provider": "local",
        "embedding_dimension": 32,
        "collection_name": "chunks_fixed",
    }
    defaults.update(overrides)
    return type("SettingsStub", (), defaults)()

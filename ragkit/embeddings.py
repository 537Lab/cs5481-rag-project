"""M3 - Embedding.

INPUT   sequence of strings
OUTPUT  list of float vectors, same order, same length
DEPENDS chromadb (local ONNX model) or openai (API embedding)
DOES NOT read files, write to a vector database, or build prompts.

Two REAL implementations (neither is a mock):

  LocalOnnxEmbedder  Chroma's bundled ONNX all-MiniLM-L6-v2. Runs locally,
                     needs no API key. First use downloads ~80 MB into
                     ~/.cache/chroma; after that it is fully offline.
  OpenAIEmbedder     OpenAI-compatible embedding endpoint; needs OPENAI_API_KEY.

Test doubles live in tests/fakes.py and are never imported from src code.
"""

from __future__ import annotations

import os
from collections.abc import Sequence

from ragkit.config import Settings, require_api_key


class LocalOnnxEmbedder:
    """Local, key-free neural embeddings (384-dim all-MiniLM-L6-v2)."""

    name = "local-onnx-minilm"
    dimension = 384

    def __init__(self, dimension: int = 384) -> None:
        self.dimension = dimension
        self._fn = None

    def _ensure_model(self) -> None:
        if self._fn is None:
            # Imported lazily: `import chromadb` is relatively slow, and unit
            # tests that only use fakes should not pay that cost.
            from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

            self._fn = DefaultEmbeddingFunction()

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        self._ensure_model()
        vectors = self._fn(list(texts))
        return [[float(value) for value in vector] for vector in vectors]


class OpenAIEmbedder:
    """OpenAI-compatible embedding endpoint. Requires OPENAI_API_KEY."""

    name = "openai-embedding"

    def __init__(
        self,
        model: str,
        dimension: int,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        from openai import OpenAI

        self.model = model
        self.dimension = dimension
        key = api_key or require_api_key()
        options: dict[str, str] = {"api_key": key}
        if base_url:
            options["base_url"] = base_url
        self._client = OpenAI(**options)

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self._client.embeddings.create(model=self.model, input=list(texts))
        ordered = sorted(response.data, key=lambda item: item.index)
        if len(ordered) != len(texts):
            raise RuntimeError(
                f"embedding API returned {len(ordered)} vectors for {len(texts)} inputs"
            )
        vectors = [list(map(float, item.embedding)) for item in ordered]
        if vectors and len(vectors[0]) != self.dimension:
            raise RuntimeError(
                f"embedding dimension mismatch: expected {self.dimension}, "
                f"got {len(vectors[0])}. Check [embedding].api_dimension in config.toml."
            )
        return vectors


def build_embedder(settings: Settings):
    """Choose the provider declared in config.toml."""
    if settings.embedding_provider == "local":
        return LocalOnnxEmbedder(settings.local_dimension)
    return OpenAIEmbedder(
        model=settings.api_model,
        dimension=settings.api_dimension,
        base_url=os.environ.get("OPENAI_BASE_URL") or None,
    )

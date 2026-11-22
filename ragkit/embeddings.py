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

import math
import os
from collections.abc import Sequence
from numbers import Integral, Real

from ragkit.config import Settings, require_api_key


def _texts(texts: Sequence[str]) -> list[str]:
    if isinstance(texts, (str, bytes)) or not isinstance(texts, Sequence):
        raise ValueError("texts must be a sequence of strings, not a single string")
    result = list(texts)
    if any(not isinstance(text, str) or not text.strip() for text in result):
        raise ValueError("each text must be a nonempty, non-whitespace string")
    return result


def _vectors(vectors, count: int, dimension: int) -> list[list[float]]:
    if vectors is None or not hasattr(vectors, "__len__"):
        raise RuntimeError("embedding output must be a batch of numeric vectors")
    if len(vectors) != count:
        raise RuntimeError(f"embedding returned {len(vectors)} vectors for {count} inputs")
    result = []
    for vector in vectors:
        if vector is None or not hasattr(vector, "__len__") or isinstance(vector, (str, bytes)):
            raise RuntimeError("embedding vector must be a numeric sequence")
        if len(vector) != dimension:
            raise RuntimeError(
                f"embedding dimension mismatch: expected {dimension}, got {len(vector)}"
            )
        if any(isinstance(v, bool) or not isinstance(v, Real) for v in vector):
            raise RuntimeError("embedding vector must contain numeric values")
        converted = [float(value) for value in vector]
        if not all(math.isfinite(value) for value in converted):
            raise RuntimeError("embedding vector must contain finite values")
        if not any(converted):
            raise RuntimeError("zero-norm embedding vector has undefined cosine similarity")
        result.append(converted)
    return result


class LocalOnnxEmbedder:
    """Local, key-free neural embeddings (384-dim all-MiniLM-L6-v2)."""

    name = "local-onnx-minilm"
    dimension = 384

    def __init__(self, dimension: int = 384) -> None:
        if isinstance(dimension, bool) or dimension != 384:
            raise ValueError("local all-MiniLM-L6-v2 requires dimension 384")
        self.dimension = dimension
        self._fn = None

    def _ensure_model(self) -> None:
        if self._fn is None:
            # Imported lazily: `import chromadb` is relatively slow, and unit
            # tests that only use fakes should not pay that cost.
            from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

            self._fn = DefaultEmbeddingFunction()

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        texts = _texts(texts)
        if not texts:
            return []
        self._ensure_model()
        vectors = self._fn(list(texts))
        return _vectors(vectors, len(texts), self.dimension)


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
        if isinstance(dimension, bool) or not isinstance(dimension, Integral) or dimension <= 0:
            raise ValueError("API embedding dimension must be a positive integer")
        if not isinstance(model, str) or not model.strip():
            raise ValueError("API embedding model must be a nonblank string")

        from openai import OpenAI

        self.model = model
        self.dimension = dimension
        key = api_key or require_api_key()
        options: dict[str, str] = {"api_key": key}
        if base_url:
            options["base_url"] = base_url
        self._client = OpenAI(**options)

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        texts = _texts(texts)
        if not texts:
            return []
        response = self._client.embeddings.create(model=self.model, input=list(texts))
        data = getattr(response, "data", None)
        if not isinstance(data, Sequence) or isinstance(data, (str, bytes)):
            raise RuntimeError("embedding API data must be a sequence of embedding records")
        if len(data) != len(texts):
            raise RuntimeError(
                f"embedding API returned {len(data)} vectors for {len(texts)} inputs"
            )
        indices = [getattr(item, "index", None) for item in data]
        if (
            any(isinstance(i, bool) or not isinstance(i, Integral) for i in indices)
            or len(indices) != len(texts)
            or set(indices) != set(range(len(texts)))
        ):
            raise RuntimeError("embedding API indices must be unique integers 0..N-1")
        ordered = sorted(data, key=lambda item: item.index)
        if any(not hasattr(item, "embedding") for item in ordered):
            raise RuntimeError("embedding API record is missing embedding")
        return _vectors([item.embedding for item in ordered], len(texts), self.dimension)


def build_embedder(settings: Settings):
    """Choose the provider declared in config.toml."""
    if settings.embedding_provider == "local":
        if settings.local_model != "all-MiniLM-L6-v2":
            raise ValueError("local model must be all-MiniLM-L6-v2")
        return LocalOnnxEmbedder(settings.local_dimension)
    if settings.embedding_provider != "api":
        raise ValueError("embedding.provider must be 'local' or 'api'")
    return OpenAIEmbedder(
        model=settings.api_model,
        dimension=settings.api_dimension,
        base_url=os.environ.get("OPENAI_BASE_URL") or None,
    )

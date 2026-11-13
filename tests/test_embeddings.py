"""M3 contract tests. No network, no model download, no API key."""

from __future__ import annotations

import pytest

from ragkit.config import load_settings
from ragkit.embeddings import LocalOnnxEmbedder, OpenAIEmbedder, build_embedder
from tests.fakes import FakeEmbedder


def test_fake_embedder_satisfies_the_contract():
    embedder = FakeEmbedder()
    vectors = embedder.embed(["alpha port 8080", "beta port 9090", "alpha port 8080"])
    assert len(vectors) == 3
    assert all(len(vector) == embedder.dimension for vector in vectors)
    assert vectors[0] == vectors[2], "same text must produce the same vector"
    assert vectors[0] != vectors[1]


def test_empty_input_never_calls_a_model():
    assert FakeEmbedder().embed([]) == []
    assert LocalOnnxEmbedder().embed([]) == []


def test_build_embedder_uses_local_provider_by_default():
    settings = load_settings()
    embedder = build_embedder(settings)
    assert isinstance(embedder, LocalOnnxEmbedder)
    assert embedder.dimension == settings.local_dimension == 384


def test_api_embedder_fails_clearly_without_a_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        OpenAIEmbedder(model="text-embedding-3-small", dimension=1536)


def test_bad_provider_is_rejected(tmp_path):
    config = tmp_path / "bad.toml"
    config.write_text(
        (load_settings().root / "config.toml")
        .read_text(encoding="utf-8")
        .replace('provider = "local"', 'provider = "magic"'),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="embedding.provider"):
        load_settings(config)

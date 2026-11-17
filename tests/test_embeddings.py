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


@pytest.mark.parametrize("texts", ["alpha", "", [""], ["  "], ["alpha", 3]])
@pytest.mark.parametrize("kind", ["local", "api"])
def test_invalid_text_inputs_rejected_before_model(kind, texts):
    # MOCK model must never be reached, including during the RED run.
    embedder = LocalOnnxEmbedder() if kind == "local" else OpenAIEmbedder.__new__(OpenAIEmbedder)
    if kind == "local":

        def forbidden_model(_texts):
            raise AssertionError("MOCK model was invoked")

        embedder._fn = forbidden_model
    with pytest.raises(ValueError, match="text|string"):
        embedder.embed(texts)


def _mock_api(data, dimension=2):
    from types import SimpleNamespace

    embedder = OpenAIEmbedder.__new__(OpenAIEmbedder)
    embedder.model = "MOCK-no-network"
    embedder.dimension = dimension
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(data=[SimpleNamespace(index=i, embedding=v) for i, v in data])

    embedder._client = SimpleNamespace(embeddings=SimpleNamespace(create=create))
    return embedder, calls


@pytest.mark.parametrize(
    "vectors",
    [
        [],
        [[1, 0]],
        [[1, 0], []],
        [[1, 0], [1]],
        [[1, 0], [float("nan"), 0]],
        [[1, 0], [float("inf"), 0]],
        [[1, 0], ["1", 0]],
    ],
)
@pytest.mark.parametrize("kind", ["local", "api"])
def test_every_output_vector_validated(kind, vectors):
    if kind == "local":
        embedder = LocalOnnxEmbedder()
        # Keep malformed values at the real local dimension so finite/numeric
        # guards cannot be masked by the dimension guard.
        vectors = (
            [[1.0] * 384, *(v + [0.0] * 382 if len(v) == 2 else v for v in vectors[1:])]
            if vectors
            else []
        )
        # MOCK local function: no model initialization or download.
        embedder._fn = lambda texts: vectors
    else:
        embedder, _ = _mock_api(list(enumerate(vectors)))
    with pytest.raises(RuntimeError, match="vector|dimension|numeric|finite"):
        embedder.embed(["alpha", "beta"])


@pytest.mark.parametrize("indices", [[0, 0], [1, 2], [-1, 0], [0.0, 1], [False, 1], ["0", 1]])
def test_api_rejects_invalid_indices_before_ordering(indices):
    embedder, _ = _mock_api([(i, [1, 0]) for i in indices])
    with pytest.raises(RuntimeError, match="indices"):
        embedder.embed(["alpha", "beta"])


@pytest.mark.parametrize(
    "changes, message",
    [
        ({"embedding_provider": "magic"}, "provider"),
        ({"local_dimension": 128}, "384"),
        ({"local_model": "unsupported-model"}, "model"),
    ],
)
def test_build_rejects_invalid_configuration_without_client(changes, message, monkeypatch):
    from types import SimpleNamespace

    import ragkit.embeddings as module

    # MOCK API constructor: an unknown provider must fail before constructing a client.
    monkeypatch.setattr(module, "OpenAIEmbedder", lambda **kwargs: pytest.fail("MOCK API invoked"))
    options = {
        "embedding_provider": "local",
        "local_dimension": 384,
        "local_model": "all-MiniLM-L6-v2",
        "api_model": "MOCK",
        "api_dimension": 2,
    }
    options.update(changes)
    with pytest.raises(ValueError, match=message):
        build_embedder(SimpleNamespace(**options))


@pytest.mark.parametrize("kind", ["local", "api"])
def test_zero_norm_output_rejected(kind):
    if kind == "local":
        embedder = LocalOnnxEmbedder()
        embedder._fn = lambda texts: [[0.0] * 384]  # MOCK model output
    else:
        embedder, _ = _mock_api([(0, [0.0, 0.0])])
    with pytest.raises(RuntimeError, match="zero-norm"):
        embedder.embed(["alpha"])


def test_baseline_mock_api_sorting_and_empty_batch():
    embedder, calls = _mock_api([(1, [0, 1]), (0, [1, 0])])
    assert embedder.embed([]) == []
    assert calls == []
    assert embedder.embed(["alpha", "beta"]) == [[1.0, 0.0], [0.0, 1.0]]
    assert calls == [{"model": "MOCK-no-network", "input": ["alpha", "beta"]}]


def test_baseline_mock_local_count_order_and_empty_batch():
    embedder = LocalOnnxEmbedder()
    calls = []

    def mock_model(texts):
        calls.append(texts)
        return [[float(i + 1)] * 384 for i in range(len(texts))]

    embedder._fn = mock_model
    assert embedder.embed([]) == []
    assert calls == []
    assert embedder.embed(["beta", "alpha"]) == [[1.0] * 384, [2.0] * 384]
    assert calls == [["beta", "alpha"]]


@pytest.mark.parametrize("vectors", [None, [None, [1, 0]], [[1, 0], [True, 0]]])
def test_malformed_model_output_has_actionable_error(vectors):
    embedder, _ = _mock_api([])
    if vectors is None:
        embedder = LocalOnnxEmbedder()
        embedder._fn = lambda texts: None  # MOCK malformed model output
    else:
        embedder, _ = _mock_api(list(enumerate(vectors)))
    with pytest.raises(RuntimeError, match="vector|numeric"):
        embedder.embed(["alpha", "beta"])


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf")])
@pytest.mark.parametrize("kind", ["local", "api"])
def test_full_dimension_nonfinite_output_rejected_as_nonfinite(kind, bad):
    if kind == "local":
        embedder = LocalOnnxEmbedder()
        embedder._fn = lambda texts: [[1.0] * 384, [bad] + [0.0] * 383]
    else:
        embedder, _ = _mock_api([(0, [1, 0]), (1, [bad, 0])])
    with pytest.raises(RuntimeError, match="finite"):
        embedder.embed(["alpha", "beta"])


@pytest.mark.parametrize("malformation", ["data_none", "missing_index", "missing_embedding"])
def test_api_malformed_fields_have_descriptive_errors(malformation):
    from types import SimpleNamespace

    embedder, _ = _mock_api([])
    data = {
        "data_none": None,
        "missing_index": [SimpleNamespace(embedding=[1, 0])],
        "missing_embedding": [SimpleNamespace(index=0)],
    }[malformation]
    embedder._client.embeddings.create = lambda **kwargs: SimpleNamespace(data=data)
    with pytest.raises(RuntimeError, match="embedding API.*(data|indices|embedding)"):
        embedder.embed(["alpha"])


@pytest.mark.parametrize("dimension", [True, False, 0, -1, 2.0, "2", None])
def test_api_invalid_dimension_rejected_before_client(dimension, monkeypatch):
    import openai

    monkeypatch.setattr(openai, "OpenAI", lambda **kwargs: pytest.fail("API client constructed"))
    with pytest.raises(ValueError, match="dimension.*positive integer"):
        OpenAIEmbedder(model="MOCK", dimension=dimension, api_key="MOCK-unused")


@pytest.mark.parametrize("model", ["", "  ", None, 2])
def test_api_invalid_model_rejected_before_client(model, monkeypatch):
    import openai

    monkeypatch.setattr(openai, "OpenAI", lambda **kwargs: pytest.fail("API client constructed"))
    with pytest.raises(ValueError, match="model.*nonblank"):
        OpenAIEmbedder(model=model, dimension=2, api_key="MOCK-unused")

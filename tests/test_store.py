"""M4 tests: real ChromaDB persistence, but with MOCK vectors (no model download)."""

from __future__ import annotations

import pytest

pytest.importorskip("chromadb", reason="chromadb is a runtime dependency")

from ragkit.contracts import Chunk  # noqa: E402
from ragkit.store import ChromaStore  # noqa: E402
from tests.fakes import FakeEmbedder  # noqa: E402

TEXTS = [
    "The alpha service listens on port 8080 and writes logs to a file.",
    "The beta service listens on port 9090 and is read-only.",
    "Vector databases store embeddings together with metadata.",
]


def _chunk(chunk_id: str, text: str) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        doc_id=chunk_id.split("#")[0],
        text=text,
        char_start=0,
        char_end=len(text),
        strategy="fixed",
        index=int(chunk_id.split("#")[1]),
        title="Test document",
        source_uri="https://example.test/source",
        license="TEST",
        meta={"chunk_size": 400, "chunk_overlap": 50},
    )


@pytest.fixture
def chunks():
    return [_chunk(f"doc_{i}#0000", text) for i, text in enumerate(TEXTS)]


def test_upsert_then_search_returns_ranked_hits(tmp_path, chunks):
    embedder = FakeEmbedder()
    store = ChromaStore(tmp_path / "index", "test_collection")
    store.upsert(chunks, embedder.embed([c.text for c in chunks]))
    assert store.count() == len(chunks)

    query = embedder.embed([TEXTS[0]])[0]
    hits = store.search(query, k=2)
    assert len(hits) == 2
    assert hits[0].chunk.chunk_id == chunks[0].chunk_id
    assert hits[0].score >= hits[1].score
    assert [hit.rank for hit in hits] == [1, 2]
    assert hits[0].score > 0.99, "an identical vector must score ~1.0"


def test_index_survives_reopening_the_client(tmp_path, chunks):
    embedder = FakeEmbedder()
    first = ChromaStore(tmp_path / "index", "persist_collection")
    first.upsert(chunks, embedder.embed([c.text for c in chunks]))
    second = ChromaStore(tmp_path / "index", "persist_collection")
    assert second.count() == len(chunks)
    assert second.search(embedder.embed([TEXTS[1]])[0], k=1)[0].chunk.chunk_id == chunks[1].chunk_id


def test_get_chunk_roundtrips_provenance_for_citation_checks(tmp_path, chunks):
    embedder = FakeEmbedder()
    store = ChromaStore(tmp_path / "index", "provenance_collection")
    store.upsert(chunks, embedder.embed([c.text for c in chunks]))
    restored = store.get_chunk(chunks[0].chunk_id)
    assert restored is not None
    assert restored.text == chunks[0].text
    assert restored.doc_id == chunks[0].doc_id
    assert restored.title == chunks[0].title
    assert restored.source_uri == chunks[0].source_uri
    assert restored.char_start == chunks[0].char_start
    assert restored.strategy == chunks[0].strategy
    assert store.get_chunk("does_not_exist#0000") is None


def test_clear_and_empty_index(tmp_path, chunks):
    embedder = FakeEmbedder()
    store = ChromaStore(tmp_path / "index", "clear_collection")
    assert store.search(embedder.embed(["anything"])[0], k=3) == []
    store.upsert(chunks, embedder.embed([c.text for c in chunks]))
    store.clear()
    assert store.count() == 0


def test_mismatched_batch_is_rejected(tmp_path, chunks):
    store = ChromaStore(tmp_path / "index", "mismatch_collection")
    with pytest.raises(ValueError, match="one vector per chunk"):
        store.upsert(chunks, [[0.0, 1.0]])


def test_standard_collection_rejects_wrong_strategy_atomically(tmp_path, chunks):
    from dataclasses import replace

    store = ChromaStore(tmp_path)
    with pytest.raises(ValueError, match="strategy"):
        store.upsert([chunks[0], replace(chunks[1], strategy="paragraph")], [[1, 0]] * 2)
    assert store.count() == 0


def test_full_chunk_roundtrip_preserves_nested_metadata(tmp_path, chunks):
    from dataclasses import replace

    chunk = replace(
        chunks[0],
        char_start=17,
        char_end=81,
        index=9,
        meta={
            "chunk_size": 80,
            "chunk_overlap": 10,
            "chunk_overlap_actual": 7,
            "nested": {"labels": ["MOCK", None, True]},
            "extra": 3.25,
        },
    )
    store = ChromaStore(tmp_path)
    store.upsert([chunk], [[1, 0]])
    reopened = ChromaStore(tmp_path)
    assert reopened.get_chunk(chunk.chunk_id) == chunk
    assert reopened.search([1, 0], 1)[0].chunk == chunk


@pytest.mark.parametrize("bad", [[], [0, 0], [float("nan"), 1], [float("inf"), 1], [1, 0, 0]])
def test_invalid_append_and_query_rejected_after_reopen(tmp_path, chunks, bad):
    store = ChromaStore(tmp_path)
    store.upsert([chunks[0]], [[1, 0]])
    store = ChromaStore(tmp_path)
    with pytest.raises(ValueError, match="vector|dimension"):
        store.upsert([chunks[1]], [bad])
    assert store.count() == 1
    with pytest.raises(ValueError, match="vector|dimension"):
        store.search(bad, 1)


def test_reopening_non_cosine_collection_is_rejected(tmp_path):
    import chromadb
    from chromadb.config import Settings

    client = chromadb.PersistentClient(str(tmp_path), settings=Settings(anonymized_telemetry=False))
    collection = client.create_collection("legacy_l2", configuration={"hnsw": {"space": "l2"}})
    assert collection.configuration["hnsw"]["space"] == "l2"
    with pytest.raises(ValueError, match="cosine"):
        ChromaStore(tmp_path, "legacy_l2")


def test_ranks_follow_sorted_scores_with_negative_similarity(tmp_path, chunks, monkeypatch):
    store = ChromaStore(tmp_path)
    store.upsert(chunks[:2], [[1, 0], [-1, 0]])
    # MOCK an unsorted backend response; rank must describe returned order.
    monkeypatch.setattr(
        store._collection,
        "query",
        lambda **kwargs: {
            "ids": [[c.chunk_id for c in chunks[:2]]],
            "documents": [[c.text for c in chunks[:2]]],
            "metadatas": [[None, None]],
            "distances": [[2.0, 0.0]],
        },
    )
    hits = store.search([1, 0], 2)
    assert [hit.score for hit in hits] == [1.0, -1.0]
    assert [hit.rank for hit in hits] == [1, 2]


def test_baseline_strategy_isolation_upsert_reopen_and_clear(tmp_path, chunks):
    from dataclasses import replace

    fixed = ChromaStore(tmp_path)
    paragraph = ChromaStore(tmp_path, "chunks_paragraph")
    para_chunk = replace(chunks[0], text="MOCK paragraph", strategy="paragraph")
    fixed.upsert([chunks[0]], [[1, 0]])
    fixed.upsert([chunks[0]], [[1, 0]])
    paragraph.upsert([para_chunk], [[0, 1]])
    fixed = ChromaStore(tmp_path)
    paragraph = ChromaStore(tmp_path, "chunks_paragraph")
    assert fixed.count() == paragraph.count() == 1
    assert fixed.get_chunk(chunks[0].chunk_id) == chunks[0]
    assert paragraph.get_chunk(chunks[0].chunk_id) == para_chunk
    fixed.clear()
    fixed.clear()
    assert fixed.count() == 0
    assert paragraph.get_chunk(para_chunk.chunk_id) == para_chunk
    with pytest.raises(ValueError, match="strategy"):
        paragraph.upsert([chunks[0]], [[1, 0]])


def test_baseline_custom_strategy_and_build_store(tmp_path, chunks):
    from types import SimpleNamespace

    from ragkit.store import build_store

    settings = SimpleNamespace(
        index_dir=tmp_path, collection_name="custom_index", chunk_strategy="fixed"
    )
    store = build_store(settings)
    store.upsert([chunks[0]], [[1, 0]])
    assert ChromaStore(tmp_path, "custom_index").count() == 1
    with pytest.raises(ValueError, match="strategy"):
        from dataclasses import replace

        store.upsert([replace(chunks[1], strategy="paragraph")], [[1, 0]])


def test_baseline_invalid_batches_do_not_mutate(tmp_path, chunks):
    store = ChromaStore(tmp_path)
    store.upsert([], [])
    for batch, vectors in [
        ([chunks[0]] * 2, [[1, 0]] * 2),
        (chunks[:2], [[1, 0], [1, 0, 0]]),
        (chunks[:2], [[1, 0], [0, 0]]),
    ]:
        with pytest.raises(ValueError):
            store.upsert(batch, vectors)
        assert store.count() == 0
    store.upsert(chunks[:2], [[1, 0], [-1, 0]])
    assert store.search([], 0) == store.search([], -1) == []
    hits = store.search([1, 0], 100)
    assert len(hits) == 2
    assert hits[-1].score == pytest.approx(-1)


def test_baseline_legacy_scalar_metadata_remains_readable(tmp_path):
    store = ChromaStore(tmp_path)
    store._collection.upsert(
        ids=["legacy#0000"],
        embeddings=[[1, 0]],
        documents=["MOCK legacy"],
        metadatas=[
            {
                "doc_id": "legacy",
                "strategy": "fixed",
                "index": 0,
                "char_start": 9,
                "char_end": 20,
                "chunk_size": 80,
            }
        ],
    )
    chunk = store.get_chunk("legacy#0000")
    assert chunk.meta == {"chunk_size": 80}
    assert chunk.char_start == 9 and chunk.char_end == 20
    assert chunk.source_uri == chunk.license == ""


def test_custom_collection_retains_strategy_binding_after_reopen(tmp_path, chunks):
    from dataclasses import replace

    store = ChromaStore(tmp_path, "custom_bound")
    store.upsert([chunks[0]], [[1, 0]])
    reopened = ChromaStore(tmp_path, "custom_bound")
    with pytest.raises(ValueError, match="strategy"):
        reopened.upsert([replace(chunks[1], strategy="paragraph")], [[0, 1]])
    assert reopened.count() == 1


def test_legacy_missing_strategy_can_be_read_but_not_mixed_on_write(tmp_path, chunks):
    store = ChromaStore(tmp_path, "legacy_unknown")
    store._collection.upsert(
        ids=["legacy#0000"],
        embeddings=[[1, 0]],
        documents=["MOCK legacy"],
        metadatas=[{"title": "Legacy"}],
    )
    reopened = ChromaStore(tmp_path, "legacy_unknown")
    legacy = reopened.get_chunk("legacy#0000")
    assert legacy.strategy == "unknown"
    assert legacy.meta == {}
    reopened.upsert([], [])
    with pytest.raises(ValueError, match="strategy"):
        reopened.upsert([chunks[0]], [[1, 0]])
    assert reopened.count() == 1


def test_unserializable_metadata_is_rejected_before_any_write(tmp_path, chunks):
    from dataclasses import replace

    store = ChromaStore(tmp_path)
    with pytest.raises(ValueError, match="meta|JSON"):
        store.upsert([chunks[0], replace(chunks[1], meta={"unsupported": {1, 2}})], [[1, 0]] * 2)
    assert store.count() == 0


def test_preopened_custom_clients_recheck_strategy(tmp_path, chunks):
    from dataclasses import replace

    first = ChromaStore(tmp_path, "shared_custom")
    second = ChromaStore(tmp_path, "shared_custom")
    first.upsert([chunks[0]], [[1, 0]])
    with pytest.raises(ValueError, match="strategy"):
        second.upsert([replace(chunks[1], strategy="paragraph")], [[0, 1]])
    assert first.count() == 1


@pytest.mark.parametrize("conflict", ["strategy", "dimension"])
def test_overlapping_custom_writers_recheck_under_lock(tmp_path, chunks, monkeypatch, conflict):
    from concurrent.futures import ThreadPoolExecutor
    from dataclasses import replace
    from threading import Event

    first = ChromaStore(tmp_path, "overlapping_custom")
    second = ChromaStore(tmp_path, "overlapping_custom")
    entered = Event()
    release = Event()
    second_started = Event()
    second_entered = Event()
    original = type(first._collection).upsert

    def paused_upsert(collection, **kwargs):
        if kwargs["ids"] == [chunks[0].chunk_id]:
            entered.set()
            assert release.wait(10), "test did not release first writer"
        else:
            second_entered.set()
        return original(collection, **kwargs)

    monkeypatch.setattr(type(first._collection), "upsert", paused_upsert)
    other = replace(chunks[1], strategy="paragraph") if conflict == "strategy" else chunks[1]
    vector = [0, 1] if conflict == "strategy" else [0, 1, 0]

    def write_second():
        second_started.set()
        second.upsert([other], [vector])

    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(first.upsert, [chunks[0]], [[1, 0]])
        try:
            assert entered.wait(10)
            b = pool.submit(write_second)
            assert second_started.wait(10)
            overlapped = second_entered.wait(0.5)
        finally:
            release.set()
        a.result(timeout=10)
        with pytest.raises(ValueError, match=conflict):
            b.result(timeout=10)
    assert not overlapped, "second writer mutated while first writer held the collection"
    assert first.count() == 1


def test_preopened_client_writes_after_other_client_clear(tmp_path, chunks):
    from dataclasses import replace

    first = ChromaStore(tmp_path, "cleared_custom")
    first.upsert([chunks[0]], [[1, 0]])
    second = ChromaStore(tmp_path, "cleared_custom")
    first.clear()
    paragraph = replace(chunks[1], strategy="paragraph")
    second.upsert([paragraph], [[0, 1, 0]])
    assert second.get_chunk(paragraph.chunk_id) == paragraph
    first.clear()
    assert first.count() == 0



def test_preopened_client_reads_after_other_client_rebuild(tmp_path, chunks):
    """Read clients should track collection replacement, not stale collection UUIDs."""
    first = ChromaStore(tmp_path, "rebound_readers")
    second = ChromaStore(tmp_path, "rebound_readers")
    first.upsert([chunks[0]], [[1, 0]])
    assert second.get_chunk(chunks[0].chunk_id) == chunks[0]

    first.clear()
    assert second.count() == 0
    assert second.get_chunk(chunks[0].chunk_id) is None
    assert second.search([1, 0], 3) == []

    first.upsert([chunks[1]], [[0, 1]])
    assert second.count() == 1
    assert second.get_chunk(chunks[1].chunk_id) == chunks[1]
    assert second.search([0, 1], 1)[0].chunk == chunks[1]



@pytest.mark.parametrize("scale", [1e-50, 1e-30, 1e20, 1e308, 5e-324])
def test_extreme_finite_vectors_preserve_real_chroma_cosine(tmp_path, chunks, scale):
    import math

    store = ChromaStore(tmp_path, "stable_cosine")
    store.upsert(chunks[:2], [[scale, 0], [-scale, 0]])
    saved = store._collection.get(include=["embeddings"])["embeddings"]
    for vector in saved:
        assert all(math.isfinite(float(value)) for value in vector)
        assert math.hypot(*vector) == pytest.approx(1.0)
    for query in ([scale, 0], [1, 0]):
        hits = store.search(query, 2)
        assert [hit.chunk.chunk_id for hit in hits] == [c.chunk_id for c in chunks[:2]]
        assert [hit.score for hit in hits] == pytest.approx([1, -1], abs=1e-6)


def test_stable_normalization_preserves_non_axis_direction(tmp_path, chunks):
    store = ChromaStore(tmp_path, "directional_cosine")
    store.upsert(chunks[:2], [[1e308, 1e308], [-1e-300, -1e-300]])
    hits = store.search([1e-300, 1e-300], 2)
    assert [hit.score for hit in hits] == pytest.approx([1, -1], abs=1e-6)
    saved = store._collection.get(include=["embeddings"])["embeddings"]
    assert saved[0] == pytest.approx([2**-0.5, 2**-0.5])


@pytest.mark.parametrize("distance", [float("nan"), float("inf"), -float("inf"), -0.01, 2.01])
def test_backend_invalid_cosine_distances_rejected(tmp_path, chunks, monkeypatch, distance):
    store = ChromaStore(tmp_path)
    store.upsert(chunks[:1], [[1, 0]])
    monkeypatch.setattr(
        store._collection,
        "query",
        lambda **kwargs: {
            "ids": [[chunks[0].chunk_id]],
            "documents": [[chunks[0].text]],
            "metadatas": [[None]],
            "distances": [[distance]],
        },
    )
    with pytest.raises(RuntimeError, match="cosine distance"):
        store.search([1, 0], 1)


@pytest.mark.parametrize("distance", [-1e-7, 2 + 1e-7])
def test_backend_distance_roundoff_is_tolerated_without_clipping(
    tmp_path, chunks, monkeypatch, distance
):
    store = ChromaStore(tmp_path)
    store.upsert(chunks[:1], [[1, 0]])
    monkeypatch.setattr(
        store._collection,
        "query",
        lambda **kwargs: {
            "ids": [[chunks[0].chunk_id]],
            "documents": [[chunks[0].text]],
            "metadatas": [[None]],
            "distances": [[distance]],
        },
    )
    assert store.search([1, 0], 1)[0].score == 1 - distance


@pytest.mark.parametrize("strategies", [[None, None], ["fixed", "paragraph"]])
def test_preopened_client_detects_current_legacy_binding(tmp_path, chunks, strategies):
    store = ChromaStore(tmp_path, "legacy_live")
    store._collection.upsert(
        ids=[c.chunk_id for c in chunks[:2]],
        documents=[c.text for c in chunks[:2]],
        embeddings=[[1, 0], [0, 1]],
        metadatas=[{"title": "Legacy", **({"strategy": s} if s else {})} for s in strategies],
    )
    assert store.get_chunk(chunks[0].chunk_id) is not None
    with pytest.raises(ValueError, match="mixed or unknown strategy"):
        store.upsert(chunks[2:], [[1, 0]])
    assert store.count() == 2
    store.clear()
    store.upsert(chunks[2:], [[1, 0, 0]])
    assert store.count() == 1


def test_clear_waits_for_overlapping_write_and_only_clears_target(tmp_path, chunks, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    writer = ChromaStore(tmp_path, "clear_overlap")
    clearer = ChromaStore(tmp_path, "clear_overlap")
    other = ChromaStore(tmp_path, "untouched_collection")
    other.upsert(chunks[1:2], [[0, 1]])
    entered = Event()
    release = Event()
    clear_started = Event()
    deleted = Event()
    original_upsert = type(writer._collection).upsert
    original_delete = type(clearer._client).delete_collection

    def paused_upsert(collection, **kwargs):
        entered.set()
        assert release.wait(10)
        return original_upsert(collection, **kwargs)

    def observed_delete(client, **kwargs):
        deleted.set()
        return original_delete(client, **kwargs)

    def clear():
        clear_started.set()
        clearer.clear()

    monkeypatch.setattr(type(writer._collection), "upsert", paused_upsert)
    monkeypatch.setattr(type(clearer._client), "delete_collection", observed_delete)
    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(writer.upsert, chunks[:1], [[1, 0]])
        try:
            assert entered.wait(10)
            b = pool.submit(clear)
            assert clear_started.wait(10)
            overlapped = deleted.wait(0.5)
        finally:
            release.set()
        a.result(timeout=10)
        b.result(timeout=10)
    assert not overlapped, "clear deleted the collection while a write was in progress"
    assert clearer.count() == 0
    assert other.get_chunk(chunks[1].chunk_id) == chunks[1]

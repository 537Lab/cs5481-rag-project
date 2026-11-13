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
    assert second.search(embedder.embed([TEXTS[1]])[0], k=1)[0].chunk.chunk_id == chunks[
        1
    ].chunk_id


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

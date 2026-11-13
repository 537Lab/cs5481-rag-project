"""M4 - Vector storage and retrieval.

INPUT   (Chunk, vector) pairs on write; a query vector + k on read
OUTPUT  list[RetrievedChunk], sorted by descending cosine similarity
DEPENDS chromadb (embedded, persistent, no server to start)
DOES NOT compute embeddings, read source documents, or build prompts.

Chroma stores the text and provenance metadata alongside each vector, so
`get_chunk(chunk_id)` can re-open the exact source slice for citation checking
without going back to the original files.

score = 1 - cosine_distance, so HIGHER is better and 0 means unrelated.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from ragkit.contracts import Chunk, RetrievedChunk


def _metadata(chunk: Chunk) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "doc_id": chunk.doc_id,
        "title": chunk.title,
        "source_uri": chunk.source_uri,
        "license": chunk.license,
        "strategy": chunk.strategy,
        "index": chunk.index,
        "char_start": chunk.char_start,
        "char_end": chunk.char_end,
        "chunk_size": chunk.meta.get("chunk_size", 0),
        "chunk_overlap": chunk.meta.get("chunk_overlap", 0),
        "chunk_overlap_actual": chunk.meta.get("chunk_overlap_actual", 0),
    }
    # Chroma metadata only accepts str / int / float / bool (never None).
    return {k: v for k, v in meta.items() if v is not None}


def _chunk_from_record(
    chunk_id: str, text: str, meta: dict[str, Any] | None
) -> Chunk:
    meta = meta or {}
    return Chunk(
        chunk_id=chunk_id,
        doc_id=str(meta.get("doc_id", chunk_id.split("#")[0])),
        text=text,
        char_start=int(meta.get("char_start", 0)),
        char_end=int(meta.get("char_end", len(text))),
        strategy=str(meta.get("strategy", "unknown")),
        index=int(meta.get("index", 0)),
        title=str(meta.get("title", "")),
        source_uri=str(meta.get("source_uri", "")),
        license=str(meta.get("license", "")),
        meta={
            "chunk_size": int(meta.get("chunk_size", 0)),
            "chunk_overlap": int(meta.get("chunk_overlap", 0)),
            "chunk_overlap_actual": int(meta.get("chunk_overlap_actual", 0)),
        },
    )


class ChromaStore:
    def __init__(self, index_dir: str | Path, collection_name: str = "chunks_fixed") -> None:
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name
        self._client = chromadb.PersistentClient(
            path=str(self.index_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert(self, chunks: Sequence[Chunk], vectors: Sequence[Sequence[float]]) -> None:
        if len(chunks) != len(vectors):
            raise ValueError(
                f"upsert needs one vector per chunk: {len(chunks)} chunks, {len(vectors)} vectors"
            )
        ids = [chunk.chunk_id for chunk in chunks]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate chunk_id in upsert batch")
        if not ids:
            return
        self._collection.upsert(
            ids=ids,
            embeddings=[list(map(float, vector)) for vector in vectors],
            documents=[chunk.text for chunk in chunks],
            metadatas=[_metadata(chunk) for chunk in chunks],
        )

    def search(self, query_vector: Sequence[float], k: int) -> list[RetrievedChunk]:
        total = self.count()
        if total == 0 or k <= 0:
            return []
        result = self._collection.query(
            query_embeddings=[list(map(float, query_vector))],
            n_results=min(k, total),
            include=["documents", "metadatas", "distances"],
        )
        ids = result["ids"][0]
        documents = result["documents"][0]
        metadatas = result["metadatas"][0]
        distances = result["distances"][0]
        hits = [
            RetrievedChunk(
                chunk=_chunk_from_record(cid, text, meta),
                score=1.0 - float(distance),
                rank=rank,
            )
            for rank, (cid, text, meta, distance) in enumerate(
                zip(ids, documents, metadatas, distances, strict=True), start=1
            )
        ]
        return sorted(hits, key=lambda hit: (-hit.score, hit.rank))

    def get_chunk(self, chunk_id: str) -> Chunk | None:
        result = self._collection.get(ids=[chunk_id], include=["documents", "metadatas"])
        if not result["ids"]:
            return None
        return _chunk_from_record(
            result["ids"][0], result["documents"][0], result["metadatas"][0]
        )

    def count(self) -> int:
        return int(self._collection.count())

    def clear(self) -> None:
        """Drop and recreate the collection. Used by `cli ingest` for a clean rebuild."""
        self._client.delete_collection(name=self.collection_name)
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )


def build_store(settings) -> ChromaStore:
    return ChromaStore(settings.index_dir, settings.collection_name)

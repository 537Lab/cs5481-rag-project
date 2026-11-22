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

import json
import math
import os
from collections.abc import Callable, Sequence
from contextlib import contextmanager
from dataclasses import replace
from hashlib import sha256
from numbers import Real
from pathlib import Path
from typing import Any, TypeVar

from ragkit.contracts import Chunk, RetrievedChunk

_ReadResult = TypeVar("_ReadResult")


@contextmanager
def _collection_write_lock(index_dir: Path, collection_name: str):
    """Serialize cooperating embedded local writers, including across processes."""
    key = sha256(collection_name.encode("utf-8")).hexdigest()
    # Keep the inode: unlinking a lock file could let writers lock different files.
    with (index_dir / f".chroma-write-{key}.lock").open("a+b") as lock:
        if os.name == "nt":
            import msvcrt

            lock.seek(0, os.SEEK_END)
            if lock.tell() == 0:
                lock.write(b"\0")
                lock.flush()
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def _vector(values: Sequence[float], dimension: int | None = None) -> list[float]:
    if not len(values) or any(isinstance(v, bool) or not isinstance(v, Real) for v in values):
        raise ValueError("vector must contain nonempty numeric values")
    result = [float(v) for v in values]
    if not all(math.isfinite(v) for v in result):
        raise ValueError("vector values must be finite")
    if not any(result):
        raise ValueError("zero-norm vector has undefined cosine similarity")
    if dimension is not None and len(result) != dimension:
        raise ValueError(f"vector dimension mismatch: expected {dimension}, got {len(result)}")
    # Scale first: directly squaring finite inputs can underflow or overflow.
    scale = max(abs(value) for value in result)
    scaled = [value / scale for value in result]
    norm = math.sqrt(math.fsum(value * value for value in scaled))
    return [value / norm for value in scaled]


def _metadata(chunk: Chunk) -> dict[str, Any]:
    try:
        encoded = json.dumps(chunk.meta, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("Chunk.meta must be losslessly JSON serializable") from exc
    if json.loads(encoded) != chunk.meta:
        raise ValueError("Chunk.meta must be losslessly JSON serializable")
    meta: dict[str, Any] = {
        "_chunk_meta_json": encoded,
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


def _chunk_from_record(chunk_id: str, text: str, meta: dict[str, Any] | None) -> Chunk:
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
        meta=json.loads(meta["_chunk_meta_json"])
        if "_chunk_meta_json" in meta
        else {
            key: meta[key]
            for key in ("chunk_size", "chunk_overlap", "chunk_overlap_actual")
            if key in meta
        },
    )


class ChromaStore:
    def __init__(
        self,
        index_dir: str | Path,
        collection_name: str = "chunks_fixed",
        *,
        strategy: str | None = None,
    ) -> None:
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name
        inferred = {"chunks_fixed": "fixed", "chunks_paragraph": "paragraph"}.get(collection_name)
        if strategy is not None and inferred is not None and strategy != inferred:
            raise ValueError("collection name and strategy disagree")
        self._expected_strategy = strategy or inferred
        self.strategy = self._expected_strategy
        self._client = chromadb.PersistentClient(
            path=str(self.index_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        with _collection_write_lock(self.index_dir, self.collection_name):
            self._collection = self._client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            self._read_binding()

    def _read_binding(self) -> None:
        self.strategy = self._expected_strategy
        config = self._collection.configuration
        index_config = config.get("hnsw") or config.get("spann") or {}
        if index_config.get("space") != "cosine":
            raise ValueError("collection must use cosine distance; rebuild under a new name")
        records = self._collection.get(include=["metadatas"])
        existing = {(meta or {}).get("strategy") for meta in records["metadatas"]}
        self._unknown_strategy = bool(existing) and (len(existing) != 1 or None in existing)
        if existing and not self._unknown_strategy:
            stored_strategy = existing.pop()
            if self.strategy is not None and self.strategy != stored_strategy:
                raise ValueError("existing collection strategy disagrees with requested strategy")
            self.strategy = stored_strategy

    def upsert(self, chunks: Sequence[Chunk], vectors: Sequence[Sequence[float]]) -> None:
        if len(chunks) != len(vectors):
            raise ValueError(
                f"upsert needs one vector per chunk: {len(chunks)} chunks, {len(vectors)} vectors"
            )
        if not chunks:
            return
        with _collection_write_lock(self.index_dir, self.collection_name):
            # clear() on another client replaces the collection's ID.
            self._collection = self._client.get_collection(name=self.collection_name)
            self._read_binding()
            if chunks and self._unknown_strategy:
                raise ValueError(
                    "existing collection has mixed or unknown strategy; rebuild before writing"
                )
            batch_strategies = {chunk.strategy for chunk in chunks}
            if len(batch_strategies) > 1 or (
                self.strategy is not None and any(c.strategy != self.strategy for c in chunks)
            ):
                raise ValueError(f"collection requires a single strategy: {self.strategy!r}")
            ids = [chunk.chunk_id for chunk in chunks]
            if len(set(ids)) != len(ids):
                raise ValueError("duplicate chunk_id in upsert batch")
            dimension = self._stored_dimension()
            validated = []
            for vector in vectors:
                validated.append(_vector(vector, dimension))
                dimension = len(validated[-1])
            self._collection.upsert(
                ids=ids,
                embeddings=validated,
                documents=[chunk.text for chunk in chunks],
                metadatas=[_metadata(chunk) for chunk in chunks],
            )
            self.strategy = chunks[0].strategy

    def _stored_dimension(self) -> int | None:
        records = self._collection.get(limit=1, include=["embeddings"])
        embeddings = records["embeddings"]
        return len(embeddings[0]) if embeddings is not None and len(embeddings) else None

    def _retry_stale_read(self, operation: Callable[[], _ReadResult]) -> _ReadResult:
        """Rebind only when a peer has replaced our Chroma collection UUID."""
        from chromadb.errors import NotFoundError

        try:
            return operation()
        except NotFoundError:
            # Peer clear() uses this lock while deleting/recreating the collection.
            # Refresh under the same lock; normal reads avoid another backend lookup.
            with _collection_write_lock(self.index_dir, self.collection_name):
                self._collection = self._client.get_collection(name=self.collection_name)
                self._read_binding()
                return operation()

    def search(self, query_vector: Sequence[float], k: int) -> list[RetrievedChunk]:
        return self._retry_stale_read(lambda: self._search_current(query_vector, k))

    def _search_current(self, query_vector: Sequence[float], k: int) -> list[RetrievedChunk]:
        total = self.count()
        if total == 0 or k <= 0:
            return []
        result = self._collection.query(
            query_embeddings=[_vector(query_vector, self._stored_dimension())],
            n_results=min(k, total),
            include=["documents", "metadatas", "distances"],
        )
        ids = result["ids"][0]
        documents = result["documents"][0]
        metadatas = result["metadatas"][0]
        distances = [float(distance) for distance in result["distances"][0]]
        # Cosine distances are in [0, 2], allowing float32 roundoff only.
        if any(not math.isfinite(d) or d < -1e-6 or d > 2 + 1e-6 for d in distances):
            raise RuntimeError("backend returned invalid cosine distance (expected finite [0, 2])")
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
        return [
            replace(hit, rank=rank)
            for rank, hit in enumerate(sorted(hits, key=lambda hit: -hit.score), start=1)
        ]

    def get_chunk(self, chunk_id: str) -> Chunk | None:
        return self._retry_stale_read(lambda: self._get_chunk_current(chunk_id))

    def _get_chunk_current(self, chunk_id: str) -> Chunk | None:
        result = self._collection.get(ids=[chunk_id], include=["documents", "metadatas"])
        if not result["ids"]:
            return None
        return _chunk_from_record(result["ids"][0], result["documents"][0], result["metadatas"][0])

    def count(self) -> int:
        return self._retry_stale_read(lambda: int(self._collection.count()))

    def clear(self) -> None:
        """Drop and recreate the collection. Used by `cli ingest` for a clean rebuild."""
        with _collection_write_lock(self.index_dir, self.collection_name):
            self._client.delete_collection(name=self.collection_name)
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            self._read_binding()


def build_store(settings) -> ChromaStore:
    return ChromaStore(
        settings.index_dir, settings.collection_name, strategy=settings.chunk_strategy
    )

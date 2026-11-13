"""Thin orchestration layer.

WHY THIS IS THIN: it only wires the five modules together in the documented
order. It contains no chunking, embedding, storage, or prompt logic. Keeping it
boring means five people can change their own modules without merge conflicts.

    docs -> chunks -> vectors -> store -> retrieve -> answer
     M1       M2        M3        M4        M4         M5
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ragkit.chunking import ChunkConfig, build_chunker
from ragkit.config import Settings
from ragkit.contracts import (
    Answer,
    Chunk,
    Chunker,
    Embedder,
    LLMClient,
    RetrievedChunk,
    VectorStore,
)
from ragkit.embeddings import build_embedder
from ragkit.generation import AnswerGenerator, build_llm
from ragkit.loaders import load_documents
from ragkit.store import build_store


@dataclass(frozen=True)
class IngestStats:
    documents: int
    chunks: int
    strategy: str
    embedding_provider: str
    collection: str


class RAGPipeline:
    def __init__(
        self,
        settings: Settings,
        chunker: Chunker,
        embedder: Embedder,
        store: VectorStore,
        generator: AnswerGenerator,
        llm: LLMClient | None = None,
    ) -> None:
        self.settings = settings
        self.chunker = chunker
        self.embedder = embedder
        self.store = store
        self.generator = generator
        self.llm = llm

    def ingest(self, manifest: str | None = None, clear: bool = True) -> IngestStats:
        documents = load_documents(manifest or self.settings.manifest)
        chunks: list[Chunk] = []
        for document in documents:
            chunks.extend(self.chunker.split(document))
        vectors = self.embedder.embed([chunk.text for chunk in chunks])
        if len(vectors) != len(chunks):
            raise RuntimeError("embedder returned a different number of vectors than chunks")
        if clear and hasattr(self.store, "clear"):
            self.store.clear()
        self.store.upsert(chunks, vectors)
        return IngestStats(
            documents=len(documents),
            chunks=len(chunks),
            strategy=self.chunker.name,
            embedding_provider=self.settings.embedding_provider,
            collection=self.settings.collection_name,
        )

    def retrieve(self, question: str, k: int | None = None) -> list[RetrievedChunk]:
        top_k = k or self.settings.top_k
        query_vector = self.embedder.embed([question])[0]
        hits = self.store.search(query_vector, top_k)
        # Reserved for the later experiment; 0.0 in v1 means "no threshold".
        return [hit for hit in hits if hit.score >= self.settings.min_score]

    def ask(self, question: str) -> tuple[Answer, Sequence[RetrievedChunk]]:
        hits = self.retrieve(question)
        answer = self.generator.generate(question, hits, llm=self.llm)
        return answer, hits


def build_pipeline(
    settings: Settings,
    *,
    chunker: Chunker | None = None,
    embedder: Embedder | None = None,
    store: VectorStore | None = None,
    llm: LLMClient | None = None,
) -> RAGPipeline:
    """Production wiring. Keyword overrides are what tests use to inject doubles."""
    config = ChunkConfig(size=settings.chunk_size, overlap=settings.chunk_overlap)
    return RAGPipeline(
        settings=settings,
        chunker=chunker or build_chunker(settings.chunk_strategy, config),
        embedder=embedder or build_embedder(settings),
        store=store or build_store(settings),
        # build_llm() is called lazily: `ingest`/`retrieve` must work with no key.
        llm=llm,
        generator=AnswerGenerator(llm=llm),
    )


def build_llm_pipeline(settings: Settings) -> RAGPipeline:
    """Wiring for `cli ask`: everything real, including the LLM client."""
    client = build_llm(settings)
    return RAGPipeline(
        settings=settings,
        chunker=build_chunker(
            settings.chunk_strategy,
            ChunkConfig(size=settings.chunk_size, overlap=settings.chunk_overlap),
        ),
        embedder=build_embedder(settings),
        store=build_store(settings),
        generator=AnswerGenerator(llm=client),
        llm=client,
    )

"""Synthetic fixture pipeline for explicitly requested MOCK batch exports."""
from ragkit.chunking import ChunkConfig, FixedSizeChunker
from ragkit.config import ROOT
from ragkit.generation import AnswerGenerator
from ragkit.loaders import load_documents
from ragkit.pipeline import RAGPipeline
from tests.fakes import FAKE_MANIFEST, FakeEmbedder, InMemoryStore, ScriptedLLM, settings_stub


def build_mock_pipeline():
    def respond(system, user):
        if 'MENU_ON_MARS' in user:
            return 'NO_ANSWER'
        return 'Alpha listens on port 8080 [mock_alpha#0000]'

    llm = ScriptedLLM(respond)
    pipeline = RAGPipeline(settings=settings_stub(top_k=10),
                           chunker=FixedSizeChunker(ChunkConfig(size=10000, overlap=0)),
                           embedder=FakeEmbedder(), store=InMemoryStore(),
                           generator=AnswerGenerator(llm), llm=llm)
    chunks = [chunk for doc in load_documents(ROOT / FAKE_MANIFEST)
              for chunk in pipeline.chunker.split(doc)]
    pipeline.store.upsert(chunks, pipeline.embedder.embed([chunk.text for chunk in chunks]))
    return pipeline

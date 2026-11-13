"""MOCK end-to-end tests.

The full five-module flow runs here with synthetic fixtures and scripted
doubles. This proves the wiring and contracts, NOT retrieval quality or answer
correctness. Never quote these results in the project report.

Regression note (v1.1): a refusal must NOT be able to pass a "normal answer"
test. Every normal-answer test asserts `not answer.abstained` AND checks the
answer content and which document was actually cited.
"""

from __future__ import annotations

import re

from ragkit.chunking import ChunkConfig, FixedSizeChunker
from ragkit.config import ROOT
from ragkit.contracts import ABSTAIN_MESSAGE, CITATION_PATTERN
from ragkit.generation import (
    AnswerGenerator,
    citation_ids_valid,
    citation_quotes_verbatim,
    verify_citation_structure,
)
from ragkit.pipeline import RAGPipeline
from tests.fakes import (
    FAKE_MANIFEST,
    FakeEmbedder,
    InMemoryStore,
    ScriptedLLM,
    settings_stub,
)

# FixedSizeChunker(size=140, overlap=20) over the two MOCK fixtures is
# deterministic (measured: 6). If this changes, the chunker changed and the
# test must be reviewed rather than silently loosened.
EXPECTED_MOCK_CHUNKS = 6


def _default_handler(_system: str, user: str) -> str:
    context = user.split("QUESTION:")[0]
    ids = re.findall(CITATION_PATTERN, context)
    if "MENU_ON_MARS" in user:
        return "NO_ANSWER"
    return f"The alpha service uses port 8080 [{ids[0]}]"


def _mock_pipeline(handler=_default_handler):
    llm = ScriptedLLM(handler)
    pipeline = RAGPipeline(
        settings=settings_stub(top_k=2),
        chunker=FixedSizeChunker(ChunkConfig(size=140, overlap=20)),
        embedder=FakeEmbedder(),
        store=InMemoryStore(),
        generator=AnswerGenerator(llm=llm),
        llm=llm,
    )
    pipeline.ingest(manifest=str(ROOT / FAKE_MANIFEST))
    return pipeline


def test_mock_end_to_end_returns_an_answer_with_a_verifiable_citation():
    pipeline = _mock_pipeline()
    answer, hits = pipeline.ask("What port does the alpha service use?")
    assert not answer.abstained, "a refusal must NOT pass a normal-answer test"
    assert "8080" in answer.answer_text
    assert answer.citation_ids, "a real answer must cite something"
    assert all(c.doc_id == "mock_alpha" for c in answer.citations)
    assert all(c.quote.strip() for c in answer.citations)
    assert citation_ids_valid(answer, hits)
    assert citation_quotes_verbatim(answer, hits)
    assert verify_citation_structure(answer, hits)
    by_id = {hit.chunk.chunk_id: hit.chunk for hit in hits}
    assert all(c.quote in by_id[c.chunk_id].text for c in answer.citations)


def test_normal_answer_and_refusal_are_clearly_distinguishable():
    normal, _ = _mock_pipeline().ask("What port does the alpha service use?")
    refused, _ = _mock_pipeline(lambda _s, _u: "NO_ANSWER").ask(
        "What port does the alpha service use?"
    )
    assert not normal.abstained and refused.abstained
    assert normal.answer_text != refused.answer_text
    assert "8080" in normal.answer_text and "8080" not in refused.answer_text
    assert normal.citations and not refused.citations


def test_mock_end_to_end_refuses_an_unanswerable_question():
    pipeline = _mock_pipeline()
    answer, hits = pipeline.ask("What is the MENU_ON_MARS today?")
    assert answer.abstained
    assert answer.answer_text == ABSTAIN_MESSAGE
    assert answer.raw == "NO_ANSWER", "refusal must come from the NO_ANSWER gate"
    assert answer.citations == ()
    assert verify_citation_structure(answer, hits), "a clean refusal is well-formed"


def test_mock_end_to_end_rejects_a_fabricated_citation():
    pipeline = _mock_pipeline(lambda _s, _u: "Invented claim [ghost_doc#9999]")
    answer, hits = pipeline.ask("Anything")
    assert answer.abstained
    assert answer.citations == ()
    assert "ghost_doc#9999" in answer.raw, "must be rejected by the id gate"
    assert verify_citation_structure(answer, hits)


def test_mock_retrieve_returns_the_relevant_document_not_just_any_chunk():
    pipeline = _mock_pipeline()
    hits = pipeline.retrieve("alpha service port", k=1)
    assert len(hits) == 1
    assert hits[0].rank == 1
    assert hits[0].chunk.doc_id == "mock_alpha"
    assert "alpha" in hits[0].chunk.text.lower()


def test_mock_ingest_reports_exact_deterministic_counts():
    pipeline = _mock_pipeline()
    assert pipeline.store.count() == EXPECTED_MOCK_CHUNKS
    stats = pipeline.ingest(manifest=str(ROOT / FAKE_MANIFEST))
    assert stats.documents == 2
    assert stats.chunks == EXPECTED_MOCK_CHUNKS
    assert stats.chunks == pipeline.store.count()
    assert stats.strategy == "fixed"

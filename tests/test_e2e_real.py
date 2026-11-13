"""REAL end-to-end tests - SKIPPED BY DEFAULT, never run in CI.

Enable explicitly once the local ONNX model is cached and (for the LLM test)
OPENAI_API_KEY is available:

    RUN_REAL_E2E=1 python -m pytest -m real -q

These are the only tests allowed to produce numbers for the report's
"experiments and discussions" section. They still do NOT constitute the formal
>=20 QA evaluation or the chunking comparison - those are future PRs.
"""

from __future__ import annotations

import os
from dataclasses import replace

import pytest

pytestmark = [
    pytest.mark.real,
    pytest.mark.skipif(
        os.environ.get("RUN_REAL_E2E") != "1",
        reason="set RUN_REAL_E2E=1 to run real end-to-end checks",
    ),
]


def test_real_corpus_ingest_and_retrieve(tmp_path):
    """REAL documents + REAL local ONNX embeddings + REAL Chroma, no API key."""
    from ragkit.config import load_settings
    from ragkit.pipeline import build_pipeline

    settings = replace(load_settings(), index_dir=tmp_path / "index")
    pipeline = build_pipeline(settings)
    stats = pipeline.ingest()
    assert stats.documents >= 3
    assert stats.chunks > stats.documents
    assert pipeline.store.count() == stats.chunks

    hits = pipeline.retrieve("What is retrieval-augmented generation?")
    assert hits
    assert all(hit.chunk.source_uri.startswith("https://") for hit in hits)
    assert all(hit.score >= 0.0 for hit in hits)
    restored = pipeline.store.get_chunk(hits[0].chunk.chunk_id)
    assert restored is not None
    assert restored.text == hits[0].chunk.text, "citation must be re-openable"


def test_real_llm_answer_cites_retrieved_chunks(tmp_path):
    """Everything real, including a paid LLM call. Requires OPENAI_API_KEY."""
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set; real LLM generation not executed")

    from ragkit.config import load_settings
    from ragkit.generation import verify_citations
    from ragkit.pipeline import build_llm_pipeline

    settings = replace(load_settings(), index_dir=tmp_path / "index")
    pipeline = build_llm_pipeline(settings)
    pipeline.ingest()
    answer, hits = pipeline.ask("When was retrieval-augmented generation first proposed?")
    assert answer.answer_text
    assert verify_citations(answer, hits)
    assert answer.model == settings.llm_model

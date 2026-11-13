"""M2 tests. The verbatim-slice invariant is the foundation of verifiable citations."""

from __future__ import annotations

import pytest

from ragkit.chunking import (
    ChunkConfig,
    FixedSizeChunker,
    ParagraphChunker,
    build_chunker,
)
from ragkit.config import ROOT
from ragkit.contracts import Document
from ragkit.loaders import load_documents


@pytest.fixture
def real_doc() -> Document:
    return load_documents(ROOT / "data" / "raw" / "manifest.json")[0]


@pytest.mark.parametrize("chunker_class", [FixedSizeChunker, ParagraphChunker])
def test_every_chunk_is_a_verbatim_slice_of_the_source(real_doc, chunker_class):
    chunks = chunker_class(ChunkConfig(size=400, overlap=50)).split(real_doc)
    assert chunks
    for chunk in chunks:
        assert real_doc.text[chunk.char_start : chunk.char_end] == chunk.text
        assert chunk.text.strip()
        assert chunk.title == real_doc.title
        assert chunk.source_uri == real_doc.source_uri


@pytest.mark.parametrize("chunker_class", [FixedSizeChunker, ParagraphChunker])
def test_chunk_ids_are_unique_stable_and_ordered(real_doc, chunker_class):
    chunker = chunker_class(ChunkConfig(size=400, overlap=50))
    first = chunker.split(real_doc)
    second = chunker.split(real_doc)
    ids = [chunk.chunk_id for chunk in first]
    assert ids == [chunk.chunk_id for chunk in second], "chunking must be deterministic"
    assert len(ids) == len(set(ids))
    assert [chunk.index for chunk in first] == list(range(len(first)))
    assert all(chunk.chunk_id.startswith(f"{real_doc.doc_id}#") for chunk in first)


def test_overlap_yields_more_chunks_than_no_overlap(real_doc):
    no_overlap = FixedSizeChunker(ChunkConfig(size=400, overlap=0)).split(real_doc)
    with_overlap = FixedSizeChunker(ChunkConfig(size=400, overlap=120)).split(real_doc)
    assert len(with_overlap) > len(no_overlap)


def test_two_strategies_are_actually_different(real_doc):
    fixed = FixedSizeChunker(ChunkConfig(size=400, overlap=50)).split(real_doc)
    paragraph = ParagraphChunker(ChunkConfig(size=400, overlap=50)).split(real_doc)
    assert [c.char_start for c in fixed] != [c.char_start for c in paragraph]
    assert {c.strategy for c in fixed} == {"fixed"}
    assert {c.strategy for c in paragraph} == {"paragraph"}


def test_oversized_paragraph_is_still_split():
    doc = Document(doc_id="long", title="Long", text="word " * 500)
    chunks = ParagraphChunker(ChunkConfig(size=200, overlap=0)).split(doc)
    assert len(chunks) > 1
    assert all(len(chunk.text) <= 200 for chunk in chunks)
    assert all(doc.text[c.char_start : c.char_end] == c.text for c in chunks)


@pytest.mark.parametrize("chunker_class", [FixedSizeChunker, ParagraphChunker])
def test_empty_document_produces_no_chunks(chunker_class):
    doc = Document(doc_id="empty", title="Empty", text="  \n ")
    assert chunker_class().split(doc) == []


@pytest.fixture
def paragraphs_doc() -> Document:
    body = "The alpha service listens on port 8080. " + ("word " * 60)
    text = "\n\n".join(f"P{i}. {body}" for i in range(8))
    return Document(doc_id="paras", title="Paragraphs", text=text)


@pytest.mark.parametrize("chunker_class", [FixedSizeChunker, ParagraphChunker])
def test_overlap_is_really_applied_and_metadata_is_truthful(
    paragraphs_doc, chunker_class
):
    """Regression: ParagraphChunker used to ignore overlap but claim it in meta."""
    config = ChunkConfig(size=400, overlap=80)
    chunks = chunker_class(config).split(paragraphs_doc)
    assert len(chunks) >= 3
    for previous, current in zip(chunks, chunks[1:], strict=False):
        actual = previous.char_end - current.char_start
        assert actual == config.overlap, f"{chunker_class.name}: wrong real overlap"
        assert current.meta["chunk_overlap"] == config.overlap
        assert current.meta["chunk_overlap_actual"] == actual
        assert current.char_start > previous.char_start
        assert paragraphs_doc.text[current.char_start : current.char_end] == current.text


def test_paragraph_overlap_is_no_longer_a_no_op(paragraphs_doc):
    without = ParagraphChunker(ChunkConfig(size=400, overlap=0)).split(paragraphs_doc)
    with_overlap = ParagraphChunker(ChunkConfig(size=400, overlap=80)).split(paragraphs_doc)
    assert len(with_overlap) == len(without)
    assert [c.char_start for c in with_overlap] != [c.char_start for c in without]
    assert all(c.meta["chunk_overlap_actual"] == 0 for c in without[1:])
    assert all(c.meta["chunk_overlap_actual"] == 80 for c in with_overlap[1:])
    assert all(c.char_start >= 0 and c.char_end <= len(paragraphs_doc.text)
               for c in with_overlap)


def test_invalid_config_is_rejected():
    with pytest.raises(ValueError):
        ChunkConfig(size=0)
    with pytest.raises(ValueError):
        ChunkConfig(size=100, overlap=100)


def test_build_chunker_factory():
    assert isinstance(build_chunker("fixed"), FixedSizeChunker)
    assert isinstance(build_chunker("paragraph"), ParagraphChunker)
    with pytest.raises(ValueError, match="unknown chunking strategy"):
        build_chunker("magic")

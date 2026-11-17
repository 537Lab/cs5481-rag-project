"""M2 - Chunking.

INPUT   Document + ChunkConfig
OUTPUT  list[Chunk]
DEPENDS stdlib only (pure functions, no I/O, no network)
DOES NOT read files, compute embeddings, or write to any database.

Two MINIMAL baseline strategies are provided so the pipeline is runnable:

  fixed      character windows of `size`, preferring a natural break
  paragraph  blank-line separated segments greedily packed up to `size`,
             with oversized segments falling back to plain windows

Overlap semantics are SHARED by both strategies: consecutive chunks repeat
`overlap` characters of the source text. Chunk.meta records BOTH the configured
overlap and the ACTUAL overlap measured from the emitted ranges, so metadata can
never claim an overlap that did not happen.

The comparison of these two strategies lives in `eval/chunking_experiment.py`.
That driver calls `eval.metrics.retrieval_hit_rate` and does not score the
strategies here. This module stays a pure chunker.

Invariant guaranteed by BOTH strategies:
    document.text[chunk.char_start:chunk.char_end] == chunk.text
This is what lets a citation be traced back to exact source text. It proves
provenance, NOT that the answer built on top of it is factually correct.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ragkit.contracts import Chunk, Document


@dataclass(frozen=True)
class ChunkConfig:
    size: int = 600
    overlap: int = 80

    def __post_init__(self) -> None:
        if self.size <= 0:
            raise ValueError("chunk size must be positive")
        if not 0 <= self.overlap < self.size:
            raise ValueError("chunk overlap must satisfy 0 <= overlap < size")


def _fixed_ranges(text: str, size: int, overlap: int) -> list[tuple[int, int]]:
    """Classic sliding windows: consecutive chunks share `overlap` characters."""
    ranges: list[tuple[int, int]] = []
    n = len(text)
    start = 0
    while start < n:
        end = min(start + size, n)
        if end < n:
            window = text[start:end]
            cut = max(window.rfind("\n"), window.rfind(" "))
            if cut > size // 2:
                end = start + cut + 1
        ranges.append((start, end))
        if end >= n:
            break
        # Always advance by at least one character: no infinite loop possible.
        start = max(end - overlap, start + 1)
    return ranges


def _apply_overlap(ranges: list[tuple[int, int]], overlap: int) -> list[tuple[int, int]]:
    """Extend every chunk except the first backwards by `overlap` characters.

    `fixed` achieves the same effect with a sliding window; `paragraph` needs
    this explicit step because its boundaries come from paragraph packing.
    Both strategies therefore mean the same thing by `overlap`: consecutive
    chunks share that many characters of the ORIGINAL text.
    """
    if overlap <= 0 or len(ranges) < 2:
        return ranges
    result = [ranges[0]]
    for i in range(1, len(ranges)):
        start, end = ranges[i]
        prev_start, prev_end = ranges[i - 1]
        # Base the overlap on the PREVIOUS chunk's end, not on this segment's
        # start: blank lines between paragraphs would otherwise make the real
        # overlap smaller than the configured value.
        new_start = min(start, max(0, prev_start + 1, prev_end - overlap))
        result.append((new_start, end))
    return result


def _ranges_to_chunks(
    doc: Document, ranges: list[tuple[int, int]], strategy: str, config: ChunkConfig
) -> list[Chunk]:
    chunks: list[Chunk] = []
    previous_end: int | None = None
    for start, end in ranges:
        piece = doc.text[start:end]
        if not piece.strip():
            continue
        actual_overlap = max(0, previous_end - start) if previous_end is not None else 0
        index = len(chunks)
        chunks.append(
            Chunk(
                chunk_id=f"{doc.doc_id}#{index:04d}",
                doc_id=doc.doc_id,
                text=piece,
                char_start=start,
                char_end=end,
                strategy=strategy,
                index=index,
                title=doc.title,
                source_uri=doc.source_uri,
                license=doc.license,
                meta={
                    "chunk_size": config.size,
                    "chunk_overlap": config.overlap,
                    "chunk_overlap_actual": actual_overlap,
                },
            )
        )
        previous_end = end
    return chunks


def _paragraph_segments(text: str) -> list[tuple[int, int]]:
    segments: list[tuple[int, int]] = []
    pos = 0
    for match in re.finditer(r"\n\s*\n", text):
        if text[pos : match.start()].strip():
            segments.append((pos, match.start()))
        pos = match.end()
    if text[pos:].strip():
        segments.append((pos, len(text)))
    return segments


def _paragraph_ranges(text: str, size: int, overlap: int) -> list[tuple[int, int]]:
    base: list[tuple[int, int]] = []
    current: tuple[int, int] | None = None

    def flush() -> None:
        nonlocal current
        if current is None:
            return
        start, end = current
        if end - start > size:
            # A single over-long paragraph is cut into plain windows first;
            # `_apply_overlap` below then adds overlap between those windows.
            cursor = start
            while cursor < end:
                stop = min(cursor + size, end)
                base.append((cursor, stop))
                cursor = stop
        else:
            base.append((start, end))
        current = None

    for seg_start, seg_end in _paragraph_segments(text):
        if current is None:
            current = (seg_start, seg_end)
        elif seg_end - current[0] <= size:
            current = (current[0], seg_end)
        else:
            flush()
            current = (seg_start, seg_end)
    flush()
    return _apply_overlap(base, overlap)


class FixedSizeChunker:
    name = "fixed"

    def __init__(self, config: ChunkConfig | None = None) -> None:
        self.config = config or ChunkConfig()

    def split(self, doc: Document) -> list[Chunk]:
        if not doc.text.strip():
            return []
        ranges = _fixed_ranges(doc.text, self.config.size, self.config.overlap)
        return _ranges_to_chunks(doc, ranges, self.name, self.config)


class ParagraphChunker:
    name = "paragraph"

    def __init__(self, config: ChunkConfig | None = None) -> None:
        self.config = config or ChunkConfig()

    def split(self, doc: Document) -> list[Chunk]:
        if not doc.text.strip():
            return []
        ranges = _paragraph_ranges(doc.text, self.config.size, self.config.overlap)
        return _ranges_to_chunks(doc, ranges, self.name, self.config)


def build_chunker(strategy: str, config: ChunkConfig | None = None):
    """Factory used by the pipeline. Add new strategies here, one per PR."""
    chunkers = {"fixed": FixedSizeChunker, "paragraph": ParagraphChunker}
    if strategy not in chunkers:
        raise ValueError(f"unknown chunking strategy: {strategy!r}")
    return chunkers[strategy](config)

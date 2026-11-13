"""Command line entry point. Run from the repository root:

    python -m ragkit.cli offline-demo            # MOCK, zero setup
    python -m ragkit.cli ingest                  # REAL: real docs + local ONNX + Chroma
    python -m ragkit.cli retrieve "what is RAG?" # REAL: query the built index
    python -m ragkit.cli ask "what is RAG?"      # REAL: needs OPENAI_API_KEY

Every command prints a REAL / MOCK banner. Nothing is silently simulated.
"""

from __future__ import annotations

import argparse
import re
import sys

from ragkit.config import load_settings, require_api_key
from ragkit.contracts import CITATION_PATTERN
from ragkit.pipeline import build_llm_pipeline, build_pipeline

BANNER_REAL = "[REAL] real documents / real embeddings / real Chroma index"
BANNER_MOCK = (
    "[MOCK / OFFLINE DEMO] synthetic fixtures + scripted doubles. "
    "No network, no API key, no vector database, no real documents."
)


def cmd_ingest(args: argparse.Namespace) -> int:
    settings = load_settings(args.config)
    print(BANNER_REAL)
    print(f"    manifest : {settings.manifest}")
    print(f"    strategy : {settings.chunk_strategy} (size={settings.chunk_size}, "
          f"overlap={settings.chunk_overlap})")
    print(f"    embedding: {settings.embedding_provider} (dim={settings.embedding_dimension})")
    print("    first local run downloads the ~80 MB ONNX model into ~/.cache/chroma")
    pipeline = build_pipeline(settings)
    stats = pipeline.ingest(manifest=args.manifest)
    print(f"\nOK: {stats.documents} documents -> {stats.chunks} chunks "
          f"stored in collection '{stats.collection}'")
    print(f"    index directory: {settings.index_dir}")
    print("\nNext: python -m ragkit.cli retrieve \"your question\"")
    return 0


def cmd_retrieve(args: argparse.Namespace) -> int:
    settings = load_settings(args.config)
    pipeline = build_pipeline(settings)
    if pipeline.store.count() == 0:
        print("Index is empty. Run `python -m ragkit.cli ingest` first.", file=sys.stderr)
        return 2
    print(BANNER_REAL)
    print(f"    question: {args.question}\n")
    hits = pipeline.retrieve(args.question, k=args.top_k)
    if not hits:
        print("No chunks passed the similarity threshold.")
        return 0
    for hit in hits:
        chunk = hit.chunk
        print(f"#{hit.rank} score={hit.score:.4f} id={chunk.chunk_id}")
        print(f"   document : {chunk.title or chunk.doc_id}")
        print(f"   source   : {chunk.source_uri or '(none)'}")
        print(f"   license  : {chunk.license or '(none)'}")
        print(f"   chars    : {chunk.char_start}-{chunk.char_end}")
        print(f"   text     : {chunk.text[:200].strip()!r}")
        print()
    print("These chunk ids are exactly what `cli ask` may cite. "
          "Use them to verify any answer.")
    return 0


def cmd_ask(args: argparse.Namespace) -> int:
    settings = load_settings(args.config)
    try:
        require_api_key()
    except RuntimeError as exc:
        print(f"Cannot run a REAL LLM answer: {exc}", file=sys.stderr)
        return 2
    print(BANNER_REAL + " / real LLM generation")
    pipeline = build_llm_pipeline(settings)
    if pipeline.store.count() == 0:
        print("Index is empty. Run `python -m ragkit.cli ingest` first.", file=sys.stderr)
        return 2
    answer, hits = pipeline.ask(args.question)
    print(f"\nQUESTION: {answer.question}")
    print(f"MODEL   : {answer.model}")
    print(f"ABSTAINED: {answer.abstained}")
    print(f"ANSWER  : {answer.answer_text}\n")
    if answer.citations:
        from ragkit.generation import (
            STRUCTURAL_VALIDATION_NOTE,
            citation_ids_valid,
            citation_quotes_verbatim,
            verify_citation_structure,
        )

        print("CITATIONS (quote is verbatim source text):")
        for citation in answer.citations:
            print(f"  [{citation.chunk_id}] {citation.title}")
            print(f"    source: {citation.source_uri}")
            print(f"    quote : {citation.quote[:160].strip()!r}")
        print("\nCitation STRUCTURE (level 1 + 2 ONLY, not factual correctness):")
        print(f"  ids valid       : {citation_ids_valid(answer, hits)}")
        print(f"  quotes verbatim : {citation_quotes_verbatim(answer, hits)}")
        print(f"  structure valid : {verify_citation_structure(answer, hits)}")
        print(f"  NOTE: {STRUCTURAL_VALIDATION_NOTE}")
    else:
        print("CITATIONS: none (answer was refused)")
    return 0


def cmd_offline_demo(_args: argparse.Namespace) -> int:
    """MOCK walkthrough for a first-time user. Test doubles come from tests/."""
    # Local import on purpose: the production commands above never load doubles.
    from ragkit.chunking import ChunkConfig, FixedSizeChunker
    from ragkit.config import ROOT
    from ragkit.generation import AnswerGenerator, verify_citation_structure
    from ragkit.loaders import load_documents
    from ragkit.pipeline import RAGPipeline
    from tests.fakes import (
        FAKE_MANIFEST,
        FakeEmbedder,
        InMemoryStore,
        ScriptedLLM,
        settings_stub,
    )

    print("=" * 78)
    print(BANNER_MOCK)
    print("=" * 78)

    def scripted_answer(_system: str, user: str) -> str:
        context = user.split("QUESTION:")[0]
        ids = re.findall(CITATION_PATTERN, context)
        if "MENU_ON_MARS" in user:
            return "NO_ANSWER"
        if "FABRICATE" in user:
            return "Invented claim with a fake id [ghost_doc#9999]"
        return f"The fixture states that the alpha service uses port 8080 [{ids[0]}]"

    llm = ScriptedLLM(scripted_answer)
    pipeline = RAGPipeline(
        settings=settings_stub(top_k=2),
        chunker=FixedSizeChunker(ChunkConfig(size=120, overlap=20)),
        embedder=FakeEmbedder(),
        store=InMemoryStore(),
        generator=AnswerGenerator(llm=llm),
        llm=llm,
    )
    documents = load_documents(ROOT / FAKE_MANIFEST)
    stats_chunks = []
    for document in documents:
        stats_chunks.extend(pipeline.chunker.split(document))
    pipeline.store.upsert(
        stats_chunks, pipeline.embedder.embed([chunk.text for chunk in stats_chunks])
    )
    print(f"MOCK fixtures: {len(documents)} docs -> {len(stats_chunks)} chunks\n")

    cases = [
        ("What port does the alpha service use?", "normal answer with a citation"),
        ("FABRICATE a claim please", "fabricated citation must be rejected"),
        ("What is the MENU_ON_MARS today?", "unanswerable question must be refused"),
    ]
    for question, label in cases:
        answer, hits = pipeline.ask(question)
        print(f"--- {label} ---")
        print(f"Q: {question}")
        print(f"abstained={answer.abstained}  citations={list(answer.citation_ids)}")
        print(f"A: {answer.answer_text}")
        print(f"structure_verified={verify_citation_structure(answer, hits)} "
              f"(id + verbatim quote ONLY; NOT factual correctness)\n")
    print("This was a MOCK run. For REAL ingestion/retrieval see README.md.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m ragkit.cli",
        description="CS5481 Topic 5 minimal RAG baseline",
    )
    parser.add_argument("--config", default=None, help="path to an alternate config.toml")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("ingest", help="REAL: load, chunk, embed, persist to Chroma")
    ingest.add_argument("--manifest", default=None, help="alternate manifest.json path")
    ingest.set_defaults(func=cmd_ingest)

    retrieve = sub.add_parser("retrieve", help="REAL: semantic search over the built index")
    retrieve.add_argument("question")
    retrieve.add_argument("--top-k", type=int, default=None)
    retrieve.set_defaults(func=cmd_retrieve)

    ask = sub.add_parser("ask", help="REAL: retrieved-context LLM answer (needs API key)")
    ask.add_argument("question")
    ask.set_defaults(func=cmd_ask)

    demo = sub.add_parser("offline-demo", help="MOCK: zero-setup walkthrough")
    demo.set_defaults(func=cmd_offline_demo)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

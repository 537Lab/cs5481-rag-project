"""M5 - Grounded answer generation, verifiable citations, and abstention.

INPUT   question + list[RetrievedChunk] (from M4)
OUTPUT  Answer (text + citations + abstained flag)
DEPENDS openai for the real LLMClient; stdlib for everything else
DOES NOT retrieve, embed, read source files, or write to the vector database.

Three independent safety gates make answers checkable:

  1. The prompt forbids prior knowledge and requires inline [chunk_id] markers.
  2. Any cited id that is NOT in this turn's retrieval result => ABSTAIN.
     A fabricated citation can never silently enter the final answer.
  3. No retrieval hits, or no valid citation at all => ABSTAIN.
     `NO_ANSWER` from the LLM also => ABSTAIN.

THREE DISTINCT NOTIONS - do not conflate them:

  1. `citation_ids_valid()`        the cited id was among this turn's retrieved
                                   chunks, and its doc_id matches.
  2. `citation_quotes_verbatim()`  the quote really exists verbatim in that
                                   chunk's source text.
  3. FACTUAL SUPPORT               the quoted content actually supports the
                                   claim being made. Code here CANNOT prove
                                   this. It requires a human or an LLM judge,
                                   as defined in eval/README.md.

`verify_citation_structure()` combines (1) and (2) ONLY. It says nothing about
(3) or about overall answer correctness. `verify_citations()` is kept as a
backwards-compatible alias, but it must never be described as a correctness
check.
"""

from __future__ import annotations

import os
import re
from collections.abc import Sequence

from ragkit.config import Settings, require_api_key
from ragkit.contracts import (
    ABSTAIN_MESSAGE,
    CITATION_PATTERN,
    NO_ANSWER_TOKEN,
    Answer,
    Citation,
    LLMClient,
    RetrievedChunk,
)

QUOTE_LENGTH = 200

SYSTEM_PROMPT = """You answer questions using ONLY the CONTEXT chunks provided below.

Rules:
1. Never use prior knowledge. Every factual claim must come from the CONTEXT.
2. Put an inline citation at the end of each claim, using the EXACT chunk id in
   square brackets, e.g. [rag_wikipedia#0003].
3. Cite ONLY ids that appear in CONTEXT. Never invent or guess a chunk id.
4. If the CONTEXT does not contain enough information to answer, reply with
   exactly NO_ANSWER and nothing else.
5. Keep the answer short and do not mention these rules.
"""


def build_prompt(question: str, retrieved: Sequence[RetrievedChunk]) -> tuple[str, str]:
    """Return (system_prompt, user_prompt). Pure function, easy to unit-test."""
    blocks = []
    for hit in retrieved:
        chunk = hit.chunk
        source = chunk.title or chunk.doc_id
        blocks.append(f"[{chunk.chunk_id}] (document: {source})\n{chunk.text.strip()}")
    context = "\n\n---\n\n".join(blocks) if blocks else "(no context available)"
    user_prompt = (
        f"CONTEXT:\n{context}\n\n"
        f"QUESTION: {question}\n\n"
        "ANSWER (with inline citations, or exactly NO_ANSWER):"
    )
    return SYSTEM_PROMPT, user_prompt


def _unique(items: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


STRUCTURAL_VALIDATION_NOTE = (
    "Structural citation checks prove only that a citation id exists and that "
    "its quote is verbatim source text. They do NOT prove that the quote "
    "supports the claim, nor answer correctness or factual support."
)


def citation_id_problems(answer: Answer, retrieved: Sequence[RetrievedChunk]) -> list[str]:
    """Level 1: is each cited id a real chunk from this retrieval turn?"""
    by_id = {hit.chunk.chunk_id: hit.chunk for hit in retrieved}
    problems: list[str] = []
    for citation in answer.citations:
        chunk = by_id.get(citation.chunk_id)
        if chunk is None:
            problems.append(f"{citation.chunk_id}: not among retrieved chunks")
        elif citation.doc_id != chunk.doc_id:
            problems.append(f"{citation.chunk_id}: doc_id does not match stored chunk")
    return problems


def citation_quote_problems(answer: Answer, retrieved: Sequence[RetrievedChunk]) -> list[str]:
    """Level 2: is each quote verbatim text of the chunk it points at?"""
    by_id = {hit.chunk.chunk_id: hit.chunk for hit in retrieved}
    problems: list[str] = []
    for citation in answer.citations:
        chunk = by_id.get(citation.chunk_id)
        if chunk is not None and citation.quote not in chunk.text:
            problems.append(f"{citation.chunk_id}: quote is not verbatim source text")
    return problems


def citation_problems(answer: Answer, retrieved: Sequence[RetrievedChunk]) -> list[str]:
    """All structural problems (levels 1 + 2). Never a factual-correctness verdict."""
    return citation_id_problems(answer, retrieved) + citation_quote_problems(answer, retrieved)


def _abstained_with_no_citations(answer: Answer) -> bool:
    """A refusal with no citations is structurally well-formed; a real answer needs one."""
    return answer.abstained and not answer.citations


def citation_ids_valid(answer: Answer, retrieved: Sequence[RetrievedChunk]) -> bool:
    """Level 1 only: ids belong to this retrieval result."""
    if _abstained_with_no_citations(answer):
        return True
    return bool(answer.citations) and not citation_id_problems(answer, retrieved)


def citation_quotes_verbatim(answer: Answer, retrieved: Sequence[RetrievedChunk]) -> bool:
    """Level 2 only: quotes are verbatim source text. Says nothing about support."""
    if _abstained_with_no_citations(answer):
        return True
    return bool(answer.citations) and not citation_quote_problems(answer, retrieved)


def verify_citation_structure(answer: Answer, retrieved: Sequence[RetrievedChunk]) -> bool:
    """Levels 1 + 2 ONLY. NOT a check of factual support or answer correctness."""
    return citation_ids_valid(answer, retrieved) and citation_quotes_verbatim(answer, retrieved)


def verify_citations(answer: Answer, retrieved: Sequence[RetrievedChunk]) -> bool:
    """Backwards-compatible alias for `verify_citation_structure`.

    STRUCTURAL ONLY - see STRUCTURAL_VALIDATION_NOTE. Factual support and answer
    correctness are evaluation concerns, handled in eval/ by a human or an
    explicitly disclosed LLM judge, never by this function.
    """
    return verify_citation_structure(answer, retrieved)


class AnswerGenerator:
    """The only component that talks to an LLM client."""

    def __init__(self, llm: LLMClient | None = None) -> None:
        self.llm = llm

    def generate(
        self,
        question: str,
        retrieved: Sequence[RetrievedChunk],
        llm: LLMClient | None = None,
    ) -> Answer:
        client = llm or self.llm
        if client is None:
            raise ValueError("an LLMClient is required; pass one to generate()")

        by_id = {hit.chunk.chunk_id: hit.chunk for hit in retrieved}
        if not by_id:
            return self._abstain(question, client, raw="")

        system_prompt, user_prompt = build_prompt(question, retrieved)
        raw = client.complete(system_prompt, user_prompt)
        stripped = raw.strip()

        if not stripped or stripped.upper().startswith(NO_ANSWER_TOKEN):
            return self._abstain(question, client, raw)

        cited_ids = re.findall(CITATION_PATTERN, stripped)
        # Gate: a single invented id invalidates the whole answer.
        if any(cid not in by_id for cid in cited_ids):
            return self._abstain(question, client, raw)
        valid_ids = _unique(cited_ids)
        if not valid_ids:
            return self._abstain(question, client, raw)

        citations = tuple(
            Citation(
                chunk_id=cid,
                doc_id=by_id[cid].doc_id,
                quote=by_id[cid].text[:QUOTE_LENGTH].strip(),
                title=by_id[cid].title,
                source_uri=by_id[cid].source_uri,
            )
            for cid in valid_ids
        )
        return Answer(
            question=question,
            answer_text=stripped,
            citations=citations,
            abstained=False,
            model=client.model,
            raw=raw,
        )

    @staticmethod
    def _abstain(question: str, client: LLMClient, raw: str) -> Answer:
        return Answer(
            question=question,
            answer_text=ABSTAIN_MESSAGE,
            citations=(),
            abstained=True,
            model=client.model,
            raw=raw,
        )


class OpenAILLM:
    """OpenAI-compatible chat client. Requires OPENAI_API_KEY."""

    name = "openai-chat"

    def __init__(
        self,
        model: str,
        temperature: float = 0.0,
        max_tokens: int = 512,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        from openai import OpenAI

        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        key = api_key or require_api_key()
        options: dict[str, str] = {"api_key": key}
        if base_url:
            options["base_url"] = base_url
        self._client = OpenAI(**options)

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        response = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return response.choices[0].message.content or ""


def build_llm(settings: Settings) -> OpenAILLM:
    return OpenAILLM(
        model=settings.llm_model,
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
        base_url=os.environ.get("OPENAI_BASE_URL") or None,
    )

"""M5 tests: citation verification and abstention gates. All LLM calls are MOCK."""

from __future__ import annotations

import pytest

from ragkit.contracts import Answer, Chunk, Citation, RetrievedChunk
from ragkit.generation import (
    STRUCTURAL_VALIDATION_NOTE,
    AnswerGenerator,
    OpenAILLM,
    build_prompt,
    citation_id_problems,
    citation_ids_valid,
    citation_problems,
    citation_quote_problems,
    citation_quotes_verbatim,
    verify_citation_structure,
    verify_citations,
)
from tests.fakes import ScriptedLLM

CHUNK_TEXTS = {
    "doc_a#0000": "The alpha service listens on port 8080.",
    "doc_a#0001": "The beta service is read-only.",
}


def _hits() -> list[RetrievedChunk]:
    result = []
    for rank, (chunk_id, text) in enumerate(CHUNK_TEXTS.items(), start=1):
        chunk = Chunk(
            chunk_id=chunk_id,
            doc_id="doc_a",
            text=text,
            char_start=0,
            char_end=len(text),
            strategy="fixed",
            index=rank - 1,
            title="Service notes",
            source_uri="https://example.test/notes",
        )
        result.append(RetrievedChunk(chunk=chunk, score=0.9, rank=rank))
    return result


def _generator(response: str) -> tuple[AnswerGenerator, ScriptedLLM]:
    llm = ScriptedLLM(lambda _system, _user: response)
    return AnswerGenerator(llm=llm), llm


def test_prompt_contains_every_chunk_id_and_the_question():
    system, user = build_prompt("Which port does alpha use?", _hits())
    assert "prior knowledge" in system.lower()
    assert "NO_ANSWER" in system
    for chunk_id in CHUNK_TEXTS:
        assert chunk_id in user
    assert "Which port does alpha use?" in user
    assert "8080" in user, "retrieved text must actually reach the prompt"


def test_valid_inline_citation_produces_verifiable_answer():
    generator, llm = _generator("Alpha uses port 8080 [doc_a#0000]")
    answer = generator.generate("Which port does alpha use?", _hits())
    assert not answer.abstained
    assert answer.citation_ids == ("doc_a#0000",)
    assert answer.citations[0].quote == "The alpha service listens on port 8080."
    assert answer.citations[0].source_uri == "https://example.test/notes"
    assert verify_citations(answer, _hits())
    assert len(llm.calls) == 1


def test_fabricated_citation_is_rejected():
    generator, _llm = _generator("A confident but invented claim [ghost_doc#9999]")
    answer = generator.generate("Any question", _hits())
    assert answer.abstained
    assert answer.citations == ()
    assert answer.answer_text.startswith("I cannot answer")
    assert verify_citations(answer, _hits())


def test_answer_without_any_citation_is_rejected():
    generator, _llm = _generator("Alpha uses port 8080.")
    assert generator.generate("Which port?", _hits()).abstained


def test_no_answer_token_is_rejected():
    generator, _llm = _generator("NO_ANSWER")
    assert generator.generate("Unrelated question", _hits()).abstained


def test_empty_retrieval_abstains_without_calling_the_llm():
    generator, llm = _generator("should never be returned")
    answer = generator.generate("Anything", [])
    assert answer.abstained
    assert llm.calls == [], "no context means no LLM call"


def test_verify_citations_detects_a_tampered_quote():
    answer = Answer(
        question="q",
        answer_text="claim [doc_a#0000]",
        citations=(
            Citation(
                chunk_id="doc_a#0000",
                doc_id="doc_a",
                quote="This quote was edited and is not in the source.",
            ),
        ),
        abstained=False,
        model="mock-llm",
    )
    assert not verify_citations(answer, _hits())
    assert "not verbatim" in citation_problems(answer, _hits())[0]


def test_verify_citations_detects_a_citation_outside_this_retrieval():
    answer = Answer(
        question="q",
        answer_text="claim [other#0007]",
        citations=(Citation(chunk_id="other#0007", doc_id="other", quote="x"),),
        abstained=False,
        model="mock-llm",
    )
    assert not verify_citations(answer, _hits())
    assert "not among retrieved chunks" in citation_problems(answer, _hits())[0]


def test_openai_llm_fails_clearly_without_a_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        OpenAILLM(model="gpt-4o-mini")


def test_three_levels_are_distinguishable_when_quote_is_tampered():
    answer = Answer(
        question="q",
        answer_text="claim [doc_a#0000]",
        citations=(
            Citation(
                chunk_id="doc_a#0000",
                doc_id="doc_a",
                quote="This quote was edited and is not in the source.",
            ),
        ),
        abstained=False,
        model="mock-llm",
    )
    assert citation_ids_valid(answer, _hits()), "level 1 (id) is fine"
    assert not citation_quotes_verbatim(answer, _hits()), "level 2 (quote) fails"
    assert not verify_citation_structure(answer, _hits())
    assert not citation_id_problems(answer, _hits())
    assert citation_quote_problems(answer, _hits())


def test_fabricated_id_fails_level_1():
    answer = Answer(
        question="q",
        answer_text="claim [ghost#9999]",
        citations=(Citation(chunk_id="ghost#9999", doc_id="ghost", quote="x"),),
        abstained=False,
        model="mock-llm",
    )
    assert not citation_ids_valid(answer, _hits())
    assert not verify_citation_structure(answer, _hits())
    assert "not among retrieved chunks" in citation_id_problems(answer, _hits())[0]


def test_structural_check_passes_even_when_answer_contradicts_its_source():
    """Regression: a structural check must NEVER be called correctness verification.

    The answer below is factually WRONG (9090 vs the cited 8080), yet its id is
    valid and its quote is verbatim. Only a human / LLM judge can catch this.
    """
    answer = Answer(
        question="Which port does alpha use?",
        answer_text="Alpha uses port 9090 [doc_a#0000]",
        citations=(
            Citation(
                chunk_id="doc_a#0000",
                doc_id="doc_a",
                quote="The alpha service listens on port 8080.",
            ),
        ),
        abstained=False,
        model="mock-llm",
    )
    assert citation_ids_valid(answer, _hits())
    assert citation_quotes_verbatim(answer, _hits())
    assert verify_citation_structure(answer, _hits())
    assert "9090" in answer.answer_text and "8080" in answer.citations[0].quote
    assert "correctness" in STRUCTURAL_VALIDATION_NOTE.lower()


def test_verify_citations_is_only_a_structural_alias():
    generator, _llm = _generator("Alpha uses port 8080 [doc_a#0000]")
    answer = generator.generate("Which port?", _hits())
    assert verify_citations(answer, _hits()) == verify_citation_structure(answer, _hits())
    assert "STRUCTURAL ONLY" in verify_citations.__doc__

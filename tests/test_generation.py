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


@pytest.mark.parametrize('corruption', ['refusal', 'config_ref', 'qa_hash'])
def test_handoff_rejects_corrupted_export(tmp_path, corruption):
    import argparse
    import json

    from demo.validate_export import validate_export
    from ragkit.cli import cmd_batch

    output = tmp_path / 'MOCK-handoff.jsonl'
    cmd_batch(argparse.Namespace(
        questions='demo/questions.csv', output=str(output),
        run_id='MOCK-handoff', config=None, mock=True,
    ))
    validate_export(output)
    if corruption == 'qa_hash':
        snapshot_path = output.with_suffix('.config.json')
        snapshot = json.loads(snapshot_path.read_text(encoding='utf-8'))
        snapshot['qa_sha256'] = '0' * 64
        snapshot_path.write_text(json.dumps(snapshot), encoding='utf-8')
        error = 'input hash mismatch'
    else:
        records = [json.loads(line) for line in output.read_text(encoding='utf-8').splitlines()]
        if corruption == 'refusal':
            records[1]['answer']['abstained'] = False
            error = 'Scripted refusal'
        else:
            records[0]['config_ref'] = 'missing.config.json'
            error = 'Broken configuration reference'
        output.write_text('\n'.join(json.dumps(row) for row in records) + '\n', encoding='utf-8')
    with pytest.raises(RuntimeError, match=error):
        validate_export(output)

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

@pytest.mark.parametrize('response', [None, {}, '', 'Uncited claim. Another claim [doc_a#0000]'])
def test_invalid_output_or_partial_coverage_refuses(response):
    generator, _ = _generator(response)
    assert generator.generate('q', _hits()).abstained


def test_multiple_claims_and_citations():
    generator, _ = _generator('Alpha uses 8080 [doc_a#0000]. Beta is read-only [doc_a#0001].')
    answer = generator.generate('q', _hits())
    assert not answer.abstained
    assert len(answer.citations) == 2


def test_batch_i4_export(tmp_path, monkeypatch):
    import argparse
    import json

    from eval.metrics import load_outputs
    from ragkit import cli

    generator, _ = _generator('Alpha uses 8080 [doc_a#0000]')

    class Pipeline:
        def ask(self, question):
            return generator.generate(question, _hits()), _hits()

    monkeypatch.setattr(cli, 'build_llm_pipeline', lambda settings: Pipeline())
    source = tmp_path / 'questions.csv'
    source.write_text('qid,question\nMOCK01,Which port?\n', encoding='utf-8')
    output = tmp_path / 'mock.jsonl'
    args = argparse.Namespace(questions=str(source), output=str(output),
                              run_id='MOCK-test', config=None)
    assert cli.cmd_batch(args) == 0
    row = json.loads(output.read_text(encoding='utf-8'))
    assert row['run_id'] == 'MOCK-test'
    assert row['retrieved_chunk_ids'] == list(CHUNK_TEXTS)
    assert 'MOCK01' in load_outputs(output)
    with pytest.raises(ValueError, match='already exists'):
        cli.cmd_batch(args)

@pytest.mark.parametrize('csv_text', ['qid,question\nx,\n',
                                     'qid,question\nx,q\nx,q2\n', 'qid,question\n'])
def test_batch_rejects_input_before_model_call(tmp_path, monkeypatch, csv_text):
    import argparse

    from ragkit import cli

    def forbidden(settings):
        pytest.fail('invalid input must be rejected before constructing a model')

    monkeypatch.setattr(cli, 'build_llm_pipeline', forbidden)
    source = tmp_path / 'bad.csv'
    source.write_text(csv_text, encoding='utf-8')
    args = argparse.Namespace(questions=str(source), output=str(tmp_path / 'out.jsonl'),
                              run_id='test', config=None)
    with pytest.raises(ValueError):
        cli.cmd_batch(args)


def test_provider_error_propagates():
    def fail(system, user):
        raise RuntimeError('provider unavailable')

    with pytest.raises(RuntimeError, match='provider unavailable'):
        AnswerGenerator(ScriptedLLM(fail)).generate('q', _hits())

@pytest.mark.parametrize(('raw', 'reason'), [
    ('NO_ANSWER', 'model_reported_insufficient_evidence'),
    ('Unsupported.', 'missing_citations'),
    ('Claim [ghost#9]', 'unknown_citation_id'),
    ('Uncited. Cited [doc_a#0000]', 'uncovered_claim'),
    ('', 'invalid_or_empty_output'),
    ('Claim [doc_a#0000]', None),
])
def test_refusal_diagnostics(raw, reason):
    from ragkit.generation import refusal_reason

    assert refusal_reason(raw, _hits()) == reason


def test_mock_batch_cli_end_to_end(tmp_path):
    import json
    import subprocess
    import sys

    output = tmp_path / 'MOCK.jsonl'
    result = subprocess.run([
        sys.executable, '-m', 'ragkit.cli', 'batch', '--mock',
        '--questions', 'demo/questions.csv', '--run-id', 'MOCK-e2e',
        '--output', str(output),
    ], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    rows = [json.loads(line) for line in output.read_text(encoding='utf-8').splitlines()]
    assert len(rows) == 2
    assert not rows[0]['answer']['abstained']
    assert rows[1]['answer']['abstained']
    assert all(row['answer']['model'].startswith('mock') for row in rows)


def test_failed_publish_cleans_temporary_file(tmp_path, monkeypatch):
    import argparse
    import os

    from ragkit import cli

    def fail(source, destination):
        raise OSError('simulated publish failure')

    monkeypatch.setattr(cli.os, 'rename' if os.name == 'nt' else 'link', fail)
    output = tmp_path / 'result.jsonl'
    args = argparse.Namespace(questions='demo/questions.csv', output=str(output),
                              run_id='MOCK-failure', config=None, mock=True)
    with pytest.raises(OSError, match='publish failure'):
        cli.cmd_batch(args)
    assert list(tmp_path.iterdir()) == []


def test_mock_export_configuration_snapshot(tmp_path):
    import argparse
    import hashlib
    import json
    from pathlib import Path

    from ragkit.cli import cmd_batch

    output = tmp_path / 'mock.jsonl'
    args = argparse.Namespace(questions='demo/questions.csv', output=str(output),
                              run_id='MOCK-config', config=None, mock=True)
    cmd_batch(args)
    row = json.loads(output.read_text(encoding='utf-8').splitlines()[0])
    config_path = Path(row['config_ref'])
    config = json.loads(config_path.read_text(encoding='utf-8'))
    assert config['mode'] == 'MOCK'
    assert config['llm']['model'] == row['answer']['model']
    assert config['embedding']['provider'] == 'MOCK'
    assert config['top_k'] == 10
    assert config['min_score'] == 0.0
    assert config['qa_sha256'] == hashlib.sha256(Path(args.questions).read_bytes()).hexdigest()
    assert config['corpus_ref'] == 'tests/fixtures/manifest.json'


def test_mock_snapshot_ignores_real_manifest_and_retrieval_config(tmp_path):
    import argparse
    import json

    from ragkit.cli import cmd_batch

    config = tmp_path / 'config.toml'
    config.write_text('''
[paths]
raw_dir = "missing/raw"
manifest = "missing/manifest.json"
index_dir = "missing/index"
[chunking]
strategy = "paragraph"
size = 321
overlap = 12
[embedding]
provider = "api"
local_model = "unused-local"
local_dimension = 1
api_model = "unused-api"
api_dimension = 2
[llm]
model = "unused-llm"
temperature = 0.9
max_tokens = 99
[retrieval]
top_k = 77
min_score = 0.85
''', encoding='utf-8')
    output = tmp_path / 'mock.jsonl'
    args = argparse.Namespace(questions='demo/questions.csv', output=str(output),
                              run_id='MOCK-independent', config=str(config), mock=True)

    cmd_batch(args)

    snapshot = json.loads(output.with_suffix('.config.json').read_text(encoding='utf-8'))
    assert snapshot['mode'] == 'MOCK'
    assert snapshot['strategy'] == 'fixed'
    assert snapshot['top_k'] == 10
    assert snapshot['min_score'] == 0.0
    assert snapshot['corpus_ref'] == 'tests/fixtures/manifest.json'

@pytest.mark.parametrize('response', [
    '[doc_a#0000]',
    '第一句没有引用。第二句有引用[doc_a#0000]。',
])
def test_citation_only_and_uncovered_chinese_sentence_refuse(response):
    generator, _ = _generator(response)
    assert generator.generate('q', _hits()).abstained


def test_chinese_claims_with_individual_citations_pass():
    generator, _ = _generator('第一句[doc_a#0000]。第二句[doc_a#0001]。')
    assert not generator.generate('q', _hits()).abstained


@pytest.mark.parametrize('content', [
    'qid,question,question\nx,q,q\n',
    'qid,question\nx,q,unexpected\n',
    'qid,prompt\nx,q\n',
])
def test_invalid_csv_shape_before_generation(tmp_path, content):
    import argparse

    from ragkit.cli import cmd_batch

    source = tmp_path / 'bad.csv'
    source.write_text(content, encoding='utf-8')
    args = argparse.Namespace(questions=str(source), output=str(tmp_path / 'out.jsonl'),
                              run_id='MOCK-bad', config=None, mock=True)
    with pytest.raises(ValueError, match='CSV'):
        cmd_batch(args)
    assert not (tmp_path / 'out.jsonl').exists()

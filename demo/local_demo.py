"""Two real local Ollama examples. Requires a prepared local embedding/index config."""
import argparse
import os
from contextlib import contextmanager

from ragkit.config import load_settings
from ragkit.generation import (
    citation_ids_valid,
    citation_quotes_verbatim,
    refusal_reason,
)
from ragkit.pipeline import build_llm_pipeline

QUESTIONS = (
    'What are the two top-level parts that make up a Kubernetes cluster?',
    'Which cloud provider offers the cheapest managed Kubernetes cluster?',
)


@contextmanager
def local_environment():
    values = {'OPENAI_BASE_URL': 'http://localhost:11434/v1',
              'OPENAI_API_KEY': 'ollama', 'LLM_MODEL': 'qwen3:4b-instruct',
              'NO_PROXY': 'localhost,127.0.0.1,::1'}
    previous = {key: os.environ.get(key) for key in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def run_demo(config: str) -> int:
    with local_environment():
        settings = load_settings(config)
        if settings.embedding_provider != 'local':
            raise ValueError('local demo requires local embeddings; API embeddings are refused')
        if not settings.index_dir.is_dir():
            raise ValueError('prepare the matching index with CLI ingest first')
        pipeline = build_llm_pipeline(settings)
        if pipeline.store.count() == 0:
            raise ValueError('matching index is empty; run CLI ingest first')
        print('[REAL / LOCAL OLLAMA] qwen3:4b-instruct; not a MOCK or formal evaluation')
        for question in QUESTIONS:
            answer, hits = pipeline.ask(question)
            print(f'\nQUESTION: {question}\nANSWER: {answer.answer_text}')
            print(f'abstained={answer.abstained}')
            if answer.abstained:
                print(f'generation_gate={refusal_reason(answer.raw, hits)}')
            by_id = {hit.chunk.chunk_id: hit.chunk for hit in hits}
            for citation in answer.citations:
                print(f'[{citation.chunk_id}] source={citation.source_uri}')
                print(f'EXPORTED QUOTE: {citation.quote}')
                print(f'COMPLETE RETRIEVED CHUNK: {by_id[citation.chunk_id].text}')
            print(f'ids_valid={citation_ids_valid(answer, hits)}')
            print(f'quotes_verbatim={citation_quotes_verbatim(answer, hits)}')
            print('semantic_support=not_graded; source membership is not answer correctness')
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    return run_demo(parser.parse_args().config)


if __name__ == '__main__':
    raise SystemExit(main())

"""Inspect existing I4 answers without model calls, gold data or metric aggregation."""
import argparse
import hashlib
import json
from collections.abc import Callable
from pathlib import Path

from eval.metrics import load_outputs
from ragkit.config import load_settings
from ragkit.contracts import Answer, Chunk, Citation, RetrievedChunk
from ragkit.generation import (
    claim_coverage_problems,
    refusal_reason,
    verify_citation_structure,
)


def inspect_record(row: dict, get_chunk: Callable[[str], Chunk | None]) -> dict:
    """Reconstruct source membership only; query scores are not evaluated."""
    ids = row['retrieved_chunk_ids']
    if not isinstance(ids, list) or any(not isinstance(cid, str) for cid in ids):
        raise ValueError('retrieved_chunk_ids must be a list of strings')
    chunks = [(cid, get_chunk(cid)) for cid in ids]
    missing = [cid for cid, chunk in chunks if chunk is None]
    result = {'qid': row['qid'], 'abstained': row['abstained'],
              'retrieved_chunk_ids': ids, 'missing_chunk_ids': missing,
              'diagnostic_status': 'incomplete_index' if missing else 'complete',
              'generation_gate': None, 'uncovered_units': [],
              'citation_structure_valid': None,
              'semantic_support': 'not_graded'}
    if missing:
        return result
    # Scores are placeholders for existing structural helpers, never reported.
    hits = [RetrievedChunk(chunk=chunk, score=0.0, rank=i)
            for i, (_cid, chunk) in enumerate(chunks, 1)]
    reason = refusal_reason(row['raw'], hits)
    result['generation_gate'] = reason
    if reason == 'uncovered_claim':
        result['uncovered_units'] = claim_coverage_problems(row['raw'])
    answer = Answer(question=row['question'], answer_text=row['answer_text'],
                    abstained=row['abstained'], model=row['model'], raw=row['raw'],
                    citations=tuple(Citation(**citation) for citation in row['citations']))
    result['citation_structure_valid'] = verify_citation_structure(answer, hits)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--outputs', type=Path, required=True)
    parser.add_argument('--config', required=True, help='configuration for the matching index')
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if args.report.exists():
        raise ValueError('report already exists; choose a new path')
    rows = load_outputs(args.outputs)
    settings = load_settings(args.config)
    if not settings.index_dir.is_dir():
        raise ValueError('matching index directory does not exist')
    from ragkit.store import build_store

    store = build_store(settings)
    report = {
        'scope': 'per-answer generator and citation diagnostics; not metrics or human grades',
        'source_sha256': hashlib.sha256(args.outputs.read_bytes()).hexdigest(),
        'index_directory': str(settings.index_dir),
        'collection': settings.collection_name,
        'records': [inspect_record(row, store.get_chunk) for row in rows.values()],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(f'Wrote {len(rows)} per-answer diagnostics to {args.report}; no model calls or grades.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

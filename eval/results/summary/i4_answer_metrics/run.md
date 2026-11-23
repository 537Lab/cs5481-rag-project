# i4_answer_metrics

- command: `python -m eval.metrics score --outputs .tmp/t5handoff/eval/results/raw/ollama-20261122/LOCAL-ollama-fixed-20261122.jsonl --formal --grades eval/review/grades_LOCAL-ollama-fixed-20261122.csv --executor 'adjudicated by usagi (T3); 14 refusals rule-scored by A+B agreement; AI-assisted evidence prep only' --summary-dir eval/results/summary/i4_answer_metrics`
- date: 2026-11-23T06:39:36+00:00
- executor: adjudicated by usagi (T3); 14 refusals rule-scored by A+B agreement; AI-assisted evidence prep only
- exit code: 0 (this file is written by the run that produced it)
- corpus: cs5481-k8s-v135-16docs-36fd3eedf33f@bddfe3601885 (frozen: True)
- QA set: eval/qa_set.csv@b01b97fbdf2a (formal Kubernetes QA set (interface I2), gold quotes verbatim in the frozen corpus snapshot)
- grades sheet: eval/review/grades_LOCAL-ollama-fixed-20261122.csv@754d6f280d35
- grades sheet reviewer_id: rule (both A and B agreed), usagi (adjudicator)
- grades sheet reviewed_at: 2026-11-22, 2026-11-23
- grades sheet ai_assisted: n/a (rule-scored), yes (evidence prep, grades by adjudicator)
- grades sheet judge_note_first: In cited_chunk_text, immediately after "Some Pods have init containers", the next sentence says init containers run and complete before app containers start.

Reproduce from the repository root with the command above; the index must
already exist (`python -m ragkit.cli ingest`).

| metric | hits | n | rate |
| --- | --- | --- | --- |
| `min_coverage` | - | - | 0.5 |
| `n_items` | - | - | 36 |
| `n_answerable` | - | - | 26 |
| `n_unanswerable` | - | - | 10 |
| `correct_abstention_rate` | 10 | 10 | 1.0 |
| `false_abstention_rate` | 14 | 26 | 0.5385 |
| `citation_structure_rate` | 12 | 12 | 1.0 |
| `answer_correctness` | 11 | 26 | 0.4231 |
| `n_graded` | - | - | 26 |
| `n_gradable` | - | - | 26 |
| `grading_coverage` | 26 | 26 | 1.0 |
| `grade_counts` | - | - | {'correct': 11, 'incorrect': 15, 'unsure': 0} |
| `hit@1` | 8 | 26 | 0.3077 |
| `hit@3` | 18 | 26 | 0.6923 |

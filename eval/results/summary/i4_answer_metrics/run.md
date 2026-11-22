# i4_answer_metrics

- command: `python -m eval.metrics score --outputs .tmp/t5handoff/eval/results/raw/ollama-20261122/LOCAL-ollama-fixed-20261122.jsonl --formal --label REAL --executor 'coding agent (Qoder) on the T4 Windows workstation; human rerun pending' --summary-dir eval/results/summary/i4_answer_metrics`
- date: 2026-11-22T09:03:25+00:00
- executor: coding agent (Qoder) on the T4 Windows workstation; human rerun pending
- exit code: 0 (this file is written by the run that produced it)
- corpus: cs5481-k8s-v135-16docs-36fd3eedf33f@bddfe3601885 (frozen: True)
- QA set: eval/qa_set.csv@b01b97fbdf2a (formal Kubernetes QA set (interface I2), gold quotes verbatim in the frozen corpus snapshot)

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
| `answer_correctness` | - | - | pending human grading (no --grades file supplied) |
| `n_graded` | - | - | 0 |
| `n_gradable` | - | - | 26 |
| `grading_coverage` | 0 | 26 | 0.0 |
| `grade_counts` | - | - | {'correct': 0, 'incorrect': 0, 'unsure': 0} |
| `hit@1` | 8 | 26 | 0.3077 |
| `hit@3` | 18 | 26 | 0.6923 |

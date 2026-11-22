# chunking_comparison

- command: `python -m eval.chunking_experiment --formal`
- date: 2026-11-22T02:13:25+00:00
- corpus: cs5481-k8s-v135-16docs-36fd3eedf33f@bddfe3601885 (frozen: True)
- QA set: eval/qa_set.csv@b01b97fbdf2a (formal Kubernetes QA set (interface I2), gold quotes verbatim in the frozen corpus snapshot)
- size / overlap / top_k / min_coverage: 600 / 80 / 3 / 0.5
- embedding: local:all-MiniLM-L6-v2
- executor: null1024-ws
- exit: 0
- chart: `hit_rates.svg` (drawn from the hit@1 / hit@3 objects below)

Retrieval hit rates below are the objects returned by `eval.metrics.retrieval_hit_rate`. This comparison does not score answers.

| strategy | chunks | length min | length max | length mean | hit@1 | hit@3 |
| --- | --- | --- | --- | --- | --- | --- |
| `fixed` | 668 | 147 | 600 | 587.5793 | 8/26 (0.3077) | 18/26 (0.6923) |
| `paragraph` | 775 | 81 | 683 | 515.7768 | 10/26 (0.3846) | 17/26 (0.6538) |

Disagreements: 21


# Formal corpus snapshot

- **corpus_id:** `cs5481-k8s-v135-16docs-36fd3eedf33f`
- **generated_at:** `2026-11-19T05:15:40Z`
- **formal domain documents:** 12 Kubernetes v1.35 pages
- **combined manifest:** 16 documents (12 formal + 4 preserved development documents)
- **source revision:** `snapshot-initial-v1.35` / `8b8f5d5669f06aa7c1b4f0b7d371adc89c4c7564`
- **licence:** [CC BY 4.0](https://github.com/kubernetes/website/blob/8b8f5d5669f06aa7c1b4f0b7d371adc89c4c7564/LICENSE)

## Why this corpus

Kubernetes documentation has an explicit open licence, a fixed upstream revision, and a useful mixture of concept, task, and reference pages. The selected pages cover cluster components, workloads, networking, configuration, storage, scheduling, probes, and kubectl commands, which supports both answerable and abstention questions.

## Descriptive statistics

- Clean characters: 326,727 total
- Length: min 2,754; median 25,774; max 57,545
- Deterministic cleaning removed 16,426 of 343,153 source characters (4.8%).

| doc_id | chars | bytes | sha256 |
| --- | ---: | ---: | --- |
| `k8s_v135_components` | 2754 | 2754 | `ed32fa5d1fa6b5b9…` |
| `k8s_v135_nodes` | 13523 | 13523 | `84a81c2ea04510e8…` |
| `k8s_v135_pods` | 22812 | 22816 | `fe88ef440f7259ce…` |
| `k8s_v135_deployments` | 57545 | 57553 | `b397f72b0a9a1df5…` |
| `k8s_v135_services` | 42606 | 42610 | `b5f379201bbe6112…` |
| `k8s_v135_configmaps` | 13409 | 13409 | `d9f4afd96d2d2df6…` |
| `k8s_v135_secrets` | 30420 | 30420 | `17a2a0cfa98d26bd…` |
| `k8s_v135_probes` | 26472 | 26472 | `5243744031d53d69…` |
| `k8s_v135_persistent_volumes` | 52722 | 52724 | `2032a965a6e47269…` |
| `k8s_v135_scheduling` | 33307 | 33307 | `f6a4c77fcc14afe4…` |
| `k8s_v135_kubectl_quick_reference` | 25076 | 25076 | `9fc5a81515bc12f0…` |
| `k8s_v135_stateless_deployment` | 6081 | 6081 | `c018cbcb15c09084…` |

## Cleaning and downstream impact

The script deterministically inlines shared prerequisites and YAML code samples from the same pinned commit, substitutes version placeholders, and removes site-only front matter, comments, and presentation wrappers. It retains the prose inside note/caution blocks, Markdown headings, code blocks, tables, and links. Long reference and task pages will produce more chunks than short concept pages; this is intentional variation for the T2 chunking comparison and T3 retrieval diagnostics.

## Reproduce and verify

```bash
python scripts/fetch_corpus.py
python -m pytest tests/test_loaders.py -q
python -m ragkit.cli ingest
```

A second fetch against the same pinned commit must leave `git diff` empty. All formal experiments must cite the `corpus_id` above.

# Formal corpus snapshot

- **corpus_id:** `cs5481-k8s-v135-16docs-115f404491b0`
- **generated_at:** `2026-11-18T20:21:23Z`
- **formal domain documents:** 12 Kubernetes v1.35 pages
- **combined manifest:** 16 documents (12 formal + 4 preserved development documents)
- **source revision:** `snapshot-initial-v1.35` / `8b8f5d5669f06aa7c1b4f0b7d371adc89c4c7564`
- **licence:** [CC BY 4.0](https://github.com/kubernetes/website/blob/8b8f5d5669f06aa7c1b4f0b7d371adc89c4c7564/LICENSE)

## Why this corpus

Kubernetes documentation has an explicit open licence, a fixed upstream revision, and a useful mixture of concept, task, and reference pages. The selected pages cover cluster components, workloads, networking, configuration, storage, scheduling, probes, and kubectl commands, which supports both answerable and abstention questions.

## Descriptive statistics

- Clean characters: 317,813 total
- Length: min 2,704; median 24,556; max 57,181
- Deterministic cleaning removed 17,604 of 335,417 source characters (5.2%).

| doc_id | chars | bytes | sha256 |
| --- | ---: | ---: | --- |
| `k8s_v135_components` | 2704 | 2704 | `073c633dfc31b379…` |
| `k8s_v135_nodes` | 13523 | 13523 | `84a81c2ea04510e8…` |
| `k8s_v135_pods` | 22615 | 22619 | `ea3be3ea7ec13a04…` |
| `k8s_v135_deployments` | 57181 | 57189 | `d1ebd5c2507d991e…` |
| `k8s_v135_services` | 42412 | 42416 | `4886ec2b1eabab7e…` |
| `k8s_v135_configmaps` | 11911 | 11911 | `fb11b2f2363826e7…` |
| `k8s_v135_secrets` | 30420 | 30420 | `17a2a0cfa98d26bd…` |
| `k8s_v135_probes` | 24040 | 24040 | `1f8aaa918b5cd9e6…` |
| `k8s_v135_persistent_volumes` | 52718 | 52720 | `0f2372da323e37ac…` |
| `k8s_v135_scheduling` | 31070 | 31070 | `dbe49c55c8bb40fb…` |
| `k8s_v135_kubectl_quick_reference` | 25072 | 25072 | `2e270c0bd6b7381c…` |
| `k8s_v135_stateless_deployment` | 4147 | 4147 | `47a7db69b78a8054…` |

## Cleaning and downstream impact

The script removes site-only front matter, comments, figures, include directives, and shortcode wrappers. It retains the prose inside note/caution blocks, Markdown headings, code blocks, tables, and links. Long reference and task pages will produce more chunks than short concept pages; this is intentional variation for the T2 chunking comparison and T3 retrieval diagnostics.

## Reproduce and verify

```bash
python scripts/fetch_corpus.py
python -m pytest tests/test_loaders.py -q
python -m ragkit.cli ingest
```

A second fetch against the same pinned commit must leave `git diff` empty. All formal experiments must cite the `corpus_id` above.

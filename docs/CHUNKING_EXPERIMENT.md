# Chunking 对比实验（T2）

比较 `fixed` 与 `paragraph` 对检索质量的影响。命中率只来自
`eval.metrics.retrieval_hit_rate()`，本实验不另写 hit@k，也不计算回答正确率或拒答率。

**下面这张表是正式实验。** 语料是已合并的 PR #14 快照，QA 是已合并的 PR #15
正式集。命令 `python -m eval.chunking_experiment --formal` 退出码 0，汇总在
`eval/results/summary/chunking_comparison/`。更早的两次运行用的是开发 QA，数字见文末，不与这张表混用。

## 比的是哪两种策略

流水线里已经有两种分块，而且重叠的含义相同，所以对比就用它们，不再加第三种，也不做
size / overlap 网格。

- `fixed`：长度为 `size` 的字符窗，尽量在空格或换行处切开；下一窗从 `end - overlap` 开始。
- `paragraph`：按空行切段，再尽量装到 `size`；装完之后用同一种规则把后一块向左延伸 `overlap` 个字符。

两种策略都保证 `document.text[chunk.char_start:chunk.char_end] == chunk.text`。
`chunk_id` 保持 `{doc_id}#{index:04d}`，策略名写在 `Chunk.strategy` 上，不写进 id。
两种策略各写各的 collection：`chunks_fixed` 与 `chunks_paragraph`。一次 `ingest` 只清空当前策略的 collection。

`paragraph` 的块可以长于 `size`。打包上限是 `size`，随后 `_apply_overlap` 再向左补重叠。这次最长仍是 683（`rag_wikipedia#0007`），最短 81（`k8s_v135_services#0064`）。`fixed` 的窗口不超过 `size`，最长 600，最短 147（`vector_db_wikipedia#0006`）。这四篇 Wikipedia 仍在冻结快照里，所以长度极值不一定落在 Kubernetes 页面上。

## 为什么 gold 是原文字符区间

`chunk_id` 是分块的产物。同一句话在两种策略里会落在不同的 id、不同的边界上。用 chunk id 当 gold，等于让每种策略拿自己的切分当标准。

gold 是 `qa_set.csv` 里的 `evidence_doc_id` + `evidence_quote`。`locate_evidence()` 把它定位成原文档上的 `[char_start, char_end)`。一块算不算命中，看它盖住这个区间的比例是否达到同一个 `min_coverage`（本次 0.5）。

## 什么保持不变

| 项 | 本次取值 |
| --- | --- |
| `size` / `overlap` | 600 / 80（`config.toml`，文件未改） |
| `top_k` | 3 |
| `min_coverage` | 0.5 |
| hit levels | 1 和 3 |
| embedding | `local:all-MiniLM-L6-v2`（384 维，本地 ONNX，无 API key） |
| QA | `eval/qa_set.csv@b01b97fbdf2a`。36 题：26 道 answerable 进入命中率分母，10 道 unanswerable 不进入。状态是 formal Kubernetes QA set |
| 语料 | `cs5481-k8s-v135-16docs-36fd3eedf33f@bddfe3601885`，`corpus_frozen=true`。索引含快照里的全部 16 篇（12 篇 Kubernetes + 4 篇保留的 Wikipedia）。正式 gold 都在 Kubernetes 文档上 |

配置快照里的 `llm` 是 `gpt-4o-mini`。那是 `config.toml` 里的名字。这次对比只做检索，**没有调用 LLM**。命中率不是回答正确率。

## 正式结果

- 命令：`python -m eval.chunking_experiment --formal`
- 分支：`t2-chunking-formal`（从已含 PR #15 的 `origin/main` 拉开）
- 执行者：Cursor 编码 agent。本机 git 用户名是 `null1024-ws`，写在 `run.md` 里。组员本人尚未重跑。
- `generated_at`：`2026-11-22T02:13:25+00:00`（GMT+8 10:13），退出码 0。
- 同一命令在 `2026-11-22T02:12:00+00:00` 先跑过一次，汇总表相同。随后 `metrics.json` 补上了分歧列表，重跑覆盖了目录。当前文件是 10:13 这一次。
- 图：`eval/results/summary/chunking_comparison/hit_rates.svg`，由同一次运行按表里的 hit@1 / hit@3 画出。
- `fixed` 的 8/26 与 18/26 和 T4 先前对同一正式集、默认 `fixed` 索引单独跑的 `retrieval_hit_rate()` 一致。

| strategy | chunks | length min | length max | length mean | hit@1 | hit@3 |
| --- | --- | --- | --- | --- | --- | --- |
| `fixed` | 668 | 147 | 600 | 587.5793 | 8/26 (0.3077) | 18/26 (0.6923) |
| `paragraph` | 775 | 81 | 683 | 515.7768 | 10/26 (0.3846) | 17/26 (0.6538) |

`paragraph` 的 hit@1 多 2 题，hit@3 少 1 题。块更多、平均更短，并没有在两个 k 上同时更好。21 处分歧都在 `metrics.json` 的 `disagreements` 里。

## 两个方向相反的漏检

**K06，只有 `paragraph` 命中，而且排在第 1。** 问的是 Pod 如何被描述成共享命名空间和卷的一组容器。gold 是 `k8s_v135_pods` 1249–1342，「A Pod is similar to a set of containers with shared namespaces and shared filesystem volumes.」。

- `fixed` 把整句放进 `k8s_v135_pods#0002`（1037–1632，595 字符）。这块不在 top-3。top-3 是 `#0000`、`#0038`、`#0037`，覆盖率 0。
- `paragraph` 的 `k8s_v135_pods#0003`（1167–1399，232 字符）盖住全句，排名第 1（score 0.7515）。

较短的那一块和这句问法更接近，所以排到第一。`fixed` 把它包在大约 600 字的窗口里，那个窗口没有进前三。

**K23，只有 `fixed` 命中，而且 hit@3 也没命中 `paragraph`。** 问的是哪条 kubectl 命令显示合并后的 kubeconfig。gold 是 `k8s_v135_kubectl_quick_reference` 1554–1608，「kubectl config view # Show Merged kubeconfig settings.」。

- `fixed` 的 `#0002`（1038–1636，598 字符）盖住全句，排名第 1（score 0.6119）。
- `paragraph` 也有盖住全句的块：`#0002`（1007–1608）和 `#0003`（1528–2116）。它们都不在 top-3。top-3 是 `k8s_v135_persistent_volumes#0008`、本篇 `#0047`、本篇 `#0043`，对这段 gold 的覆盖率是 0。

同一条命令，`paragraph` 的邻接文本不同，盖住它的块没有进前三，前三里还有一篇别的文档。

这两题在 hit@3 上各漏一次，方向相反。其余分歧没有互相抵消，所以 hit@3 是 18/26 对 17/26，不是打平。

## 更早的开发运行

这两次都不是正式实验。QA 当时还是 Wikipedia 开发集，分母是 27 而不是 26。

2026-11-17，语料 `data/raw/manifest.json@b5bfc0d70e4a`，`corpus_frozen=false`，QA `eval/qa_set.csv@80b1d950f652`。`fixed` 28 块，hit@1 16/27 (0.5926)，hit@3 23/27 (0.8519)；`paragraph` 33 块，hit@1 17/27 (0.6296)，hit@3 23/27 (0.8519)。见 `RUNLOG.md` 第 9 节。

2026-11-21，同一开发 QA 改在冻结快照上重跑，QA 引用变成 `eval/qa_set.csv@c97051d8789c`。`fixed` 668 块、`paragraph` 775 块，命中率与 11 月 17 日相同。见 `RUNLOG.md` 第 10 节。PR #15 之后这份开发集挪到了 `eval/qa_set_dev_v0.csv`，`eval/qa_set.csv` 改成上面的正式集。

## 这次没有做的事

- 没有调用 LLM，没有回答正确率，没有拒答率。
- 没有改切分算法，没有改 `eval/metrics.py`，没有改语料或 QA。
- 开发模式的 `--out` 仍然不能写进 `eval/results/summary/`。`--formal --qa` 指向已提交集合以外的文件仍然退出 2。

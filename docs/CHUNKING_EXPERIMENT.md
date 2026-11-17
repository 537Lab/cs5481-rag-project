# Chunking 对比实验（T2）

比较 `fixed` 与 `paragraph` 对检索质量的影响。命中率只来自
`eval.metrics.retrieval_hit_rate()`，本实验不另写 hit@k，也不计算回答正确率或拒答率。

**本页数字是开发用结果，不是正式实验结果。** 语料仍是 `CORPUS_V0`（没有
`data/raw/frozen_manifest.json`），QA 仍是 `eval/qa_set.csv` 上的开发集。
`--formal` 会被 `assert_formal_inputs()` 拒绝，因此没有写入
`eval/results/summary/chunking_comparison/`。

## 比的是哪两种策略

流水线里已经有两种分块，而且重叠的含义相同，所以对比就用它们，不再加第三种，也不做
size / overlap 网格。

- `fixed`：长度为 `size` 的字符窗，尽量在空格或换行处切开；下一窗从 `end - overlap` 开始。
- `paragraph`：按空行切段，再尽量装到 `size`；装完之后用同一种规则把后一块向左延伸 `overlap` 个字符。

两种策略都保证 `document.text[chunk.char_start:chunk.char_end] == chunk.text`。
`Chunk.meta` 里的 `chunk_overlap` 是配置值，`chunk_overlap_actual` 是相邻区间真正重叠的字符数。
`chunk_id` 保持 `{doc_id}#{index:04d}`，策略名写在 `Chunk.strategy` 上，不写进 id。

两种策略各写各的 collection：`chunks_fixed` 与 `chunks_paragraph`。一次 `ingest` 只清空当前策略的 collection。

`paragraph` 的块可以长于 `size`。打包上限是 `size`，随后 `_apply_overlap` 再向左补重叠，段间空白也会被带进来。这次实测最长 683，而 `size` 是 600。`fixed` 的窗口本身不超过 `size`，实测最长就是 600。

## 为什么 gold 是原文字符区间

`chunk_id` 是分块的产物。同一句话在两种策略里会落在不同的 id、不同的边界上。用 chunk id 当 gold，等于让每种策略拿自己的切分当标准，比较没有意义。

gold 是 `qa_set.csv` 里的 `evidence_doc_id` + `evidence_quote`。`locate_evidence()` 把它定位成原文档上的 `[char_start, char_end)`。这个区间不随策略改变。一块算不算命中，看它盖住这个区间的比例是否达到同一个 `min_coverage`（本次 0.5）。

A17 说明为什么不能改用 chunk id。gold 是 `vector_db_wikipedia` 的 2905–3040。`paragraph` 把它切成两段：`#0006` 只盖住 51/135（0.378，低于 0.5），`#0007` 盖住 135/135。命中的是覆盖率，不是「这块的 id 在不在名单里」。

## 什么保持不变

同一次运行里两种策略共用：

| 项 | 本次取值 |
| --- | --- |
| `size` / `overlap` | 600 / 80（`config.toml`，文件未改） |
| `top_k` | 3 |
| `min_coverage` | 0.5 |
| hit levels | 1 和 3 |
| embedding | `local:all-MiniLM-L6-v2`（384 维，本地 ONNX，无 API key） |
| QA | `eval/qa_set.csv@80b1d950f652`，35 题，其中 27 题 answerable 进入命中率分母 |
| 语料 | `data/raw/manifest.json@b5bfc0d70e4a`，`corpus_frozen=false` |

配置快照里的 `llm` 是 `gpt-4o-mini`。那是 `config.toml` 里的名字。这次对比只做检索，**没有调用 LLM**，也没有付费请求。命中率不是回答正确率。

## 开发用结果

- 命令：`python -m eval.chunking_experiment`
- 组员重跑：2026-11-17T12:50:10Z（GMT+8 20:50），仓库根目录，已激活 `.venv`，退出码 0。当前 JSON 是这一次写的。
- 更早一次：2026-11-17T12:43:21Z，由 Cursor 编码 agent 执行，汇总数字相同，记录在 `RUNLOG.md` 第 9 节。
- 原始 JSON：`eval/results/raw/chunking_comparison/comparison.json`（gitignore，不入库）
- 状态：开发用，非正式实验结果

| strategy | chunks | length min | length max | length mean | hit@1 | hit@3 |
| --- | --- | --- | --- | --- | --- | --- |
| `fixed` | 28 | 147 | 600 | 554.8571 | 16/27 (0.5926) | 23/27 (0.8519) |
| `paragraph` | 33 | 89 | 683 | 480.3939 | 17/27 (0.6296) | 23/27 (0.8519) |

`fixed` 的 16/27 与 23/27 和 T4 先前对同一开发集、同一 `fixed` 索引单独跑的 `retrieval_hit_rate()` 一致。`paragraph` 多 5 块，平均更短，hit@1 多 1 题，hit@3 相同。

## 两个方向相反的漏检

下面两题都是一种策略的 top-3 盖住了 gold（覆盖率 1.0），另一种的 top-3 覆盖率为 0。数字来自上面那次运行，再对照两种分块的字符区间。

**A06，只有 `fixed` 在 hit@3 命中。** 问的是 RAG 为什么省计算和费用。gold 是 `rag_wikipedia` 1312–1413，「RAG also reduces the need to retrain LLMs with new data...」。

- `fixed` 的 `rag_wikipedia#0002` 是 1033–1627，整句都在里面，检索排名第 2。
- `paragraph` 也有一块完全盖住这句：`rag_wikipedia#0002` 为 1120–1800（680 字符）。它不在 top-3 里。top-3 是 `#0001`、`#0004`、`#0009`，对 gold 的覆盖率是 0。

同一句话，`paragraph` 的窗口更靠后、也更长，邻接文本不同，这块的向量就没进前三。

**A17，只有 `paragraph` 命中，而且 hit@3 也命中。** 问的是 RAG 查询时对用户 prompt 做了什么。gold 是 `vector_db_wikipedia` 2905–3040，「Given a user prompt, the feature vector of the prompt is computed...」。

- `fixed` 把整句放进 `vector_db_wikipedia#0005`（2584–3179，595 字符）。这块不在 top-3。top-3 是 `#0006`、`rag_wikipedia#0000`、`rag_wikipedia#0002`，覆盖率 0。
- `paragraph` 把这句切开。`#0006`（2274–2956）只盖住 51/135，低于 0.5，即使被取回也不算命中。`#0007`（2876–3221，345 字符）盖住全句，排名第 1（score 0.5312）。

`paragraph` 把这句收进一个更短的尾块，查询和这块更接近，所以排到第一。`fixed` 把它包在一个约 600 字的窗口里，那个窗口没有进前三。

这两题在 hit@3 上各漏一次，方向相反，所以 hit@3 都是 23/27。hit@1 的净差来自三题：A08 与 A17 是 `paragraph` 排第一而 `fixed` 不是，A16 相反。A16 两边都完整盖住 gold，只是 `fixed` 的覆盖块排第 1、`paragraph` 的排第 2，所以它只影响 hit@1。

## 这次没有做的事

- 没有把开发数字写进 `eval/results/summary/`。`--formal` 的退出码是 2，原因是 I1 快照不存在，以及 8 道 unanswerable 题没有 `REVIEWED_BY`。
- 没有调用 LLM，没有回答正确率，没有拒答率。
- 语料或 QA 冻结之后，要用同一命令重跑，并只有在 `--formal` 通过之后才能把汇总放进 `summary/chunking_comparison/`。

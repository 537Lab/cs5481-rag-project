# 五人开发任务包（v1.1 之后，正式开发阶段）

> 基础流水线已经跑通，所以**不要把五个基础文件简单分给五个人**。下面五个任务包按
> Topic 5 尚未完成的工作重新划分，五人地位平等，每人都有**代码开发 + 自动化测试 +
> 运行验证 + 实验分析**四项责任。组长承担 T1，同样写代码，不是只做进度管理。
>
> 所有人都在**同一个仓库、同一套 `ragkit` 契约**上继续开发，禁止另起炉灶重写系统。
> 未经全组确认，不要替别人完成他/她的任务包。

## 当前已完成（不要重复做）

真实语料 4 篇 + manifest/出处、两种最小 chunker、本地 ONNX embedding、Chroma 持久化与检索、
OpenAI 兼容 LLM 客户端、引用结构校验与拒答、评测共同证据标准、离线测试 57 passed、
GitHub Actions CI。**没有**任何正式实验结果、20 组 QA、chunking 对比数字。

## 契约冻结（并行开发的前提）

以下三项在 `ragkit/contracts.py` / `eval/evidence.py` 中已固定，改动需 ≥2 人同意：

- `Document` / `Chunk` / `RetrievedChunk` / `Answer` 的字段；
- 不变式 `doc.text[chunk.char_start:chunk.char_end] == chunk.text`；
- gold 证据 = `evidence_doc_id` + `evidence_quote` → 原始文档字符区间，**不用 chunk id**。

**解除数据依赖的约定**：`CORPUS_V0` = 当前已提交的 4 篇 `data/raw/*.txt`（doc_id 与文本不得被 T1 修改）。
五人先用 CORPUS_V0 + `tests/fixtures/` 并行开发；T1 扩充的语料放在新 doc_id 下，
另出 `data/raw/frozen_manifest.json` 作为正式实验的冻结快照。这样没有人需要等别人。

---

## T1 正式知识库与文档处理（组长承担）

| 项 | 内容 |
| --- | --- |
| 输入 | 公开授权文档源；现有 `data/raw/` 与 `SOURCES.md` |
| 输出 | 扩充后的正式语料（建议 10–20 篇，含不同主题/长度/噪声）、`manifest.json`、`SOURCES.md`、`frozen_manifest.json`；`ragkit/loaders.py` 增加编码校验、去重、空文件处理与（可选）PDF/HTML 转文本 |
| 允许修改 | `ragkit/loaders.py`、`data/raw/**`、`scripts/fetch_corpus.py`、`tests/test_loaders.py`、`docs/CORPUS.md` |
| 依赖 | **无**（但需 Day 1 先声明 CORPUS_V0 冻结，供其他人使用） |
| 现在可跑 | `python -m pytest tests/test_loaders.py -q`、`python -m ragkit.cli ingest` |
| 交付后验收 | `python -m pytest tests/test_loaders.py -q` 全绿；`python -m ragkit.cli ingest` 成功；逐条检查 manifest 的 `source_uri`/`license` 可打开；CORPUS_V0 四篇 doc_id 与文本哈希不变 |
| 完成标准 | ≥10 篇真实文档、出处与许可齐全、零 MOCK 混入、去重与编码有测试、字符偏移不变式成立、给出语料规模/长度分布的描述性统计 |
| 实验分析 | 文档类型、长度、噪声对后续检索的影响（描述性，不编造指标） |

## T2 Chunking 策略与对比实验

| 项 | 内容 |
| --- | --- |
| 输入 | CORPUS_V0、`eval/evidence.py`、T4 的 `qa_set.csv`（先用约定的 `tests/fixtures/gold_v0.csv` 5 行解除依赖） |
| 输出 | `ragkit/chunking.py` 的策略参数化与稳定元数据；`eval/chunking_experiment.py`；`eval/results/chunking_<date>.json`（gitignore）；`docs/CHUNKING_EXPERIMENT.md` |
| 允许修改 | `ragkit/chunking.py`、`tests/test_chunking.py`、`eval/chunking_experiment.py`、`docs/CHUNKING_EXPERIMENT.md` |
| 依赖 | T1 冻结语料（CORPUS_V0 已解除）、T4 的 gold（`gold_v0.csv` 已解除） |
| 现在可跑 | `python -m pytest tests/test_chunking.py -q` |
| 交付后验收 | 上述测试全绿；`python -m eval.chunking_experiment --help` 可用；结果文件含命令/config/日期；`python -m pytest -q` 全绿 |
| 完成标准 | ≥2 种策略在**同一 gold、同一 top_k、同一 min_coverage** 下可比；报告 chunk 数、长度分布、hit@1/hit@3；每个数字来自真实运行，无硬编码 |
| 实验分析 | 解释策略差异为何影响检索质量，附失败案例 |

## T3 检索层与向量库

| 项 | 内容 |
| --- | --- |
| 输入 | CORPUS_V0、chunk 输出、本地 ONNX embedding |
| 输出 | `ragkit/store.py` / `ragkit/embeddings.py` 增强（collection 隔离、score 语义、可选阈值/混合检索）；`eval/retrieval_metrics.py`；`docs/RETRIEVAL.md` |
| 允许修改 | `ragkit/store.py`、`ragkit/embeddings.py`、`tests/test_store.py`、`tests/test_embeddings.py`、`eval/retrieval_metrics.py`、`docs/RETRIEVAL.md` |
| 依赖 | T2 的 chunk 格式（`Chunk` 契约已冻结，无需等待） |
| 现在可跑 | `python -m pytest tests/test_store.py tests/test_embeddings.py -q`、`python -m ragkit.cli retrieve "..." --top-k 3` |
| 交付后验收 | 上述测试全绿；重开 Chroma 客户端仍可查；`get_chunk()` 出处 roundtrip 完整；hit@1/hit@3 能由真实检索结果计算 |
| 完成标准 | 不同策略索引不混、无需 API key 可跑、检索分数语义写进文档、给出 top_k 与失败案例分析 |
| 实验分析 | score 分布、检索失败原因、是否值得加关键词检索 |

## T4 评测集、指标与拒答评估

| 项 | 内容 |
| --- | --- |
| 输入 | CORPUS_V0、`eval/evidence.py`、`eval/qa_template.csv` |
| 输出 | `eval/qa_set.csv`（≥20 组，含 answerable / unanswerable）、`eval/metrics.py`、`eval/judge_protocol.md`、`tests/test_eval_metrics.py` |
| 允许修改 | `eval/qa_set.csv`、`eval/metrics.py`、`eval/judge_protocol.md`、`tests/test_eval_metrics.py`、`eval/README.md`（细化指标） |
| 依赖 | T5 的 LLM 输出格式（`Answer` 契约已冻结；先用 MOCK 输出开发） |
| 现在可跑 | `python -m pytest tests/test_eval_evidence.py -q` |
| 交付后验收 | `python -m pytest tests/test_eval_metrics.py tests/test_eval_evidence.py -q` 全绿；每条 gold quote 都通过 `locate_evidence()`；`python -m eval.metrics --help` 可用 |
| 完成标准 | ≥20 组 QA；命中率用 `is_retrieval_hit()`；正确率由**人工 judge**（默认）并披露；明确区分结构校验与事实正确性；正确拒答率与误拒答率可算；**无任何硬编码结果** |
| 实验分析 | QA 覆盖度、拒答题比例、评分者一致性、指标局限讨论 |

## T5 LLM 问答、引用支持性与可运行演示

| 项 | 内容 |
| --- | --- |
| 输入 | 检索结果、`Answer` 契约、LLM API 配置（**付费调用须全组先确认**） |
| 输出 | `ragkit/generation.py` 增强（prompt、拒答策略、可选 support judge 接口）、`ragkit/cli.py` 的 `demo` 命令、`demo/` 最小演示、`docs/ANSWER_QUALITY.md` |
| 允许修改 | `ragkit/generation.py`、`ragkit/cli.py`、`tests/test_generation.py`、`demo/**`、`docs/ANSWER_QUALITY.md` |
| 依赖 | T3 检索契约、T4 指标契约（均已冻结） |
| 现在可跑 | `python -m pytest tests/test_generation.py -q`、`python -m ragkit.cli offline-demo`（MOCK） |
| 交付后验收 | 上述测试全绿；`demo` 一键可运行；真实 `cli ask` **仅在用户提供密钥并确认费用方案后**执行；README 写明三层引用概念 |
| 完成标准 | 真实回答带逐字可回查引用、拒答可评估、结构校验不被宣称为正确性、演示可复现、无未授权付费调用 |
| 实验分析 | 回答正确率（人工 judge）、拒答表现、幻觉/错误引用失败案例 |

---

## 依赖关系与建议顺序

```
                 CORPUS_V0（已冻结，全部人立即可用）
                          │
   T1 ──► 正式语料快照 ───┼──► T2 对比实验 ──┐
   （可并行，不阻塞）     ├──► T3 检索指标 ──┼──► 联合集成实验（最后一起跑）
                          └──► T4 QA/指标 ◄──┤
                                    ▲        │
                                    └── T5 问答/演示
```

- **Day 1**：全员 clone、跑通 `offline-demo` + `pytest`、认领 Issue、读 `contracts.py` 与 `eval/README.md`；T1 确认 CORPUS_V0 冻结。
- **Day 2–4**：五人并行开发，各自只改自己任务包列出的文件，各自补测试并本地跑通。
- **Day 5**：合并 PR 后，五人一起跑一次完整对比实验（T2+T3+T4+T5 集成），结果写入 `eval/results/`。
- **Day 6–7**：分析、报告、演示、**贡献比例 + 全体签名单独一页**（课程硬性要求）。

## Coding Agent 使用约定

任务包按"输入/输出/可改文件/验收命令"写清，适合让 Coding Agent 辅助执行。但每人必须：

1. 亲自读一遍 Agent 生成的代码，能在组内解释实现思路与关键取舍；
2. 亲自跑验收命令并保留输出，不把 Agent 的"已完成"当成验证；
3. 在 `docs/AI_USAGE.md` 记录使用过哪些 Agent、用于哪个任务、人工复核了什么；
4. 不把 Agent 生成的数字写进报告，除非来自自己真实运行。

课程要求报告含**每人贡献比例与全体签名**，AI 辅助使用情况也应如实披露。

## 明确禁止

- 另起仓库/另写一套 RAG 系统；修改别人任务包的文件而不告知对方。
- 硬编码命中率/正确率、伪造运行记录、把 MOCK 输出当实验结果。
- 提交 `.env` / API key / `data/index/` / `eval/results/`。
- 未经全组确认产生**付费 LLM API 调用**。

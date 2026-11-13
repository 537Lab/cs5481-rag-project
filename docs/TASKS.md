# 五人开发任务包（正式开发阶段）

> 基础流水线已经跑通，所以**不要把五个基础文件简单分给五个人**。下面五个任务包按
> Topic 5 尚未完成的工作划分，五人地位平等，每人都有**代码开发 + 自动化测试 +
> 运行验证 + 实验分析**四项责任。T1 **暂定**由组长承担，同样写代码，不是只做进度管理。
>
> 所有人都在**同一个仓库、同一套 `ragkit` 契约**上继续开发，禁止另起炉灶重写系统。
> 任务划分、冻结规则与协作流程均为 bootstrap 阶段拟定，**尚未征求另外四名组员意见**；
> 五人开工时应共同确认或调整，在此之前不要写成「全组已确认」。
> 未经对方同意，不要替别人完成他/她的任务包。

## 当前已完成（不要重复做）

真实语料 4 篇 + manifest / 出处、两种最小 chunker、本地 ONNX embedding、Chroma 持久化与检索、
OpenAI 兼容 LLM 客户端、引用结构校验与拒答、评测共同证据标准、离线测试（57 passed / 2 skipped，
见 `RUNLOG.md`）、GitHub Actions CI。**没有**任何正式实验结果、20 组 QA 或 chunking 对比数字。

## 契约冻结（并行开发的前提）

以下三项在 `ragkit/contracts.py` / `eval/evidence.py` 中已固定，改动需在 PR 中获 ≥2 人同意
（协作约定见 [`CONTRIBUTING.md`](../CONTRIBUTING.md)）：

- `Document` / `Chunk` / `RetrievedChunk` / `Answer` 的字段；
- 不变式 `doc.text[chunk.char_start:chunk.char_end] == chunk.text`；
- gold 证据 = `evidence_doc_id` + `evidence_quote` → 原始文档字符区间，**不用 chunk id**。

---

## 语料与评测集的冻结规则（T1 → T4 → 正式实验）

| 名称 | 内容 | 状态 / 冻结时点 | 约束 |
| --- | --- | --- | --- |
| `CORPUS_V0` | 当前已提交的 4 篇 `data/raw/*.txt` 及其 doc_id、文本 | **已冻结**（bootstrap 基线） | T1 不得修改这 4 篇的 doc_id 或文本；只供开发与自测，**不得当作正式实验语料** |
| 正式语料快照 | T1 扩充后的语料 + 交付时新建的 `data/raw/frozen_manifest.json` | T1 的 PR 合并、经 review 确认后冻结 | 冻结后不得再改 doc_id / 文本 / manifest；正式实验必须引用这一版快照并保留其标识 |
| 正式评测集 | T4 交付的 `eval/qa_set.csv`（≥20 组，含 gold 引文） | T4 的 PR 合并、经 review 确认后冻结 | 冻结后所有策略对比必须使用同一份 `qa_set.csv`、同一 `top_k`、`min_coverage`、embedding 与 LLM |

依赖顺序与判定：

1. **T1 不阻塞并行开发**：所有人先用 `CORPUS_V0` + `tests/fixtures/` 写代码和自测。
2. **T4 依赖 T1**：正式 QA 的每条 `evidence_quote` 必须逐字出自**冻结后的正式语料**，
   并能通过 `eval/evidence.py::locate_evidence()` 定位到原始文档字符区间。
   语料未冻结前不得确定正式 gold。
3. **T2 / T3 / T5 的正式数字依赖 T4**：chunking 对比、检索命中率、回答正确率等正式指标，
   只能在正式语料与正式评测集都冻结之后、使用同一份评测集计算。
4. **冻结前允许**：用 `CORPUS_V0`、`eval/qa_template.csv` 的 2 行格式示例或自己在
   `tests/fixtures/` 下新建并明确标注 MOCK 的样例做开发、调试与自测。这些输出必须标注
   「开发用」，**不得称为正式实验结果、不得写入报告**。
5. **不存在 `tests/fixtures/gold_v0.csv`**，也不存在任何「临时 gold」。旧版 T2 任务包对它的
   引用是错误的，已删除；不要按那个名字新建文件或把它当作 T4 的替代品。
6. 冻结快照由对应任务负责人在 PR 中说明内容、校验方式与影响范围；本轮整理**不生成**任何
   正式语料、gold 或实验结果。

---

## T1 正式知识库与文档处理（暂定组长承担）

| 项 | 内容 |
| --- | --- |
| 输入 | 公开授权文档源；现有 `data/raw/` 与 `SOURCES.md` |
| 输出 | 扩充后的正式语料（建议 10–20 篇，含不同主题/长度/噪声）、`manifest.json`、`SOURCES.md`、新建 `frozen_manifest.json`（记录语料快照标识与校验方式）；`ragkit/loaders.py` 增加编码校验、去重、空文件处理与（可选）PDF/HTML 转文本 |
| 允许修改 | `ragkit/loaders.py`、`data/raw/**`、`scripts/fetch_corpus.py`、`tests/test_loaders.py`、`docs/CORPUS.md` |
| 依赖 | **无上游依赖**；但下游 T4 的 gold 必须基于本任务冻结的正式语料，见上文冻结规则 |
| 现在可跑 | `python -m pytest tests/test_loaders.py -q`、`python -m ragkit.cli ingest` |
| 交付后验收 | 上述测试全绿；`python -m ragkit.cli ingest` 成功；逐条检查 manifest 的 `source_uri` / `license` 可打开；`CORPUS_V0` 四篇 doc_id 与文本不变 |
| 完成标准 | ≥10 篇真实文档、出处与许可齐全、零 MOCK 混入、去重与编码有测试、字符偏移不变式成立、给出语料规模/长度分布的描述性统计 |
| 实验分析 | 文档类型、长度、噪声对后续检索的影响（描述性，不编造指标） |

## T2 Chunking 策略与对比实验

| 项 | 内容 |
| --- | --- |
| 输入 | 开发期：`CORPUS_V0` + `eval/evidence.py` + `eval/qa_template.csv`（格式示例）；正式对比：**T1 冻结的正式语料 + T4 冻结的 `eval/qa_set.csv`** |
| 输出 | `ragkit/chunking.py` 的策略参数化与稳定元数据；`eval/chunking_experiment.py`；`docs/CHUNKING_EXPERIMENT.md`；真实运行的汇总结果按 [`eval/README.md`](../eval/README.md) 提交 |
| 允许修改 | `ragkit/chunking.py`、`tests/test_chunking.py`、`eval/chunking_experiment.py`、`docs/CHUNKING_EXPERIMENT.md` |
| 依赖 | 代码开发与自测**不等待任何人**（用 `CORPUS_V0` + `Chunk` 契约）；**正式对比数字**依赖 T1 冻结语料与 T4 冻结评测集。不存在任何临时 gold 文件 |
| 现在可跑 | `python -m pytest tests/test_chunking.py -q` |
| 交付后验收 | 上述测试全绿；`python -m eval.chunking_experiment --help` 可用；结果文件含命令 / config / 日期；`python -m pytest -q` 全绿 |
| 完成标准 | ≥2 种策略在**同一 gold、同一 top_k、同一 min_coverage** 下可比；报告 chunk 数、长度分布、hit@1 / hit@3；每个数字来自真实运行，无硬编码 |
| 实验分析 | 解释策略差异为何影响检索质量，附失败案例 |

## T3 检索层与向量库

| 项 | 内容 |
| --- | --- |
| 输入 | `CORPUS_V0`、chunk 输出、本地 ONNX embedding |
| 输出 | `ragkit/store.py` / `ragkit/embeddings.py` 增强（collection 隔离、score 语义、可选阈值/混合检索）；`eval/retrieval_metrics.py`；`docs/RETRIEVAL.md` |
| 允许修改 | `ragkit/store.py`、`ragkit/embeddings.py`、`tests/test_store.py`、`tests/test_embeddings.py`、`eval/retrieval_metrics.py`、`docs/RETRIEVAL.md` |
| 依赖 | `Chunk` 契约已冻结，无需等待 T2 实现；正式 hit@k 数字依赖 T4 冻结评测集 |
| 现在可跑 | `python -m pytest tests/test_store.py tests/test_embeddings.py -q`、`python -m ragkit.cli retrieve "..." --top-k 3` |
| 交付后验收 | 上述测试全绿；重开 Chroma 客户端仍可查；`get_chunk()` 出处 roundtrip 完整；hit@1 / hit@3 能由真实检索结果计算 |
| 完成标准 | 不同策略索引不混、无需 API key 可跑、检索分数语义写进文档、给出 top_k 与失败案例分析 |
| 实验分析 | score 分布、检索失败原因、是否值得加关键词检索 |

## T4 评测集、指标与拒答评估

| 项 | 内容 |
| --- | --- |
| 输入 | **T1 冻结的正式语料**（gold 引文的唯一来源）；开发期可用 `CORPUS_V0`；`eval/evidence.py`、`eval/qa_template.csv` |
| 输出 | `eval/qa_set.csv`（≥20 组，含 answerable / unanswerable）、`eval/metrics.py`、`eval/judge_protocol.md`、`tests/test_eval_metrics.py` |
| 允许修改 | `eval/qa_set.csv`、`eval/metrics.py`、`eval/judge_protocol.md`、`tests/test_eval_metrics.py`、`eval/README.md`（细化指标） |
| 依赖 | **T1 正式语料冻结**；`Answer` 契约已冻结，代码开发期可先用 MOCK 输出 |
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
| 依赖 | `Answer` 契约 / 检索契约已冻结；正式回答质量评估依赖 T4 冻结评测集 |
| 现在可跑 | `python -m pytest tests/test_generation.py -q`、`python -m ragkit.cli offline-demo`（MOCK） |
| 交付后验收 | 上述测试全绿；`demo` 一键可运行；真实 `cli ask` **仅在用户提供密钥并确认费用方案后**执行；README 写明三层引用概念 |
| 完成标准 | 真实回答带逐字可回查引用、拒答可评估、结构校验不被宣称为正确性、演示可复现、无未授权付费调用 |
| 实验分析 | 回答正确率（人工 judge）、拒答表现、幻觉/错误引用失败案例 |

---

## 依赖关系与建议顺序

```
   CORPUS_V0（已冻结，仅用于开发/自测）
        │
        ├──► T2 / T3 / T5 并行写代码、补测试（不等待任何人）
        │
        ▼
   T1 正式语料快照（T1 交付、review 后冻结）
        ▼
   T4 正式评测集 qa_set.csv（gold 引文逐字出自冻结语料，review 后冻结）
        ▼
   T2 对比实验 / T3 检索指标 / T5 回答评估（同一语料 + 同一评测集）
        ▼
   联合集成实验（最后一起跑，结果按 eval/README.md 提交）
```

- **Day 1**：全员 clone、跑通 `offline-demo` + `pytest`、认领 Issue、读 `contracts.py` 与 `eval/README.md`；五人共同确认协作规则与任务分配。
- **Day 2–4**：五人并行开发，各自只改自己任务包列出的文件，各自补测试并本地跑通；T1 冻结正式语料，T4 据此定稿 gold。
- **Day 5**：合并 PR 后，五人一起跑一次完整对比实验，按 [`eval/README.md`](../eval/README.md) 提交汇总结果。
- **Day 6–7**：分析、报告、演示、**贡献比例 + 全体签名单独一页**（课程硬性要求）。

## Coding Agent 使用约定

任务包按「输入 / 输出 / 可改文件 / 验收命令」写清，适合让 Coding Agent 辅助执行。但每人必须：

1. 亲自读一遍 Agent 生成的代码，能在组内解释实现思路与关键取舍；
2. 亲自跑验收命令并保留输出，不把 Agent 的「已完成」当成验证；
3. 在 [`AI_USAGE.md`](AI_USAGE.md) 记录使用过哪些 Agent、用于哪个任务、人工复核了什么；
4. 不把 Agent 生成的数字写进报告，除非来自自己真实运行。

课程要求报告含**每人贡献比例与全体签名**，AI 辅助使用情况也应如实披露。

## 明确禁止

- 另起仓库 / 另写一套 RAG 系统；修改别人任务包的文件而不告知对方。
- 硬编码命中率 / 正确率、伪造运行记录、把 MOCK 输出当实验结果。
- 提交 `.env` / API key / `data/index/` / `eval/results/raw/`。
- 提交没有来源、无法复现或并非来自真实运行的实验数字。
- 未经全组确认产生**付费 LLM API 调用**。

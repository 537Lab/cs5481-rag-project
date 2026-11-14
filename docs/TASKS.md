# T1–T5 五人开发任务卡

> 项目背景、目标、老师要求映射、架构、依赖排期与交付标准统一见
> [`PROJECT_PLAN.md`](PROJECT_PLAN.md)；本文件只放**任务卡**。GitHub Issues #1–#5 与本文件一致。
>
> **状态**：五个任务均未认领；应用领域、技术方案与 LLM 方案仍需五人共同确认。
> 五人地位平等，由本人在对应 Issue 评论认领并设置 Assignee；本文件不预先指定任何人。
> 每人都有**代码 + 自动化测试 + 真实运行验证 + 技术解释 / 实验分析**四项责任。
> 所有人都在同一仓库、同一套 `ragkit` 契约上开发，不另起一套系统；
> 未经对方同意不替别人完成其任务包。

## 已完成的基础（不要重复做）

`CORPUS_V0` 4 篇真实公开授权语料、两种最小 chunker、本地 ONNX embedding、Chroma 持久化与检索、
OpenAI 兼容 LLM 客户端、引用结构校验与拒答、`eval/evidence.py` 共同证据标准、
离线测试（57 passed / 2 skipped，见 `RUNLOG.md`）、GitHub Actions CI。
**没有**正式语料、≥20 组 QA、chunking 对比实验、任何正式指标或真实 LLM 回答。

## 共同契约（Day 1 冻结，改动需 ≥2 人同意）

- `ragkit/contracts.py` 的 `Document / Chunk / RetrievedChunk / Answer` 字段与四个 `Protocol`；
- 不变式 `doc.text[chunk.char_start:chunk.char_end] == chunk.text`；
- `eval/evidence.py` 的 gold 标准 = `evidence_doc_id` + `evidence_quote` → 原始文档字符区间，
  **不用 chunk id**；
- `PROJECT_PLAN.md` §6.1 的 I1–I5 五个数据 / 接口契约（语料快照、`qa_set.csv` schema、
  `eval/metrics.py` 函数签名、答案产物 `jsonl`、实验配置 schema）。

**单一职责（避免重复计算与职责重叠）**：指标定义与聚合只属于 T4 的 `eval/metrics.py`；
chunking 对比实验只属于 T2；检索诊断只属于 T3；拒答行为与引用生成只属于 T5；
回答正确性判定与 judge 协议只属于 T4。详见 `PROJECT_PLAN.md` §5.1。

---

## T1 正式知识库与文档处理

| 项 | 内容 |
| --- | --- |
| **任务意义** | 没有一份真实、许可明确、可复现、带出处的固定文档集，后面四个任务的检索、引用和评测都无从谈起。这是 R1a / R1b 与所有正式实验的输入。 |
| **要开发什么** | ① 按全组确认的领域采集并清洗正式语料（建议 10–20 篇，含不同长度与结构）；② `ragkit/loaders.py` 增加 UTF-8 校验、去重、空文件处理，并把 `source_uri` / `license` 从可选改为必填；③ `scripts/fetch_corpus.py` 支持按固定版本 / tag 复现抓取；④ 生成 `data/raw/frozen_manifest.json`（`corpus_id`、生成时间、每篇 `sha256`）与 `docs/CORPUS.md` 统计说明。 |
| **输入** | 全组确认的应用领域与文档清单；现有 `data/raw/`、`SOURCES.md`、`manifest.json`、`scripts/fetch_corpus.py`。 |
| **输出** | 正式语料快照（纯文本 + `manifest.json` + `SOURCES.md` + `frozen_manifest.json`）、强化后的 `loaders.py`、可复现采集脚本、`docs/CORPUS.md`。 |
| **可修改文件** | `ragkit/loaders.py`、`data/raw/**`、`scripts/fetch_corpus.py`、`tests/test_loaders.py`、`docs/CORPUS.md`。 |
| **依赖** | 上游：无代码依赖，但须等全组确认 C1 / C2（`PROJECT_PLAN.md` §1.9）。下游：T4 的 gold 引文必须逐字出自本任务冻结的快照（I1），见 `PROJECT_PLAN.md` §6.2 的 time-box 与 fallback。 |
| **测试方法** | `python -m pytest tests/test_loaders.py -q`；`python -m pytest -q`；`ruff check .`；`python -m ragkit.cli ingest` 在冻结语料上真实跑一次；逐条打开 `source_uri` 核对许可。 |
| **完成标准** | ≥10 篇真实文档、逐篇出处与许可可打开、零 MOCK 混入、`CORPUS_V0` 四篇 doc_id 与文本未改、编码/去重/空文件/出处必填均有测试、字符偏移不变式成立、`frozen_manifest.json` 可复现校验、`docs/CORPUS.md` 给出规模与长度分布的描述性统计。 |
| **实验分析与技术解释** | 说明文档类型、长度、结构噪声对后续检索的影响（描述性，不编造指标）；能解释为什么选这个版本、如何复现抓取、为什么 `source_uri` / `license` 必须随文档传递。 |
| **演示成果** | 语料表（篇数 / 版本 / 许可 / URL）、清洗前后对比、一次真实 `ingest` 输出。 |

## T2 Chunking 策略与对比实验

| 项 | 内容 |
| --- | --- |
| **任务意义** | R1d 明文要求比较 ≥2 种分块策略并报告对检索质量的影响；这是本项目唯一的"策略对比实验"，也是报告 experiments 的主线。 |
| **要开发什么** | ① `ragkit/chunking.py` 策略参数化（size / overlap / 策略名）与稳定元数据，保证两种策略的 `overlap` 语义一致；② `eval/chunking_experiment.py`：对每种策略分别建索引、跑同一份 QA、**调用 T4 的 `eval/metrics.py`** 汇总，输出可复现结果；③ `docs/CHUNKING_EXPERIMENT.md` 实验报告。 |
| **输入** | 开发期：`CORPUS_V0` + `Chunk` 契约 + `eval/evidence.py` + `qa_template.csv` 格式示例。正式实验：I1 冻结语料 + I2 冻结 `qa_set.csv` + I3 `metrics.py` 函数。 |
| **输出** | `chunking.py`、`eval/chunking_experiment.py`、`docs/CHUNKING_EXPERIMENT.md`、`eval/results/summary/chunking_comparison/` 下真实汇总结果。 |
| **可修改文件** | `ragkit/chunking.py`、`tests/test_chunking.py`、`eval/chunking_experiment.py`、`docs/CHUNKING_EXPERIMENT.md`、`eval/results/summary/chunking_comparison/**`。 |
| **依赖** | 代码与自测不等待任何人（用 `CORPUS_V0` + `Chunk` 契约）；正式对比数字依赖 I1 冻结语料、I2 冻结 QA 与 I3 指标实现。**不自己实现 hit@k**。 |
| **测试方法** | `python -m pytest tests/test_chunking.py -q`；`python -m pytest -q`；`ruff check .`；`python -m eval.chunking_experiment --help`；Day 5 真实跑一次完整对比并保存输出。 |
| **完成标准** | ≥2 种策略在同一 gold、同一 `top_k`、同一 `min_coverage`、同一 embedding / LLM 下可比；报告 chunk 数、长度分布、hit@1 / hit@3；每个数字来自真实运行并附命令 / 配置 / 日期 / 快照 id；无硬编码；命中率一律调用 `eval/metrics.py`。 |
| **实验分析与技术解释** | 解释策略差异为何影响检索质量，附至少 2 个失败案例；能解释为什么 gold 用原文字符区间而不是 chunk id。 |
| **演示成果** | 策略对比表 + 图 + 一个"某策略命中 / 另一策略漏掉"的具体案例。 |

## T3 检索层与向量库

| 项 | 内容 |
| --- | --- |
| **任务意义** | R2 / R3 要求把 chunk 与向量存进向量库、把问题转向量做语义检索；本任务让检索质量**可观测、可复现**，并保证不同 chunking 策略的索引不互相污染。 |
| **要开发什么** | ① `ragkit/store.py` / `ragkit/embeddings.py` 增强：按策略隔离 collection、写清 `score = 1 - cosine_distance` 语义、重开客户端 roundtrip、可选阈值行为（不调参）；② `eval/retrieval_diagnostics.py`：score 分布、gold 证据在 top-k 中的排名、检索失败原因、索引 roundtrip 检查；③ `docs/RETRIEVAL.md`。 |
| **输入** | `CORPUS_V0` / 冻结语料、`Chunk` 契约、本地 ONNX embedding、I2 `qa_set.csv`、I3 的 `is_retrieval_hit()` 等共享判据。 |
| **输出** | 强化后的 `store.py` / `embeddings.py`、`eval/retrieval_diagnostics.py`、`docs/RETRIEVAL.md`、诊断结果（标注正式 / 开发用）。 |
| **可修改文件** | `ragkit/store.py`、`ragkit/embeddings.py`、`tests/test_store.py`、`tests/test_embeddings.py`、`eval/retrieval_diagnostics.py`、`docs/RETRIEVAL.md`。 |
| **依赖** | `Chunk` 契约已冻结，代码与自测可立即并行；正式诊断数字依赖 I1 / I2 冻结输入。**不定义、不发布正式命中率**（正式数字由 T4 汇总）。 |
| **测试方法** | `python -m pytest tests/test_store.py tests/test_embeddings.py -q`；`python -m pytest -q`；`ruff check .`；`python -m ragkit.cli retrieve "..." --top-k 3` 真实运行；重开客户端验证持久化。 |
| **完成标准** | 不同策略索引不混、无需 API key 可跑、`get_chunk()` 出处 roundtrip 完整、score 语义写进文档、给出 top_k 与失败案例分析、诊断脚本可被 T2 / T4 调用。 |
| **实验分析与技术解释** | score 分布、检索失败原因、是否值得加关键词检索（讨论即可，不实现）；能解释稠密向量检索 vs BM25 关键词检索的取舍与局限。 |
| **演示成果** | 一条真实 top-k 检索输出（带出处 / 字符区间）+ score 分布图 + 失败案例。 |

## T4 评测集与唯一指标实现

| 项 | 内容 |
| --- | --- |
| **任务意义** | R5 明文要求 ≥20 组 QA 与两个指标；本任务同时是**全组唯一的指标中台**，避免 T2 / T3 / T5 各自算一遍命中率或正确率。 |
| **要开发什么** | ① `eval/qa_set.csv`（≥20 组，含 answerable / unanswerable，gold 为原文逐字引文）；② `eval/metrics.py`——**唯一**的 `retrieval_hit_rate()` / `answer_correctness()` / `abstention_rates()` / `citation_structure_rate()` 实现，Day 1 先合入可 import 的骨架；③ `eval/judge_protocol.md`（人工 judge 口径、两人独立评分与一致性）；④ `tests/test_eval_metrics.py`；⑤ 按 I4 读取 T5 的答案产物，产出正式汇总。 |
| **输入** | I1 冻结语料（gold 引文的唯一来源）、`eval/evidence.py`、`eval/qa_template.csv`、I4 答案产物 `eval/answers/<run_id>.jsonl`、`Answer` 契约。 |
| **输出** | `eval/qa_set.csv`、`eval/metrics.py`、`eval/judge_protocol.md`、`tests/test_eval_metrics.py`、正式指标汇总（写入 `eval/results/summary/`）。 |
| **可修改文件** | `eval/qa_set.csv`、`eval/metrics.py`、`eval/judge_protocol.md`、`tests/test_eval_metrics.py`、`eval/README.md`、`eval/results/summary/**`。 |
| **依赖** | `Answer` 契约已冻结，代码与单测可立即用 MOCK `Answer` 开发；正式 gold 引文依赖 I1 冻结语料（见 `PROJECT_PLAN.md` §6.2 的 time-box 与 fallback）；正式正确率依赖 I4 答案产物与 C4 judge 方案。**不修改 `generation.py` 的拒答逻辑，不另造临时 gold 文件。** |
| **测试方法** | `python -m pytest tests/test_eval_evidence.py tests/test_eval_metrics.py -q`；`python -m pytest -q`；`ruff check .`；`python -m eval.metrics --help`；对 `qa_set.csv` 每一行运行 `locate_evidence()` 全部通过；用 MOCK 答案验证四个指标的边界条件（空集、全拒答、编造引用）。 |
| **完成标准** | ≥20 组 QA、每条 gold quote 通过 `locate_evidence()`；命中率用 `is_retrieval_hit()`；正确率由人工 judge 并披露评分者一致性；正确拒答率与误拒答率可算；引用结构校验与事实正确性在命名和文档中明确区分；无任何硬编码结果；`metrics.py` 是唯一实现。 |
| **实验分析与技术解释** | QA 覆盖度、拒答题比例、评分者一致性、指标局限；能解释为什么结构校验不能当正确率、为什么不同策略必须用同一份 QA。 |
| **演示成果** | QA 表节选 + 指标表（命中率 / 正确率 / 拒答）+ judge 协议摘要。 |

## T5 LLM 问答、引用支持性与可运行演示

| 项 | 内容 |
| --- | --- |
| **任务意义** | R4 要求把问题与检索片段交给 LLM、只用上下文作答、逐论断引用、无答案时明确拒答；本任务同时产出课堂展示要用的可运行系统与全组评测所需的答案产物。 |
| **要开发什么** | ① `ragkit/generation.py` 增强：逐论断引用覆盖检查、拒答策略说明、三层概念在 CLI 中的清晰呈现；② `ragkit/cli.py` 增加批量答案导出（按 I4 写 `eval/answers/<run_id>.jsonl`）；③ `demo/` 一键演示脚本；④ `docs/ANSWER_QUALITY.md`（定性失败案例）。 |
| **输入** | 检索结果、`Answer` 契约、LLM API 配置（**付费调用须全组先确认 C3**）、I2 `qa_set.csv`、I4 产物 schema。 |
| **输出** | 强化后的 `generation.py` / `cli.py`、`eval/answers/<run_id>.jsonl`、`demo/`、`docs/ANSWER_QUALITY.md`。 |
| **可修改文件** | `ragkit/generation.py`、`ragkit/cli.py`、`tests/test_generation.py`、`eval/answers/**`（汇总产物）、`demo/**`、`docs/ANSWER_QUALITY.md`。 |
| **依赖** | `Answer` 与检索契约已冻结，代码与自测可立即用 MOCK / fixtures 并行；真实 `cli ask` 与零上下文消融依赖 C3 全组批准的 API 方案；正式评估依赖 I2 冻结 QA。**不计算回答正确率或拒答率**（由 T4 判定）。 |
| **测试方法** | `python -m pytest tests/test_generation.py -q`；`python -m pytest -q`；`ruff check .`；`python -m ragkit.cli offline-demo`（MOCK）；验证导出的 `jsonl` 能被 T4 的 `metrics.py` 读取；真实 `cli ask` 仅在 C3 确认后执行。 |
| **完成标准** | 真实回答带逐字可回查引用；引用 ID 有效 / 引文逐字 / 内容支持回答三层清晰区分；拒答可评估；答案产物符合 I4；`demo` 一键可复现；不产生未授权付费调用；不把结构校验宣称为事实正确性。 |
| **实验分析与技术解释** | 定性分析幻觉、错误引用、过度拒答等失败案例；能解释四道拒答门与为什么"引用有效"不等于"答案正确"。 |
| **演示成果** | 现场跑一条真实问答（带引用回查）+ 一条拒答 + 一键 demo；若 C3 未批准，演示用 `offline-demo` 并明确标注 MOCK。 |

---

## 依赖、并行与每日集成

```
Day 1：共同冻结 contracts.py / evidence.py / I1–I5
        ├──► T1 采集与 loaders 强化 ──┐
        ├──► T2 chunker + 实验骨架     │
        ├──► T3 store + 诊断脚本       ├─ 每日小 PR + 集成自检
        ├──► T4 metrics.py 骨架 + QA   │
        └──► T5 generation + 答案导出  ┘
Day 2：T1 冻结正式语料快照（或启用 PROJECT_PLAN.md §6.2 fallback）
Day 3：T4 冻结 qa_set.csv；T5 产出答案产物
Day 4：五模块联合 dry run（开发数据，标注非正式）
Day 5：同一语料 + 同一 QA + 同一参数跑正式实验（E1–E4）
Day 6–7：报告、slides、贡献比例 + 全体签名单独一页
```

- **可以立即并行的**：五个任务的代码、单测与开发期运行验证（基于 `CORPUS_V0`、
  `tests/fixtures/`、`qa_template.csv` 格式示例）。
- **必须等待共同数据 / 接口的**：正式 gold 引文 ← I1 语料快照；正式指标数字 ← I3 `metrics.py`
  + I2 冻结 QA；正式正确率 ← I4 答案产物 + judge；真实 LLM 问答 ← C3。
- **每日集成**：每人每天至少一个可合并的小 PR（薄片优先），每天开工 rebase `main`；
  由当天提交 PR 的人跑 `PROJECT_PLAN.md` §6.4 的集成自检清单并把输出贴到 PR / `DEV_LOG.md`；
  接口变更当天在 PR 中通知其余四人。
- **冻结规则**：`CORPUS_V0` / 正式语料快照 / `eval/qa_set.csv` 的冻结时点与约束
  统一见 `PROJECT_PLAN.md` §6.6；开发期输出标注「开发用」，不得称为正式实验结果。

## Coding Agent 使用约定

任务卡按「输入 / 输出 / 可改文件 / 测试 / 验收」写清，适合让 Coding Agent 辅助执行。每人必须：
① 亲自读一遍生成的代码，能在组内解释实现与取舍；② 亲自跑验收命令并保留输出；
③ 在 [`AI_USAGE.md`](AI_USAGE.md) 登记用了哪个 Agent、用于哪个任务、人工复核了什么；
④ 不把 Agent 生成的数字写进报告，除非来自自己真实运行。
课程要求报告含**每人贡献比例与全体签名**，AI 辅助使用情况也应如实披露。

## 明确禁止

- 另起仓库 / 另写一套 RAG 系统；未经告知修改别人任务包的文件。
- 自己再实现一份 hit@k / 正确率 / 拒答率；把结构校验率称作回答正确率。
- 硬编码指标、伪造运行记录、把 MOCK 输出当实验结果、新建所谓「临时 gold」。
- 提交 `.env` / API key / `data/index/` / `eval/results/raw/`。
- 未经全组确认产生**付费 LLM API 调用**。

# T3 检索层与向量库 / Retrieval and vector storage

> **状态更新 / Update（2026-11-21 HKT，GitHub 状态核查）**：PR #14 的 Kubernetes v1.35 冻结语料已合入 `main`（12 个来源页面、16 个清洗文档），因此下方 2026-11-18 所说“尚无 I1 冻结文件”是**当时的历史状态**，不是当前阻塞。此文第 6–8 节的 4 文档／35QA 数据、示例 score、排名和旧快照哈希均仅对应 `CORPUS_V0` 开发实验，**不得标成冻结 Kubernetes 重跑结果**。PR #15 的正式 QA 及 KN01–KN10 人工复核尚未完成；本次同步尚**未**在新语料上实跑 diagnostics，新数据与输出哈希均待真实执行后补入。CI/pytest 不能代替 ONNX 实验，也不能代替学生本人复核。
>
> **复跑提示（尚未执行）**：先在冻结语料对应的 `main` 环境重建索引：`python -m ragkit.cli ingest`，然后根据当前真实 QA 版本分别选择开发或正式输入运行 `python -m eval.retrieval_diagnostics --qa eval/qa_set.csv --strategy fixed --top-k 3 --min-coverage 0.5 --output-dir eval/results/raw/t3-k8s-fixed-<run-id>`；每次使用新的输出目录，核对报告中的 `corpus_snapshot_sha256`、`qa_sha256`、collection 实际 count、retrieval 和 provenance checks。完成前不要宣称已重跑或通过正式评测。


> **状态 / Status（2026-11-18，HKT）**：T3 的代码与开发期真实检索已实现；本文记录的是 **DEVELOPMENT / REAL_LOCAL**，不是正式评测。语料是 `CORPUS_V0` 的 4 篇文章，QA 是 T4 已合入的 35 题开发集。I1 正式冻结文件尚不存在；不能把这些观察写成正式实验结果。`offline-demo` 和确定性测试替身则是 **MOCK**，另行标识。
>
> **English summary:** T3 hardens Chroma collection isolation, cosine-score semantics, lossless chunk roundtrips and embedding validation. The reusable diagnostic CLI records actual local retrieval, deep gold-evidence ranks, integrity checks and descriptive score distributions. It defines no hit-rate, correctness or abstention metric. Formal evaluation and human review remain team responsibilities.

## 1. T3 在系统中做什么 / Role in the pipeline

```text
T1 原文与出处 → T2 分块 → T3 embedding → T3 Chroma → 带出处的检索结果 → T5 生成
                                   ↓                 ↓
                               get_chunk 回查    T3 逐题诊断 → T4 唯一指标实现
```

- **向量化 / embedding**：把一段文字转成定长的数字列表，语义接近的文字通常方向接近。本地模型是 Chroma 自带的 `all-MiniLM-L6-v2`，384 维，无需 API key；首次使用可能下载免费模型，之后本地推理。
- **Chroma**：嵌入式向量数据库，同时保存向量、原文与出处，不需要启动数据库服务器。与简单的 Python 列表不同，程序退出后数据仍在磁盘上。
- **Collection**：数据库内的独立集合。`chunks_fixed` 和 `chunks_paragraph` 像两个独立抽屉；同一个 `doc#0000` 可以分别表示两种切法，不能拿它们当同一个块。
- **余弦相似度 / cosine similarity**：比较向量方向，而非它们的长度。这里的分数是相似程度，不是“答案正确的概率”。

T3 不写 prompt、不生成答案、不修改 gold、不实现第二套指标，也不接管 T2 的策略对比实验。

## 2. 实现与兼容边界 / Implementation

### 存储：`ragkit/store.py`

保留原来的 `upsert/search/get_chunk/count/clear` 和 `build_store(settings)` 调用方式；构造器只增加可选的 keyword-only `strategy`，未修改共享 `VectorStore` 契约。

1. 标准 collection 名称推导策略，`build_store` 显式传入设置中的策略；批次混用或与 collection 不符时拒写。自定义名称仍可用，绑定到单一策略。重开时检查已有记录；策略未知或混杂的旧集合可读，但拒绝继续追加，要求显式重建。
2. 检查 Chroma 实际 collection 配置必须为 cosine，已有 L2 等其他空间的库会报错，不把其他距离误标成 cosine，也不偷偷改旧库。
3. 一次 upsert 前检查数量、重复 ID、非空向量、统一维度、有限数值及零范数；重开后仍从已存向量确认维度。相同 ID 的合法再次写入更新记录，不增加重复条目。
4. 全部 `Chunk` 字段往返保留；`Chunk.meta` 额外存为 JSON 字符串，保留嵌套元数据，同时兼容原来的标量 metadata。无法无损 JSON 序列化的内容明确拒绝，不静默删字段。旧记录缺失的出处不会被宣称为已验证。
5. `clear()` 只删除并重建当前 collection，不重置整个 Chroma 客户端。
6. 首轮独立审查发现“两个预先打开的自定义客户端交错写入”可绕过旧的内存绑定；修复后 constructor/upsert/clear 使用 collection 专属文件锁，并在锁内重新读取当前策略和维度，避免本地协作写入者互相污染。它不是分布式锁，绕过 `ChromaStore` 直接写库不在保护范围内；Windows 分支尚未实测。
7. 写入和查询均先按最大绝对值缩放、再做稳定单位归一化，避免极小/极大有限向量在 float32 cosine 中下溢、溢出或生成 NaN。归一化不改变余弦方向，异常后端距离会被拒绝，而不是继续传播成合法分数。已有污染向量不会自动修复，须重建。

**维度保护不等于模型身份保护**：384 维索引与另一个不同维度的查询会被拒绝，但两个不同模型如果恰好同维，单凭维度无法识别。换 embedding 模型必须重建索引，不能混用。

### 向量化：`ragkit/embeddings.py`

- 空批次返回 `[]`，不加载模型、不调用 API；单条空白文本、把整个字符串误当字符串列表等输入明确报错。
- 本地模型检查配置名称与固定 384 维；验证每条输出的数量、维度、数值类型、有限性和非零范数，而不是只看第一条。
- API 路径保留，但测试只用 MOCK client。真实 API 返回先校验 `index` 恰好是唯一整数 `0..N-1`，再按输入顺序恢复；重复、缺失、越界、布尔值或小数 index 均拒绝。
- 未知 provider 不会默默落入 API 分支。诊断 CLI 更严格：**只允许 local**，即使配置写了 `api` 也在创建客户端前拒绝。

## 3. Score、rank、top-k 和阈值 / Search semantics

```text
score = 1 - cosine_distance
```

- 理论 cosine 范围是 `[-1, 1]`，数值计算可能有微小越界；不裁剪成 `[0,1]`。相同方向约为 1，正交约为 0，相反方向约为 -1。
- 分数越大越相似；结果按 score 降序，排序后重新标记从 1 开始的 `rank`。相同分数的先后保留数据库返回次序，不承诺跨版本完全相同的 tie-break。
- `ChromaStore.search(vector, k)`：`k <= 0` 或空集合返回空；大于集合大小时封顶为集合大小。空集合不需要一个有效查询向量。
- 诊断的 `top_k=0` 明确表示空 top-k，但仍可查询更深排名；负值不接受。
- 诊断不做 score 阈值过滤，避免把“有结果但被阈值删掉”和“数据库没找到”混为一谈；记录 `pipeline_min_score` 与 `threshold_applied=false`。

**已核实但未越界修的共享层问题：**

1. `contracts.py` 的 score 字段旧注释写 `[0,1]`，与实际 cosine 定义不符；T3 保留真实负分，建议共享契约负责人纠正注释，不改变字段。
2. `pipeline.retrieve()` 用 `k or settings.top_k`，所以显式 `k=0` 会回退默认值；它还始终执行 `score >= min_score`，因此 `min_score=0.0` 实际会过滤负分，并非注释所说完全关闭。这两个行为应由共享层负责人另行修复。本文诊断直接用现有 embedder + store，不改 pipeline，也不把 raw ranking 冒充阈值后的管线输出。

## 4. 可复用诊断模块 / Diagnostic API and CLI

主入口：

```python
from eval.retrieval_diagnostics import diagnose_retrieval

report = diagnose_retrieval(
    items, documents, expected_chunks, embedder, store,
    strategy="fixed", collection="chunks_fixed",
    top_k=3, min_coverage=0.5,
)
```

`items` 用 T4 的 `QAItem`；预期 chunks 必须由当前 T2 chunker 从相同输入生成，不能自己再写一套切块算法。调用者负责 embedding 的授权；内置 CLI 不允许 API。函数不生成答案、不修改索引。

其他可导入入口：`audit_index()`、`score_distribution()`、`write_outputs()`、`build_parser()`、`main(argv)`。输出是可序列化字典，schema 版本为 1；每题含 qid、question、策略、collection、gold 字符范围、top-k 实际记录和更深的 evidence candidates。每条记录保存文本、score、rank、出处、许可、区间、source 检查和 `get_chunk()` roundtrip 结果。

默认请求整个 collection 的实际排名，而非看完前三条就宣布 gold 不存在。`requested_depth / searched_count / ranking_complete` 分开记录请求与实际返回范围；更深搜索仍未提供证据时，不捏造排名。全索引较大时这个设计会比较慢，当前适用于课程规模的批量诊断，不是在线查询接口。诊断时应固定输入并避免其他进程重建索引；本工具不提供跨多个读取请求的数据库快照事务。

CLI（先运行 `ingest` 建好对应 collection）：

```bash
python -m eval.retrieval_diagnostics --help
python -m eval.retrieval_diagnostics \
  --qa eval/qa_set.csv --strategy fixed --top-k 3 --min-coverage 0.5 \
  --output-dir eval/results/raw/t3-20261118-fixed-final
```

支持 `--config`（或 `RAGKIT_CONFIG`）、`--qa`、`--strategy`、`--top-k`、`--min-coverage`、`--output-dir`、显式 `--overwrite`。已有输出默认拒绝覆盖，而且在重复模型计算前检查。不会自动 ingest、清空索引、下载另一套语料或换收费 provider。

输出四件套，默认都留在 gitignored 的 `eval/results/raw/`：

| 文件 | 用途 |
| --- | --- |
| `diagnostics.json` | 参数、输入和代码 SHA256、包版本、UTC 日期、真实命令、逐题排名与完整性证据 |
| `retrieved.csv` | top-k 逐条文本、出处、分数与区间，方便 T2/T4 检查 |
| `score_histogram.svg` | stdlib 生成的可复现分布图，无新增绘图库 |
| `run.md` | 命令、输入快照指纹、结果文件说明 |

指纹包括 manifest 字节、QA CSV 字节、按 doc_id 排序的已加载原文及出处摘要，以及实际参与运行的各 Python 源文件；`git_commit` 只是补充，不能掩盖当时的未提交源码。快照 SHA256 是内容身份，**不是全组批准的正式冻结 ID**。`frozen_manifest_present` 也只表示文件是否存在，不表示已通过 I1/I2 审核。目前 CLI 始终标 DEVELOPMENT，不提供绕过人工关口的 `--formal`。

## 5. 如何谨慎区分失败 / Evidence-based classification

所有命中判断直接调用共享 `locate_evidence()`、`evidence_coverage()`、`is_retrieval_hit()`；T3 不聚合 hit@k。

| diagnosis | 可支持的结论 |
| --- | --- |
| `hit` | 当前 top-k 至少有一块满足共享 gold 覆盖判据，不代表答案生成正确 |
| `ranking_below_top_k` | 真实更深排名已找到满足判据的块，但不在本次 top-k |
| `chunk_boundary_fragmentation` | 预期索引完整、gold 区间并集完整，但没有单个块达到覆盖阈值 |
| `chunk_coverage_gap` | 当前完整分块输出本身没有覆盖 gold 的全部区间，不能直接说成排名问题 |
| `index_incomplete_or_mismatched` | 预期块缺失、内容/元数据不符或存在额外记录，优先检查索引与配置 |
| `roundtrip_or_provenance_error` | 实际查询结果回查不一致，或不符合原文切片/出处；不把损坏的区间当有效命中 |
| `unknown_gold_unlocated` | gold 无法定位；可能是 QA/语料版本错配，**不能因此断言语料无答案** |
| `unknown_needs_review` | 证据不足，保留人工排查 |
| `unanswerable_label` | 独立保留 T4 标签和人工复核状态，不进入普通检索失败分析 |

并集覆盖只是定位分块问题的描述量，不是另一套命中率。比如三块各覆盖 gold 的三分之一，即使合起来完整，按共享“单块 ≥50%”标准仍未命中，不能私自将它改成成功。8 条 unanswerable 的 `REVIEWED_BY` 当前为空；近邻分数高不等于题目可回答，缺少某个词也不证明全文没有答案，需 T4 规定的人工判断。

## 6. 真实运行证据 / DEVELOPMENT observations

本轮起点 `main`：`4f865c10232f8d7890e9e1c019569276bcb9638e`（已合入 PR #7/#8，核查时 #10 未合并）。独立分支 `t3-retrieval-diagnostics`。验证环境：Python 3.14.6、Chroma 1.5.9、ONNX Runtime 1.32.0、NumPy 2.5.5、OpenAI SDK 1.109.1；项目依赖文件未改。

2026-11-18 HKT 实跑：

- `python -m ragkit.cli ingest`：4 文档 → fixed 28 块。
- `python -m ragkit.cli retrieve "What is retrieval-augmented generation?" --top-k 3`：真实本地检索，无 API key。
- 35 题诊断：预期 28 / 实际 28，缺块、元数据错配、额外记录均为 0；105 条 top-k 记录全部通过 roundtrip 和原文出处检查。
- 独立的真实存储检查：paragraph 33 块；两种策略有 28 个同名 ID，分别回查仍是各自策略；重复 upsert 不增条目；clear paragraph 后 fixed 内容逐字段不变。
- 使用**另一个 Python 进程**打开磁盘库，fixed 28 与 paragraph 33 块全部逐字段往返一致；这不只是同进程创建第二个客户端对象。

真实 top-3 示例（来源均为 [Retrieval-augmented generation, Wikipedia](https://en.wikipedia.org/wiki/Retrieval-augmented_generation)，许可 `CC BY-SA 4.0`）：

| rank | chunk_id | score（展示四位） | 原文字符区间 `[start,end)` |
| ---: | --- | ---: | --- |
| 1 | `rag_wikipedia#0006` | 0.6146 | `[3101,3701)` |
| 2 | `rag_wikipedia#0000` | 0.6006 | `[0,598)` |
| 3 | `rag_wikipedia#0003` | 0.5792 | `[1547,2143)` |

第二块包含 “Retrieval-augmented generation (RAG) is a technique that enables large language models (LLMs) to retrieve and incorporate new information from external data sources.”。返回顺序只说明模型的相似度，不保证人类最想看的定义句排第一。

输入指纹（完整值可在 JSON 中重核）：

```text
corpus_snapshot_sha256 = b8a3e8d42e8fcd42be4445415fd95c3e419b8cdd9d2515400913ccd740db80b3
qa_sha256              = d0aff5ea5837a7b7686ce05c69fd24429913912514c020e1fa33a10901bfa46c
```

## 7. Score 分布为什么不能当正确率 / Score distribution

下面是同一轮真实 top-k 观察的描述统计。supporting 仅表示达到单块 gold 覆盖判据，不是“支持了生成答案”的人工判断。n 是结果条数，不是问题通过率的分母。

| Group | n | min | max | mean | median |
| --- | ---: | ---: | ---: | ---: | ---: |
| all_top_k | 105 | 0.163301 | 0.833785 | 0.444987 | 0.431201 |
| answerable_other | 58 | 0.193355 | 0.665279 | 0.462644 | 0.455218 |
| answerable_supporting | 23 | 0.344951 | 0.833785 | 0.537378 | 0.542198 |
| unanswerable_label | 24 | 0.163301 | 0.520798 | 0.313775 | 0.320967 |

图在运行输出目录的 `score_histogram.svg`；固定 10 个区间覆盖 `[-1,1]`，左闭右开，最后一格包含 1，浮点越界另列计数，不裁剪原始分数。用向量替身的测试也验证负分保留。

**为什么阈值难分对错？** 达标证据分数最低 0.344951，而未覆盖指定 gold 的结果最高 0.665279，分布明显重叠。拉高阈值会删掉一部分有效证据，留下的高分也未必含指定答案。这里没有进行阈值搜索，更没有为改善某个结果改正式参数。

## 8. 本轮失败案例与边界 / Failure analysis

以下均来自当前 QA 和本轮真实深度检索，不是复制旧 RUNLOG。

| qid | gold 文档区间 | 第一个达标块与真实 rank | score |
| --- | --- | --- | ---: |
| A03 | `rag_wikipedia [580,689)` | `rag_wikipedia#0001`，rank 6，覆盖 1.0 | 0.358756 |
| A14 | `vector_db_wikipedia [1170,1263)` | `vector_db_wikipedia#0002`，rank 4，覆盖 1.0 | 0.349727 |
| A17 | `vector_db_wikipedia [2905,3040)` | `vector_db_wikipedia#0005`，rank 8，覆盖 1.0 | 0.313522 |
| A18 | `vector_db_wikipedia [3041,3221)` | `vector_db_wikipedia#0005`，rank 5，覆盖 0.766667 | 0.460944 |

### A03：指定 gold 排第六，不等于上下文完全没有答案

问题问 RAG 最初何时提出。指定 gold 是 “The technique was first proposed in 2020 ...” 所在区间，完整块在第 6 名；top-3 中 `#0000` 只覆盖该 gold 的 0.165138，未达到 0.5。**因此按共享 gold 判据，本轮是排序失败。**

但 top-1 的 `rag_wikipedia#0003` 实际也写着 “The term retrieval-augmented generation (RAG) was introduced in a 2020 paper ...”。这是另一个位置的相关依据。它提醒我们：当前单一 gold span 可能漏记等价证据；T3 不能擅自改 gold 或宣布生成失败，应把候选等价证据交给 T4 人工讨论。没有真实 LLM 调用，不能据此声称“最终答案答错”。

### A17：证据完整，词义相近仍不保证细节排在前三

问题明确问“用户 prompt 转为向量后怎样查询”；原文 `[2905,3040)` 在 `vector_db_wikipedia#0005` 完整存在，真实 rank 8、score 0.313522。索引审计与 roundtrip 正常，所以“没入库”不是本轮原因。**可确认的是排名落后；**可能是其他 RAG 概述块的整体语义更相近，但没有模型内部归因证据，不能把这个推测写成已证实机制。

把 k 增到 8 能把这个指定证据带入候选，这是由已观察排名得出的结论，不是新跑的正式策略实验；代价是更多上下文、检索与后续生成成本、重复或干扰片段。

### A18：引文跨边界，但本轮不应误判为“纯边界失败”

Gold `[3041,3221)` 被两个块覆盖：`#0005 [2584,3179)` 覆盖 76.67%，rank 5；`#0006 [3099,3246)` 覆盖 67.78%，rank 27。两个块各自都不含完整引文，说明边界确实切断了句子；但在本轮共享 `min_coverage=0.5` 下，它们各自都已达标。top-3 没有它们，所以应归为**排序失败**，不是“再增 k 也无法命中”的边界失败。

k=5 可带回当前判据下的合格证据，但不能凭空把整句合进一个 chunk。真正“每块都低于阈值、并集完整”的情况由离线确定性测试覆盖；本轮没有把合成例子冒充真实 QA 失败。旧 T4 报告的 A18 定性不用于替代当前证据。

## 9. 稠密检索与 BM25 / Future trade-offs

- 稠密向量擅长同义表达、概念相近的问题；局限是对年份、数值、罕见术语、版本/字段名等精确线索未必敏感，相似度高也可能只是在讲同一主题。
- BM25 是按词项匹配并考虑词频和文档长度的关键词排序，适合明确标识符、命令和专名；但同义改写没有共同词时可能漏掉。
- hybrid search 可以合并两路候选，未来值得在正式冻结输入上验证；它会增加索引、排名融合和参数公平性问题。本轮**只讨论，未实现 BM25、reranker 或另一套存储**。

## 10. 干净环境复现与测试 / Reproduction

从仓库根目录运行，Python 3.11+；以下命令不改变提交的 `config.toml` 或依赖文件：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest tests/test_store.py tests/test_embeddings.py -q
python -m pytest tests/test_retrieval_diagnostics.py -q
python -m pytest -q
ruff check .
python -m eval.retrieval_diagnostics --help
python -m ragkit.cli offline-demo
python -m ragkit.cli ingest
python -m ragkit.cli retrieve "What is retrieval-augmented generation?" --top-k 3
python -m eval.retrieval_diagnostics \
  --qa eval/qa_set.csv --strategy fixed --top-k 3 --min-coverage 0.5 \
  --output-dir eval/results/raw/t3-20261118-fixed-final
```

测试默认不下载模型、无需密钥。两个已有真实 E2E 默认 skip，其中一个包含可能收费的 LLM 路径，本轮**未启用**；真实 key-free 运行用上面的 ingest/retrieve/diagnostics 命令另行验证。已有输出时选新目录，只有确定要替换自己的运行才加 `--overwrite`。

可选：用相同生产接口创建 paragraph collection，再用 `--strategy paragraph` 诊断，不改共享配置：

```bash
python -c 'from dataclasses import replace; from ragkit.config import load_settings; from ragkit.pipeline import build_pipeline; print(build_pipeline(replace(load_settings(), chunk_strategy="paragraph")).ingest())'
```

它会**只重建 paragraph collection**，使用真实本地模型。不要在别人的索引目录上未经确认运行。两种策略的正式命中率对比仍交给 T2，并统一调用 T4 指标。

本轮基线：124 passed / 2 skipped，Ruff 通过。首次整合：66 个存储/Embedding 定向测试通过，200 passed / 2 skipped 全回归通过。审查修复后的最终实跑（2026-11-18 04:41 HKT）：存储/Embedding **106 passed**，诊断 **37 passed**，全量 **257 passed / 2 skipped**，`ruff check .` 通过；再次 ingest/retrieve、35 题诊断与独立进程双集合检查全部通过，诊断 JSON 中的源码 SHA256 与运行代码逐一一致。测试覆盖真实 Chroma + MOCK 向量、完整元数据、同 ID 跨集合、重开/clear、负 score/rank、非法向量、Embedding 异常、诊断边界/无证据/不完整库/unanswerable/API 禁用与输出复现。

独立 `gpt-6.1-sol / high` 复审已通过：审稿代理另跑三个受影响测试文件 **143 passed**，未发现阻断逻辑或安全问题，并核对最终真实产物的代码/输入指纹；主控再次确认六个代码/测试文件与审查 SHA256 一致。主控还追加了两个独立 Python 写进程同时启动的真实 Chroma 检查（MOCK 向量、无模型）：恰一方写入、另一方因策略冲突拒绝，第三个进程重开只见一种策略。此项不是 Windows 实测，也不扩大到分布式保证。AI 终审仍不替代组员批准。

首次边界测试曾因漏设替身触发免费 ONNX 下载，随后修正并重跑；不宣称整个开发过程从未联网。没有真实调用收费 Embedding API、LLM API 或 LLM judge。

## 11. 交接与仍需人工确认 / Team handoff

| 对接方 | T3 提供什么 | 不替对方决定什么 |
| --- | --- | --- |
| T1 / I1 | 文本/出处/许可/区间保真和内容指纹 | 正式领域、语料收集与冻结批准 |
| T2 | 原有 store/embedder 接口；可导入诊断与深度排名 | 分块实现和正式策略比较 |
| T4 / I2-I3 | 原文 gold 覆盖、逐题诊断与 source/roundtrip 证据 | 等价 gold、正式 hit@k、正确率与拒答率 |
| T5 / I4 | 带来源的 `RetrievedChunk` 与稳定 `get_chunk()` | prompt、答案、引用支持性与拒答行为 |

待办：I1 正式冻结、I2 重校验及 unanswerable 人工复核；共享 pipeline/注释问题交相关负责人；不同组员进行 PR review/Approve，由非作者手动合并。AI 独立审查不等于组员批准。本人仍须读代码、亲自运行关键命令并理解设计，真实记录在 AI_USAGE/DEV_LOG；不能由代理代签贡献比例或声称已完成人工复核。

## 12. 展示时可以讲什么 / Presentation outline

五分钟：

1. **问题（约一分钟）**：同一份文章切成两种块，ID 可以相同；不隔离会互相覆盖，丢出处也无法回查引用。
2. **实现（约一分钟）**：本地 384 维向量 → cosine Chroma → score/rank/出处；策略隔离、输入校验、完整元数据往返，不只是让查询“有输出”。
3. **证据（约一分钟）**：现场 retrieve，展示字符区间和 `get_chunk()`；解释两种 collection 的独立进程持久化验证。不要用 MOCK 演示冒充真实结果。
4. **失败（约一分钟）**：A17 的指定证据在第 8 名；A18 引文跨边界但按 50% 判据是第 5 名的排序问题；A03 则暴露单一 gold 可能漏掉等价证据。
5. **取舍（约一分钟）**：高分不等于正确，阈值无法干净区分两类；提高 k 有上下文代价；未来 BM25/hybrid 值得验证但本轮没擅自扩展。

老师可能问：

- **“为什么同一个 chunk_id 不会混？”** 因为 ID 只在 collection 内唯一，策略分集合，并在写入/重开时检查策略，测试还验证 clear 一个集合不影响另一个。
- **“分数 0.6 是 60% 正确吗？”** 不是，它是向量方向的相似度。答案是否正确仍需指定 gold 和 T4 人工判定；结构可回查不等于内容支持答案。
- **“top-k 没找到，是不是语料没有？”** 不能这样推断。先查原文 gold、完整索引和更深实际排名；只有来源和排名证据充分才能分类，其余标 unknown。unanswerable 是需要人审的独立标签。

# 架构与技术设计

本文是**全组共享的技术约定**：数据契约、模块边界、引用与校验机制、技术取舍和基线验收清单。
项目背景、目标、老师要求逐项映射、五个任务、依赖排期与交付标准的**唯一来源**是
[`PROJECT_PLAN.md`](PROJECT_PLAN.md)；本文件不重复这些定义。
协作规则见 [`CONTRIBUTING.md`](../CONTRIBUTING.md)，上手步骤见 [`START_HERE.md`](../START_HERE.md)，
任务卡见 [`TASKS.md`](TASKS.md)。

> 技术取舍仍需五人共同确认；改动本文、`PROJECT_PLAN.md` 或 `ragkit/contracts.py`
> 属于「影响所有人」的变更，需要 ≥2 人 review。

---

## 1. 课程要求的对应关系

老师明文要求、推断的考察重点、自愿增加的质量目标，以及每一项的现有实现 / 剩余工作 /
验收标准 / 展示证据，统一见 [`PROJECT_PLAN.md` §3](PROJECT_PLAN.md)。
本文只保留与架构直接相关的技术取舍，避免形成第二套项目定义。

---

## 2. 技术取舍

| # | 决定 | 选择 | 放弃了什么 / 代价 |
| --- | --- | --- | --- |
| D1 | 依赖与布局 | 扁平 `ragkit/` 包 + `config.toml`（Python 3.11 自带 `tomllib`）+ `.env` 自己读（约 10 行 stdlib） | 放弃 `src/` + pyproject 打包、Poetry/uv、PyYAML/python-dotenv。代价：所有命令必须从仓库根目录运行 |
| D2 | Embedding / LLM | **混合**：本地 ONNX `all-MiniLM-L6-v2`（无需密钥）+ OpenAI 兼容 LLM API（`OPENAI_BASE_URL` 可换供应商） | 放弃"全 API"（每步都要网络和额度）与"全本地 Ollama"（每人装模型，环境难一致）。代价：首次 `ingest` 需下载约 80 MB 模型；LLM 环节仍需密钥 |
| D3 | 真实语料 | 公开授权资料：Wikipedia CC BY-SA 4.0 摘录，附 `SOURCES.md` 署名与链接 | 放弃课程讲义 PDF（版权/不宜公开上传，且要引入 pypdf）。代价：语料与课程无直接关联，后续可扩充 |
| D4 | 向量库 | ChromaDB 嵌入式持久化 | 放弃 pgvector（要起数据库，五人环境难一致）与纯 NumPy（不算"向量数据库"，评分吃亏）。代价：依赖稍重 |
| D5 | 检查与合并 | `ruff` + `pytest` + GitHub Actions（离线、不需要密钥），绿灯 + ≥1 review 才能合并 | 放弃"只本地手工测"的轻流程。代价：PR 要等 CI |
| D6 | 框架 | **不用** LangChain / LlamaIndex | 它们把分块、检索、prompt 塞进一条链，正好掩盖五个模块的边界，也不利于把 methodology 讲清楚 |

以上 6 项是为使五人能立即开工而做的技术选择，需由五人共同复核，不能表述为「全组已确认」。
此后若要改（例如换 pgvector、换全本地模型），必须新开 PR 并说明对每人环境的影响。
架构如何对应 Topic 5 的后端管线与答案保真重点，见 [`PROJECT_PLAN.md` §4](PROJECT_PLAN.md)。

**为什么契约用 `@dataclass` 而不是 dict**：五个人并行开发时，字段名是最容易对不上的地方。把所有跨模块类型集中在 `ragkit/contracts.py`，配合 `Protocol` 接口，任何人不看别人代码也知道自己该返回什么。

---

## 3. 数据契约（`ragkit/contracts.py`，唯一定义处）

数据流严格单向，不允许反向依赖：

```
Document -> Chunk -> (Chunk + vector) -> RetrievedChunk -> Answer
   M1        M2          M3 / M4            M4              M5
```

| 类型 | 字段 | 说明 |
| --- | --- | --- |
| `Document` | `doc_id, title, text, source_uri, license, meta` | M1 产出；出处随文档一路传递 |
| `Chunk` | `chunk_id, doc_id, text, char_start, char_end, strategy, index, title, source_uri, license, meta` | `chunk_id = "{doc_id}#{index:04d}"`；**不变式**：`doc.text[char_start:char_end] == chunk.text` |
| `RetrievedChunk` | `chunk, score, rank` | `score = 1 - cosine_distance`，越大越相关；`rank` 从 1 开始 |
| `Citation` | `chunk_id, doc_id, quote, title, source_uri` | `quote` 必须是该 chunk 原文的逐字片段 |
| `Answer` | `question, answer_text, citations, abstained, model, raw` | `raw` 保留 LLM 原始输出便于排查 |

四个 `Protocol` 接口（实现在各自模块）：`Chunker`、`Embedder`、`VectorStore`、`LLMClient`。

**不变式为什么重要**：`verify_citations()` 用 `quote in chunk.text` 判断引用是否逐字来自来源；`store.get_chunk(chunk_id)` 能重新取回原文。两者共同保证"引用可验证"不是一句空话。

`config.toml` 存**非敏感**参数（路径、chunk 大小、top_k、模型名）；`.env` 只存**密钥**（`OPENAI_API_KEY`、`OPENAI_BASE_URL`）。`config.py` 用 `os.environ.setdefault`，真实 shell 变量优先于 `.env`，CI 行为可预测。

---

## 4. 五个模块的代码边界（一人一文件）

| 模块 | 文件 | 输入 → 输出 | 允许依赖 | 禁止做 | 怎么测 |
| --- | --- | --- | --- | --- | --- |
| **M1 文档接入** | `loaders.py` | `manifest.json` + 原文 → `list[Document]` | stdlib（`json`/`pathlib`） | 分块、embedding、碰数据库 | `pytest tests/test_loaders.py -q`：字段/出处、缺文件、重复 id、空文档、非 list |
| **M2 分块** | `chunking.py` | `Document` + `ChunkConfig` → `list[Chunk]` | **仅 stdlib，纯函数** | 读文件、调模型、网络 | `pytest tests/test_chunking.py -q`：逐字切片不变式、id 稳定、overlap、两种策略不同、空文档、超长段 |
| **M3 向量化** | `embeddings.py` | `list[str]` → `list[list[float]]`（等长、定维） | `chromadb`（本地 ONNX）/ `openai` | 读文件、写库、写 prompt | `pytest tests/test_embeddings.py -q`：契约、空输入、缺 key 报错、provider 校验 |
| **M4 存储检索** | `store.py` | 写：`(Chunk, vector)`；读：查询向量 + k → `list[RetrievedChunk]` | `chromadb` | 计算 embedding、构建 prompt | `pytest tests/test_store.py -q`：真实 Chroma 持久化、重开可读、top_k 排序、出处 roundtrip、clear |
| **M5 生成引用** | `generation.py` | question + `list[RetrievedChunk]` → `Answer` | `openai` + stdlib | 检索、查库、读文件 | `pytest tests/test_generation.py -q`：有效引用、编造引用、无引用、`NO_ANSWER`、空检索、篡改 quote |

共享层：`contracts.py`（全员 PR 才能改）、`config.py`、`pipeline.py`（薄编排，不含业务逻辑）、`cli.py`（命令适配）、`eval/`、`tests/fakes.py`。

**硬规则（防止五个模块重复实现相同功能）**：
- 只有 **M1** 读源文件；
- 只有 **M3** 调 embedding；
- 只有 **M4** 碰向量库；
- 只有 **M5** 调 LLM；
- **M2 是纯函数**，任何模块都不得自己再实现一遍分块。

不同 chunking 策略使用不同 collection（`chunks_{strategy}`），避免两种实验的索引数据混淆。

---

## 5. 引用与拒答机制

`AnswerGenerator.generate()` 有四道门：

1. Prompt 明令"只用 CONTEXT、每条论断附 `[chunk_id]`、只能引用给出的 id、不足则输出 `NO_ANSWER`"。
2. `retrieved` 为空 → **直接拒答，且不调用 LLM**（省一次请求）。
3. LLM 输出 `NO_ANSWER`（或为空）→ 拒答。
4. 用正则提取所有 `[...]` id：出现任意一个**不在本次检索结果中**的 id，或**一个有效引用都没有** → 拒答。

通过后才生成 `Citation`，其 `quote` 是该 chunk 原文前 200 字符（逐字）。

### 三层概念必须分开

| 层 | 判据 | 函数 | 能证明什么 |
| --- | --- | --- | --- |
| 1 引用 ID 有效 | id 属于本次检索结果、`doc_id` 匹配 | `citation_ids_valid()` | 引用不是编造的 |
| 2 引用原文存在 | `quote` 是该 chunk 逐字文本 | `citation_quotes_verbatim()` | 指针能回查到真实原文 |
| 3 内容支持回答 | 引文真的支持该论断 | **人工或明确披露的 LLM judge**（评测任务 T4） | 事实支持 / 回答正确 |

`verify_citation_structure()` 只做 **1 + 2**，是**结构校验**；`verify_citations()` 只是它的兼容别名。
它们**不能**证明第 3 层，也**不能**被称为"事实正确性验证"或"回答正确性"。
回归测试 `test_structural_check_passes_even_when_answer_contradicts_its_source`
专门构造了"引用完全有效但答案说错端口"的例子：结构校验依然返回 True，
正确性只能由评测阶段的 judge 判定。CLI 的 `ask` 会分别打印三层状态与这条免责说明。

因此**编造引用不会静默进入最终答案**，这是"可验证引用"的实现核心；
后续实验里的指标应叫 **citation structure rate**，不叫 correctness。

`retrieval.min_score` 目前为 `0.0`（关闭），是留给后续实验的旋钮；本期**不调参、不做阈值实验**。

---

## 6. MOCK 与 REAL 的严格区分

| 层 | 位置 | 允许出现 |
| --- | --- | --- |
| 生产代码 | `ragkit/*.py` | 只有真实实现。`cli offline-demo` 是唯一例外：它从 `tests.fakes` 导入替身并打印 MOCK 横幅 |
| 测试替身 | `tests/fakes.py` | `FakeEmbedder`（确定性哈希向量）、`InMemoryStore`、`ScriptedLLM`。文件头明确写 MOCK |
| 模拟语料 | `tests/fixtures/` | 首行 `MOCK FIXTURE - NOT REAL DATA` |
| 真实语料 | `data/raw/` | 仅真实公开授权文档 + 出处 |
| 真实 E2E | `tests/test_e2e_real.py` | 标 `pytest.mark.real`，默认 skip；需 `RUN_REAL_E2E=1`，LLM 测试还需密钥 |
| 运行记录 | `RUNLOG.md` | 命令 + 原始输出 + 时间；未执行的命令明确写"未执行" |

**禁止**：把 MOCK 输出写进报告、把模拟数字当实验结果、伪造"已运行成功"、在生产代码里塞未被标注的假实现。

---

## 7. 基线验收清单（可逐条实测）

1. 干净环境 `python -m venv .venv && pip install -r requirements-dev.txt` 成功。
2. **不配置任何密钥**时 `python -m pytest -q` 全绿；真实 E2E 显示为 skipped 并注明原因。
3. `ruff check .` 通过。
4. `python -m ragkit.cli offline-demo` 打印带 `[chunk_id]`（`doc_id#index` 形式）的引用答案 + 两个拒答案例，顶部有 MOCK 横幅。
5. `python -m ragkit.cli ingest` 用**真实语料 + 真实本地 embedding + 真实 Chroma** 成功，输出文档数与 chunk 数。
6. `python -m ragkit.cli retrieve "..."` 能返回带出处与原文片段的 top-k，且 chunk id 可被 `store.get_chunk()` 回查。
7. 有 `OPENAI_API_KEY` 时 `cli ask` 能生成带可验证引用的答案；**本次若无凭据则如实记录"未执行"**。
8. 五个模块各自只 import 声明的依赖；`contracts.py` 零第三方依赖。
9. 仓库内 grep 不到 `sk-` 形态密钥；`.env` / `data/index/` / `eval/results/raw/` 被 gitignore，
   而 `eval/results/summary/` 中的真实可复现汇总结果按 [`eval/README.md`](../eval/README.md) 提交。
10. `RUNLOG.md` 记录真实命令 + 原始输出，明确区分 MOCK 与 REAL。
11. `eval/qa_template.csv` **不含** `expected_chunk_ids`；gold 用 `evidence_doc_id` + `evidence_quote`，`pytest tests/test_eval_evidence.py -q` 通过。
12. 结构校验与事实正确性在代码命名、CLI 输出、测试与文档中明确区分。
13. `fixed` 与 `paragraph` 都真正应用 `overlap`，且 `chunk_overlap_actual` 等于实际字符重叠数。

对应命令与实际结果见根目录 `RUNLOG.md`。

---

## 8. 当前基线未覆盖的内容（后续 PR）

对应五个任务与交付标准见 [`PROJECT_PLAN.md` §3.2、§7](PROJECT_PLAN.md) 及 [`TASKS.md`](TASKS.md)。
**单元测试通过不等于满足课程要求**：下面的缺口正是 R1d / R4 / R5 与 G3–G5 尚未完成的部分。

- 20 组正式 QA 及其 gold 证据引文（共同证据标准已定义在 `eval/README.md` + `eval/evidence.py`；`qa_template.csv` 目前只有 2 行格式示例）。
- 两种 chunking 的对比实验、命中率 / 正确率 / 拒答率数字；真实、可复现的结果与图表按
  [`eval/README.md`](../eval/README.md) 的规范提交，不预先写入仓库。
- 评测脚本、LLM-as-judge、检索阈值调参、chunk size/overlap 网格搜索。
- 最终版 prompt 工程、reranking、hybrid search、UI、报告与 slides。
- 把语料扩到课程讲义 PDF、引入 pypdf / OCR。

`chunking.py` 里 `fixed` 与 `paragraph` 只是让流水线跑通的**最小基线实现**，不是实验结论。

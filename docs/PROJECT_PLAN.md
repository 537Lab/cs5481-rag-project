# CS5481 Topic 5 项目方案（统一定义）

> **本文件是项目定义、课程要求映射、五人任务与协作计划的唯一来源。** README 是简明入口；
> `docs/TASKS.md` 只放任务卡；`docs/ARCHITECTURE.md` 只放技术契约；`eval/README.md` 只放评测格式；
> `CONTRIBUTING.md` 只放协作规则；`START_HERE.md` 只放上手步骤。这些文档都链接回本文件，
> 不再各自写一套项目背景、目标或交付标准。
>
> **当前状态**：五个任务尚未认领；应用领域、技术方案与 LLM 调用方案仍需五人共同确认。
> 本轮只定稿文档与协作计划，**没有**生成正式语料、正式评测集、实验结果，也没有产生任何付费 API 调用。

---

## 0. 三十秒速览

我们做 Topic 5「Knowledge Base Q&A System with Verifiable Citations」：把一组**公开、许可明确、
版本固定**的官方文档建成知识库，用户用自然语言提问，系统先检索原文片段，再让 LLM **只用这些片段**
作答，每条论断附上「来源文档 + chunk + 逐字引文」，知识库里没有的答案明确拒答。
重点在**后端数据管线与答案保真机制**，不是聊天界面。

五个人在同一套 `ragkit` 契约上并行做 T1 语料、T2 分块、T3 检索、T4 评测、T5 生成与演示；
每人都有代码、测试、真实运行和技术解释。正式实验统一使用同一份冻结语料、同一份 ≥20 组 QA、
同一 `top_k` / `min_coverage` / embedding / LLM，报告检索命中率、回答正确率与 chunking 对比结果。
最终交付：Canvas 上的报告（≤6 页正文）+ `.py` 源码 + 附在报告末尾的 slides + 15 分钟课堂展示，
以及**单独一页**的贡献比例与全体签名（硬性红线）。

---

## 1. 项目背景与实际问题

### 1.1 推荐应用领域（首选，待全组确认）

**面向开发者与运维的「官方技术手册版本化可溯源问答」**：以一份有明确开放许可、按版本发布的官方
产品手册为知识库，回答"某个字段/参数/命令在这个版本里怎么定义、是否已弃用、默认值是什么"这类问题。

推荐语料：**Kubernetes 官方文档**（`kubernetes/website` 仓库，站点内容采用
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)，按固定版本 tag 抓取 Markdown 源文件）。
选择与理由见 1.2；这只是推荐，**不是已决定的事实**，最终由全组共同确认。

### 1.2 为什么先评估、但不首选「公开高校规章及学生办事指南」

这是最初提出的方向，用户价值最高（用户就是本校同学），但逐项核查后有几项不能忽略的问题：

| 维度 | 公开高校规章 / 学生办事指南 | 开放许可官方技术手册（推荐） |
| --- | --- | --- |
| 语料获取 | 部分公开可下载，但多为 PDF（含表格、页眉页脚、扫描件），部分页面需校方登录；不同院系、不同学年版本并存 | 官方仓库的 Markdown 源文件，可按固定 tag 复现抓取，无登录、无 OCR |
| 授权 | 校规与手册通常**只写"公开可读"，没有明示再分发许可**；把全文复制进仓库与向量库存在版权灰区，无法声称"许可齐全" | CC BY 4.0 明示可复制与改编，署名并保留来源即可；与现有 `source_uri` / `license` 端到端设计直接契合 |
| 可评测性 | 条文精确、天然有拒答题，评测性很好；但中英混杂、跨学年版本冲突会让 gold 引文与"标准答案"产生歧义 | 条款精确、版本号明确、可逐字引用；"问未收录版本/已删除字段"是很自然的拒答题 |
| 文档处理难度 | 需引入 PDF 解析甚至 OCR，属于额外依赖与噪声源，且五人环境更难一致 | 需要清洗 front-matter、导航、代码块与表格，是真实的文档处理工作但不增加重型依赖 |
| 与课程重点的契合 | 契合"government policy documents"示例 | 契合"product manuals"示例；同样要求 load / chunk / embed / 检索 / 引用 |

**结论**：高校规章方向的用户价值更强，但在**授权、语料稳定性、可复现抓取**上不达标，容易在报告与
展示中被追问"你们凭什么收录这些全文"。因此推荐改用许可明确的官方技术手册，把同样的可溯源问答
机制、同样的评测方法、同样的"具体用户与真实痛点"保留下来，去掉授权与 PDF 风险。

**若全组仍倾向高校规章方向**，必须先共同确认三件事，再写入本文件替换本节：
① 只收录明确公开、无需登录、且许可允许课程作业收录与引用的文件；
② 固定到**单一学年 / 单一版本**，逐篇记录 URL、访问日期、版本与许可状态；
③ 语料只用于本课程私有仓库与作业展示，不对外再分发，并在报告里如实说明授权边界。
在此之前不要把它写成"已确定"。

### 1.3 目标用户与现实痛点

- **用户**：需要在特定版本上做配置、排障或写实验脚本的开发者 / 运维，以及本组同学在做课程实验时
  扮演的同一类用户。
- **场景**：升级或排障时想确认"这个字段在这个版本还有效吗、默认值是多少、正确的写法是什么"。
  答案散落在 concept / task / reference 三类页面，且不同版本的同名页面内容不同。
- **痛点**：关键词搜索对同义改写、术语差异不稳；直接问通用 LLM，模型凭训练记忆给出**过时或虚构**
  的字段与命令，而且无法指出依据；人工翻文档要跨多页比对，也无法确认"文档里到底有没有写"。

### 1.4 系统如何解决

用户提问 → 问题转向量 → 从向量库取回 top-k 原文片段（带文档名、版本、URL、许可、字符区间）→
把这些片段作为**唯一上下文**交给 LLM → 输出带 `[chunk_id]` 标记的答案 → 系统校验引用 ID 与逐字
引文 → 任何一环不成立或证据不足就明确拒答 → 用户可点开引文回查原文。
例：问"v1.30 里某个已弃用 API 的替代写法是什么"，系统给出答案 + 该版本文档某段的引文；
若冻结语料里没有该版本页面，回答"无法从提供的文档中回答"。

### 1.5 为什么需要文档处理、向量检索和 RAG

| 环节 | 为什么不能省 |
| --- | --- |
| 文档处理 | 官方手册是长 Markdown/HTML，含导航、front-matter、代码块、表格与版本标记。必须清洗、赋稳定 `doc_id`、保留 `source_uri` / `license`、切成可逐字回查的片段，否则引用无法回到原文，也无法做跨策略对比。 |
| 向量检索 | 用户用自然语言提问，与原文的措辞往往不同；纯关键词匹配对同义改写不稳。把问题和 chunk 映射到同一向量空间做语义相似度 top-k 检索，并由向量库持久化 chunk 与向量，才能"按意思"找到条款。 |
| RAG | LLM 的训练数据不含我们选定的固定版本文档，凭记忆会编造字段。检索到的原文作为唯一上下文，配合 prompt 约束、引用校验与拒答，把答案绑定到可核验来源；换语料即换知识，不需要重训模型。 |

### 1.6 与普通 LLM 问答的区别

| 维度 | 普通 LLM 直接问答 | 本系统 |
| --- | --- | --- |
| 知识来源 | 模型参数记忆，可能过时 | 冻结的、带出处与版本的文档快照 |
| 可验证性 | 无 | 每条论断带文档 + chunk + 逐字引文，可回查字符区间 |
| 无答案时 | 倾向猜测 / 编造 | 明确拒答，且不调用 LLM 也能拒答 |
| 可更新 | 需重训或微调 | 替换语料快照即可 |
| 可评测 | 只能人工感觉 | 检索命中率、回答正确率、正确拒答率、引用结构率、chunking 对比 |
| 可复现 | 模型版本不可控 | 冻结语料 + 冻结 QA + 固定配置 + 运行清单 |

**如何量化证明**（计划中的消融实验，不是已完成的结果）：同一份 ≥20 组 QA、同一个 LLM，分别跑
① 零上下文直接提问 ② 本系统 RAG 提问，对比回答正确率、可核验引用比例与幻觉/错误引用案例。
该实验需要真实 LLM 调用，须先由全组确认 API 方案与费用；未经确认不执行、不编造数字。

### 1.7 怎样证明系统有效

1. **≥20 组 QA**（含 answerable 与 unanswerable），gold 证据是**原文逐字引文**，用
   `eval/evidence.py::locate_evidence()` 定位到原始文档字符区间，而不是 chunk id（chunk id 是分块
   策略的产物，用它当 gold 会让两种策略的比较失去意义）。
2. **检索命中率**：`hit@1` / `hit@3`，声明 `min_coverage`（默认 0.5），按 chunking 策略分别报告。
3. **回答正确率**：以 `reference_answer` 为基准，默认**人工 judge**，两人独立评分并报告一致性；
   若用 LLM judge 须明确披露并先获全组批准。结构校验**不能**冒充正确性。
4. **拒答**：正确拒答率、误拒答率；**引用结构率**单列，不与正确性混用。
5. **chunking 对比**：≥2 种策略在同一冻结语料、同一 QA、同一参数下比较，报告 chunk 数、长度分布
   与 hit@1 / hit@3，并解释差异与失败案例。
6. **可复现**：每个汇总结果记录命令、配置、日期、执行者与冻结快照标识；开发期输出标注"开发用"，
   不进报告（规范见 `eval/README.md` 与 `eval/results/README.md`）。

### 1.8 项目边界与无法保证的事情

- 只覆盖**冻结快照**里收录的文档与版本；不保证最新、不保证未收录内容，不自动联网更新。
- 不提供官方解释、法律 / 学业决定，不替代官方文档与教务处；答案不具权威性。
- **不保证事实正确性**：引用 ID 有效 + 引文逐字只保证"指针可回查"，不保证引文支持该论断；
  人工 judge 也有主观性与评分误差。
- 不做多轮对话、用户登录与个性化、实时抓取、跨语言检索、复杂 UI、Agent、知识图谱、
  reranking 或混合检索（可作为讨论，不实现）。
- 不保证任何具体指标数值；不产生未经全组确认的付费 LLM 调用；不伪造运行结果。
- 若最终选高校规章方向，还需额外声明：语料仅用于本课程作业、按来源署名、不对外再分发，
  且不保证条文的现行有效性。

### 1.9 需要全组共同确认的少数事项

| # | 事项 | 影响 | 未确认时的默认处理 |
| --- | --- | --- | --- |
| C1 | 应用领域：推荐 1.1，或按 1.2 的三项前提改回高校规章 | T1 语料、T4 出题、报告背景 | 不开始正式语料采集，继续用 `CORPUS_V0` 做开发自测 |
| C2 | 正式语料范围与冻结日（文档数、版本、doc_id 命名） | T1 → T4 关键路径 | 采用 6.2 的 time-box 与 fallback |
| C3 | LLM API 方案：付费 / 免费额度 / 本地 OpenAI 兼容服务，及是否做零上下文消融 | R4 真实回答、回答正确率、演示 | 只用 MOCK / 离线链路，报告中如实写"未执行真实 LLM 调用" |
| C4 | 报告是否使用外部 LLM judge（若使用须披露） | 正确率口径 | 默认人工 judge，两人独立评分 |
| C5 | Canvas 组队登记是否已完成、五人贡献比例与签名的收集方式 | 通用要求 G2 / G5 | 不影响开发；交付前必须补齐 |
| C6 | 五个任务的认领与 Assignee | 分工 | 保持未认领，由本人认领 |

---

## 2. 项目目标和预期系统

### 2.1 目标（不改变 Topic 5）

在不改变 Topic 5 五项 Requirements 的前提下，交付一个**有具体用户、可溯源、可评测**的 RAG 系统：
① 完整后端数据管线（采集/清洗 → 分块 → 向量化 → 向量库 → 语义检索 → 受约束生成）；
② 每条论断可回查原文、证据不足即拒答的答案保真机制；
③ 可复现的实验与讨论：≥2 种 chunking 对比、≥20 组 QA、检索命中率与回答正确率；
④ 能支撑 15 分钟展示与 ≤6 页报告的证据链。

### 2.2 预期系统

- **输入**：冻结的公开文档快照 + 用户自然语言问题 + `config.toml` 非敏感参数。
- **输出**：`Answer`（答案文本、逐条 `Citation`、是否拒答、模型名、原始 LLM 输出）+ 检索命中的
  `RetrievedChunk`（含 score、rank、出处、许可、字符区间）。
- **可运行形态**：`cli ingest` / `cli retrieve` / `cli ask` / `cli offline-demo`，以及一键演示脚本；
  `cli offline-demo` 打印 MOCK 横幅，不能当实验结果。
- **评测形态**：`eval/qa_set.csv` + 答案产物 + `eval/metrics.py` 汇总指标 +
  `eval/results/summary/<experiment>/` 的可复现汇总结果。

### 2.3 明确不做

不引入 Agent、多智能体编排、知识图谱、向量库之外的第二套存储、复杂前端、LangChain / LlamaIndex。
理由：Topic 5 原文明确"主要挑战不是聊天界面，而是准备与提供知识的后端数据管线，以及保持答案
忠于来源的机制"；加这些既不加分，也会掩盖五个模块的边界、让 methodology 讲不清楚。

---

## 3. 老师原始要求及符合情况

### 3.1 依据与口径

- `CS5481: Data Engineering - Projects (2026)` 项目说明（本地 PDF，第 1 页 Instructions、
  第 6 页 Topic 5；两个存档版本内容在 Topic 5 与 Instructions 上完全一致）。
- `CS5481 Data Engineering Syllabus`（课程目标、周次主题、评分权重；小组项目占 30%）。
- 课程讲义 L2 数据获取、L3 预处理、L5 LLM for Data Engineering、L7 数据索引、L8 数据查询、
  L9 信息检索与推荐（向量空间模型、TF-IDF / BM25、P/R/F1、Hit rate）、L11 数据管理——
  仅用于**推断考察重点**，不是明文要求。
- 课程 PDF 与讲义不入库（版权与体积），仓库只记录结论与页码索引。

**三类要求必须分清**：

| 类别 | 含义 | 在报告里怎么写 |
| --- | --- | --- |
| **A 明文要求** | 项目说明 Instructions 1–5 与 Topic 5 Requirements 1–5 逐字要求 | 逐条对应、逐条举证，缺一不可 |
| **B 推断的考察重点** | 由课程大纲主题、讲义内容与评分方式推断，非老师明文 | 作为 methodology / discussion 的侧重，不写成"老师要求" |
| **C 自愿增加的质量目标** | 我们为提高可复现性与诚信而自加的设计 | 说明"为什么加"，不得写进"符合老师要求"的清单 |

### 3.2 A 类：老师明文要求逐项对应表

状态：✅ 已有可核验实现／⚠️ 部分具备、缺正式证据／❌ 未开展。

| # | 老师明文要求 | 类别 | 现有实现（可核验） | 剩余工作 | 验收标准 | 最终展示证据 |
| --- | --- | --- | --- | --- | --- | --- |
| G1 | 2026-11-24（周二）23:59 截止 | A | 计划已按此排期 | 按 6.5 时间表推进 | 11-24 前完成 Canvas 提交 | 提交时间戳 |
| G2 | 小组项目，每组最多 8 人；Canvas-People-Groups 组队（10-18 前） | A | 本组 5 人，≤8 | 确认 Canvas 登记已完成（C5） | Canvas 小组页面可查 | 报告封面列 5 人 |
| G3 | Canvas 提交报告 + 源码；课堂 15 分钟展示；报告至少 introduction / methodology / experiments and discussions；正文 ≤6 页，参考文献与附录不限；源码 `.py` 或 `.ipynb` | A | 源码为 `.py`；`ragkit/` + `tests/` 齐备 | 写报告、做 slides、排 15 分钟展示 | 三部分齐全、正文 ≤6 页、`.py` 可运行、展示 15 分钟 | 报告 PDF + slides + 现场演示录屏/截图 + 可运行 CLI |
| G4 | 展示 slides 附在报告末尾 | A | 无 | 生成并附在报告末尾 | 报告中 slides 紧随正文与贡献页之后 | 报告 PDF 目录 |
| G5 | **单独一页**写每人贡献比例(%) + **全体成员签名**，位于 appended slides 之前，不计入 6 页；缺页或缺签名 desk reject | A | 有 PR / commit 历史与 `docs/DEV_LOG.md`、`docs/AI_USAGE.md` 作为举证 | 五人据实填写比例与签名，单独成页 | 每人比例、五人签名、位置正确 | 报告 PDF 该页扫描件 |
| R1a | 收集一组文档（示例：course notes / product manuals / government policy documents） | A | `data/raw/` 4 篇真实 CC BY-SA Wikipedia 摘录 + `SOURCES.md` + `manifest.json`（开发语料 `CORPUS_V0`） | 按 C1 定稿应用领域，T1 采集并冻结正式语料（现有 4 篇是技术主题的百科摘录，与推荐领域不同，只作开发语料） | 文档真实、逐篇可打开 `source_uri` 与 `license`、零 MOCK 混入 | 语料表（篇数/版本/许可/URL）+ `frozen_manifest.json` |
| R1b | 写脚本 load / chunk / embed | A | `ragkit/loaders.py`、`chunking.py`、`embeddings.py`、`pipeline.ingest()`、`cli ingest`；`RUNLOG.md` 记录真实 4 篇 → 28 chunks | T1 强化编码/去重/空文件与出处必填；T2 策略参数化 | `cli ingest` 在冻结语料上成功；偏移不变式成立 | methodology 管线图 + `ingest` 真实输出 |
| R1c | 使用开源 embedding 模型或 API | A | Chroma 内置本地 ONNX `all-MiniLM-L6-v2`（开源、384 维、无需密钥），另备 OpenAI 兼容 embedding | 在报告写明模型与维度 | 无密钥可完成 ingest/retrieve | 配置快照 + 模型说明 |
| R1d | **比较 ≥2 种 chunking 策略并报告对检索质量的影响** | A | `fixed` / `paragraph` 两个最小实现 + 单测；`eval/evidence.py` 定义与策略无关的共同证据标准 | T2 写对比实验驱动，T4 冻结 QA，正式跑两种策略 | 同一语料 / QA / `top_k` / `min_coverage` 下可比，报告 chunk 数、长度分布、hit@1 / hit@3，数字来自真实运行 | 对比表 + 图 + 失败案例 + `summary/` 运行清单 |
| R2 | 把 chunk 与对应 embedding 存入向量数据库 | A | `ragkit/store.py` 用 Chroma 持久化，携带出处/许可/字符区间；`get_chunk()` 回查有测试 | T3 完善 collection 隔离与 score 语义说明 | 重开客户端仍可查；出处 roundtrip 完整 | 架构图 + `store` 测试与真实 `retrieve` 输出 |
| R3 | 问题转 embedding，按语义相似度检索最相关 chunks | A | `pipeline.retrieve()` 与 `cli retrieve` 真实输出 top-3（score、出处、字符区间） | T3 出检索诊断；T2/T4 用同一检索接口做实验 | `top_k`、score 语义、失败案例写进文档 | 检索示例 + score 分布 |
| R4a | 把原始问题 + 检索到的 chunks 传给 **LLM API** | A | `OpenAILLM` / `build_llm()` / `cli ask` 已实现；`RUNLOG.md` 明确记录**未执行**（无密钥，EXIT=2） | 按 C3 确认方案后真实跑 `cli ask` 并留输出 | 至少一次真实 LLM 调用的可核验输出；否则如实写"未执行" | 真实问答日志 + 报告里如实说明 |
| R4b | Prompt 令 LLM **只用给定上下文**作答，**每条论断**标注来源文档与 chunk | A | `SYSTEM_PROMPT` 明令只用 CONTEXT、逐论断内联 `[chunk_id]`、不得编造 id；`Citation` 带 doc_id / quote / source_uri | T5 核对逐论断覆盖、引文回查；真实 LLM 下验证 | 每条论断有可回查引用；编造 id 被拒答；逐字引文成立 | 带引用的答案截图 + 引用三层说明 |
| R4c | 知识库没有答案时明确说明，不猜测 | A | 四道门（空检索 / `NO_ANSWER` / 编造 id / 无有效引用）+ `ABSTAIN_MESSAGE`；MOCK 演示含 2 例拒答 | 真实 LLM 场景验证；T4 计算拒答指标 | 正确拒答率、误拒答率可算 | 拒答案例 + 指标表 |
| R5a | 构造 ≥20 组 QA 测试集 | A | `eval/qa_template.csv` 仅 2 行**格式示例**；字段与 gold 标准已定义 | T4 编写并冻结 `eval/qa_set.csv` | ≥20 组，含 answerable / unanswerable，每条 gold quote 通过 `locate_evidence()` | QA 表 + 覆盖度说明 |
| R5b | 报告**检索命中率** | A | `eval/evidence.py::is_retrieval_hit()` 已定义；无聚合脚本、无正式结果 | T4 实现 `eval/metrics.py`；T2/T3 调用同一实现 | hit@1 / hit@3，声明 `min_coverage`，按策略分别报告 | 指标表 + 可复现 `metrics.json` |
| R5c | 报告**回答正确率** | A | 三层概念已区分，人工 judge 口径已写入 `eval/README.md`；无 judge 结果 | 按 C4 完成 judge；T5 产出答案产物 | 人工 judge 与一致性披露；结构校验不冒充正确性 | judge 协议 + 评分表 + 正确率 |
| T5-intro | Topic 5 引言：重点是后端数据管线与保真机制，不是聊天界面 | A | 五模块 M1–M5 后端划分、不用 LangChain、无复杂 UI；六项技术取舍记录在 `docs/ARCHITECTURE.md` | 在报告 introduction / methodology 明确回应 | 报告把管线与保真机制作为主线 | methodology 架构图 |

> **截止口径**：项目说明写 `11:59 pm, November 24, Tuesday, 2026`；课程大纲的通用条款写
> 「homework / projects 当天 6 pm 前」。两者不一致，本方案按**项目说明**的 23:59 排期，
> 并在 Day 1 向 TA 确认一次；确认结果写回本表 G1。

### 3.3 B 类：根据课程内容推断的考察重点（非明文要求）

| # | 推断重点 | 依据 | 现状 | 应补的工作 |
| --- | --- | --- | --- | --- |
| B1 | 完整数据工程管线：获取 → 预处理 → 索引 → 查询 → 应用 → 管理 | 大纲周次 2/3/7/8/9/11 | M1–M5 已对应 | 报告中按此顺序写 methodology，逐步说明取舍 |
| B2 | 检索模型与评价指标的理解（向量空间模型、TF-IDF / BM25、P/R/F1、Hit rate） | L9 | 现用稠密向量语义检索 | 在 experiments/discussions 解释为何选稠密检索、与关键词检索的取舍与局限（**不要求**实现 BM25） |
| B3 | LLM for Data Engineering：prompt 设计、用 LLM 完成数据任务 | L5 | `SYSTEM_PROMPT` + 拒答 + 引用约束 | 把 prompt 与三层校验写进 methodology，讨论失败模式 |
| B4 | 可复现实验与讨论（报告含 experiments and discussions） | G3 | 冻结快照 / 配置 / 运行清单规范已具备，但**无任何正式实验** | 完成 7.2 的实验矩阵，讨论局限与失败案例 |
| B5 | 团队协作与贡献可追溯（team-based learning） | Syllabus + G5 | PR / CI / `DEV_LOG` / `AI_USAGE` 已具备 | 五人贡献比例与签名、按 PR 历史举证 |
| B6 | 15 分钟课堂展示的取舍表达 | G3 | 无 | 用一条真实问题贯穿"文档→向量→检索→引用→拒答→指标" |

### 3.4 C 类：我们自愿增加的设计与质量目标（不是老师要求）

| # | 自愿目标 | 为什么加 |
| --- | --- | --- |
| C-1 | 出处与许可随文档一路传递到 chunk / 检索结果 / 引用 | 让"可验证引用"可回查，也满足开放许可的署名要求 |
| C-2 | 引用三层区分（ID 有效 / 引文逐字 / 内容支持回答），结构校验 ≠ 事实正确性 | 避免把工程校验误报成 R5c 的回答正确率 |
| C-3 | gold 用原文逐字引文定位字符区间，不用 chunk id | 否则两种 chunking 策略的比较不成立 |
| C-4 | 冻结语料与 QA 快照、内容哈希、同一 `top_k` / `min_coverage` / embedding / LLM | 保证实验可比、可复现 |
| C-5 | MOCK / REAL 严格分离、离线 CI、密钥扫描、零未授权付费调用 | 学术诚信与环境一致性 |
| C-6 | 正确拒答率、误拒答率、引用结构率、零上下文 LLM 消融对照 | 更完整地说明系统是否真的有效 |
| C-7 | 贡献比例、AI 辅助使用披露、每日集成清单 | 满足 G5 并让并行开发不失控 |
| C-8 | 不用 Agent / 知识图谱 / 复杂框架 | 保持五个模块边界清晰，便于讲解与评分 |

### 3.5 必须写进报告的一句声明

> **离线单元测试通过（当前 `57 passed / 2 skipped`）只说明模块契约与流水线没有坏，
> 不等于满足课程要求。** 它不能替代 R1d 的 chunking 对比实验、R4 的真实 LLM 回答、R5 的
> ≥20 组 QA 与两个指标，也不能替代 G3–G5 的报告、slides、15 分钟展示与贡献比例签名页。
> CI 绿灯同样只说明代码与测试没坏，不证明任何实验数字正确。

---

## 4. 技术架构和设计理由

### 4.1 数据流（严格单向）

```
manifest + 原文 → Document → Chunk → (Chunk, vector) → Chroma → RetrievedChunk → Answer
      M1             M2          M3 / M4          M4            M4 / M5
```
`Document / Chunk / RetrievedChunk / Answer` 的字段与四个 `Protocol` 接口只在
`ragkit/contracts.py` 定义（改动需 ≥2 人同意）。不变式
`doc.text[chunk.char_start:chunk.char_end] == chunk.text` 是引用可回查的基础。

### 4.2 技术取舍（详见 `docs/ARCHITECTURE.md`）

| 决定 | 选择 | 理由 / 代价 |
| --- | --- | --- |
| 布局 | 扁平 `ragkit/` + `config.toml` + `.env` 读密钥 | 五人不需打包即可运行；代价是命令必须在仓库根目录执行 |
| Embedding | 本地 ONNX `all-MiniLM-L6-v2`（无密钥）+ 可选 OpenAI 兼容 API | 契合"开源 embedding 模型"；代价是首次下载约 80 MB |
| LLM | OpenAI 兼容接口（`OPENAI_BASE_URL` 可指向本地兼容服务或网关） | 契合"LLM API"；可避免未授权的付费调用（C3） |
| 向量库 | ChromaDB 嵌入式持久化 | 是真正的向量数据库，且五人环境一致；不引入外部服务 |
| 框架 | 不用 LangChain / LlamaIndex | 保持五个模块边界可讲解、可分别开发 |
| 检查 | `ruff` + 离线 `pytest` + GitHub Actions 密钥扫描 | `main` 永远可运行；CI 不重跑实验 |

### 4.3 引用与拒答机制

三层概念必须分开：**① 引用 ID 有效**（`citation_ids_valid()`）、**② 引文逐字存在**
（`citation_quotes_verbatim()`）、**③ 内容支持回答**（人工或明确披露的 LLM judge）。
`verify_citation_structure()` 只做 ① + ②，**绝不能**称为事实正确性或回答正确性。
四道拒答门：空检索（不调用 LLM）、`NO_ANSWER`、任意编造引用 id、完全没有有效引用。

### 4.4 为什么这个架构正好对应 Topic 5

- 题目重点在后端管线 → M1–M5 五个独立模块 + 薄编排层，实验与讲解都能逐步展示。
- 题目重点在答案忠于来源 → 出处端到端传递、逐字引文、引用 ID 校验、拒答、三层区分。
- 题目要求比较 chunking → gold 定义在**原始文档字符区间**，与分块策略解耦，比较才有意义。
- 题目要求 ≥20 组 QA 与两个指标 → `eval/` 作为独立评测层，不与生成逻辑混在一起。

---

## 5. 五个合理的并行任务

五人地位平等，**不预先指定谁承担哪个任务**；由本人在对应 Issue 评论认领并设置 Assignee。
任务卡全文见 [`docs/TASKS.md`](TASKS.md)，GitHub 任务见 Issues #1–#5，三处内容一致。

| 任务 | 主题 | 主要产物（代码 + 测试 + 运行 + 分析） | 15 分钟展示中的角色 |
| --- | --- | --- | --- |
| T1 | 正式知识库与文档处理 | `loaders.py` 强化、正式语料 + `frozen_manifest.json`、`fetch_corpus.py`、`docs/CORPUS.md` | 展示语料表、出处/许可与清洗前后对比 |
| T2 | Chunking 策略与对比实验 | `chunking.py` 参数化、`eval/chunking_experiment.py`、`docs/CHUNKING_EXPERIMENT.md` | 展示 ≥2 策略的对比表与失败案例 |
| T3 | 检索层与向量库 | `store.py` / `embeddings.py` 增强、`eval/retrieval_diagnostics.py`、`docs/RETRIEVAL.md` | 展示 top-k 检索、score 分布与索引隔离 |
| T4 | 评测集与**唯一指标实现** | `eval/qa_set.csv`、`eval/metrics.py`、`eval/judge_protocol.md`、`tests/test_eval_metrics.py` | 展示 ≥20 组 QA、命中率 / 正确率 / 拒答指标 |
| T5 | 生成、引用与可运行演示 | `generation.py` / `cli.py` 增强、答案产物、`demo/`、`docs/ANSWER_QUALITY.md` | 现场跑一条真实问答 + 一条拒答 + 引用回查 |

### 5.1 单一职责划分（解决旧方案的三处重叠）

| 争议点 | 唯一拥有者 | 其他任务只能做什么 |
| --- | --- | --- |
| 指标定义与聚合（hit@k、正确率、正确/误拒答率、引用结构率） | **T4**（`eval/metrics.py`） | T2 / T3 / T5 一律**导入调用**，不得另写一份计算 |
| chunking 对比实验的**运行与报告** | **T2**（`eval/chunking_experiment.py`） | T3 只提供检索诊断，T4 只提供指标函数与 QA |
| 检索质量**诊断**（score 分布、gold 证据排名、失败原因、索引 roundtrip） | **T3** | T3 **不发布**正式命中率数字；正式数字由 T4 汇总 |
| 回答正确性判定与 judge 协议 | **T4** | T5 只产出答案产物，不计算正确率；T5 可做定性失败案例 |
| 拒答**行为**（prompt、四道门、何时 `abstained=True`） | **T5** | T4 只读取 `Answer.abstained` 计算指标，不改生成逻辑 |
| gold 引文 / QA 数据 | **T4** | 任何任务不得另造"临时 gold"文件或把开发样例当正式评测集 |

---

## 6. 依赖关系、集成方式与时间安排

### 6.1 Day 1 必须先冻结的**共同数据接口**（不是等人，而是等 schema）

五个任务并行开发的前提是接口固定，而不是某个人的代码写完。Day 1 由五人共同确认以下 5 个契约，
之后写入 `docs/ARCHITECTURE.md` 并冻结；改动需 ≥2 人同意。

| # | 产物 / 接口 | 产出方 | 消费方 | 内容 |
| --- | --- | --- | --- | --- |
| I1 | `data/raw/manifest.json` + `frozen_manifest.json` | T1 | T2 / T3 / T4 / T5 | 每篇 `doc_id` / `path` / `title` / `source_uri` / `license` / `version`；快照含 `corpus_id`、生成时间、每篇 `sha256` |
| I2 | `eval/qa_set.csv` schema | T4 | T2 / T3 / T5 | `qid, question, reference_answer, evidence_doc_id, evidence_quote, category, notes`（沿用 `qa_template.csv`） |
| I3 | `eval/metrics.py` 公开函数签名 | T4 | T2 / T3 | `retrieval_hit_rate()` / `answer_correctness()` / `abstention_rates()` / `citation_structure_rate()`；**Day 1 先合入可 import 的骨架 + 单测** |
| I4 | 答案产物 `eval/answers/<run_id>.jsonl` | T5 | T4 | 每行一个 `qid` + `Answer`（含 `answer_text` / `abstained` / `citations` / `model` / `raw`）+ 本轮 `retrieved_chunk_ids` + `run_id` / `config_ref` |
| I5 | 实验配置与结果 schema | T4 + T2 | 全员 | `strategy` / `size` / `overlap` / `top_k` / `min_coverage` / embedding / LLM / `corpus_ref` / `qa_set_ref`（见 `eval/results/README.md`） |

### 6.2 T1 正式语料与 T4 标准答案：实质性修正

旧方案让 T4 的 gold 引文必须出自"T1 冻结后的正式语料"，但没有给 T1 设定完成时限，也没有兜底，
于是 T4 的**主交付物**被无限期阻塞，T2 / T3 / T5 的正式实验也随之顺延。修正如下：

1. **依赖对象从"人"改成"快照"**：T4 需要的是 I1 冻结快照，不是"等 T1 做完"。Day 1 先共同
   确认 I1 的字段与 `corpus_id` 规则，T4 当天就能写 `qa_set.csv` 的结构、metrics 代码与测试。
2. **T1 time-box**：正式语料快照最迟 **Day 2 结束**冻结；冻结动作是合并一个只含语料与
   `frozen_manifest.json` 的小 PR，不是等到最后一起提交。
3. **明确的 fallback**：若 Day 2 结束时 C1/C2 未确认或 T1 未能冻结，全组可当场决定把
   `CORPUS_V0`（已提交的 4 篇）作为正式实验语料，并在报告里如实说明语料规模与局限。
   **不允许出现"因为语料没定，QA 与实验全部停摆"。**
4. **gold 绑定是机器校验，不是人工排队**：T4 的每条 `evidence_quote` 必须能被
   `locate_evidence()` 定位；语料快照一变就重跑校验命令，不靠口头确认。
5. **T1 只加不改**：正式语料只能新增 `doc_id`，不得修改 `CORPUS_V0` 四篇的文本与 doc_id，
   保证开发期写的测试与 QA 草稿仍然有效。

### 6.3 哪些能并行、哪些必须等

| 可以立即并行（Day 1，基于已冻结的 `contracts.py` / `evidence.py` / `CORPUS_V0` / `tests/fixtures/`） | 必须等待共同数据或接口 |
| --- | --- |
| T1：`loaders.py` 编码/去重/空文件/出处必填与单测；采集脚本与文档清单 | T4 的正式 `qa_set.csv` gold 引文 ← I1 冻结语料（或 6.2 fallback） |
| T2：策略参数化、稳定元数据、`chunking_experiment.py` 骨架与单测 | T2 / T3 / T5 的**正式指标数字** ← I3 `metrics.py` + 冻结 `qa_set.csv` |
| T3：collection 隔离、score 语义、检索诊断脚本与单测 | T4 的正式回答正确率 ← I4 答案产物 + judge（C4） |
| T4：`metrics.py` 骨架与单测（用 MOCK `Answer`）、judge 协议、QA 题干与结构设计 | 零上下文 LLM 消融 ← C3 全组批准 API 方案 |
| T5：`generation.py` / `cli.py` 增强、答案产物导出、demo 与单测（用 MOCK / fixtures） | 真实 LLM 问答证据 ← C3 |
| 五人共用：`CORPUS_V0` + `qa_template.csv` 格式示例 + 自己新建并标注 MOCK 的 fixture | 报告里的正式数字 ← 冻结语料 + 冻结 QA + 真实运行 |

开发期输出必须标注「开发用」，**不得**称正式实验结果、不得写进报告。

### 6.4 每天怎么集成（避免五个 Agent 最后才合并）

1. **薄片优先**：每个任务 Day 1–2 先合一个"可 import / 可 `--help` / 带单测"的小 PR
   （例如 I3 的 `metrics.py` 骨架、T2 的实验脚本骨架），而不是攒一个大 PR。
2. **每人每天至少一个可合并的小 PR**，分支短生命周期；每天开工先 `git pull` + rebase `main`。
3. **每日集成自检**（由当天提交 PR 的人执行，不设固定负责人），现在就能跑的是：
   ```bash
   python -m pytest -q
   ruff check .
   python -m ragkit.cli offline-demo
   python -m ragkit.cli ingest
   python -m ragkit.cli retrieve "..." --top-k 3
   ```
   下面两条在对应薄片合入后才加入清单（Day 1 起逐步启用）：
   ```bash
   python -m eval.metrics --help              # I3 合入后
   python -m eval.chunking_experiment --help  # T2 脚本合入后
   ```
   外加一条数据一致性检查：对 `qa_set.csv` 每一行调用 `locate_evidence()`，全部通过才算绿。
   把输出贴到当天 PR 或 `docs/DEV_LOG.md`，不写"应该能通过"。
4. **接口变更当天广播**：谁改 I1–I5 中任意一项，当天在 PR 里 @ 其余四人并写明影响，
   按 `CONTRIBUTING.md` 走 ≥2 人同意。
5. **Day 4 联合 dry run**：五模块端到端跑一遍（开发数据，明确标注非正式），确认答案产物能被
   T4 的 metrics 读进去，再进入 Day 5 正式实验。
6. PR 合并条件见 `CONTRIBUTING.md`；`ci / check` 绿灯 + 至少 1 位其他组员 Approve。

### 6.5 时间安排（相对天数，按 2026-11-24 23:59 截止倒排）

| 时间 | 全员 | 关键产出 / 门槛 |
| --- | --- | --- |
| Day 1 | clone、跑通 `offline-demo` + `pytest` + `ruff`；共同确认 C1–C6 与 I1–I5；认领 Issue | 五个契约冻结；五个薄片 PR 至少开出；`metrics.py` 骨架合入 |
| Day 2 | 并行开发与自测；T1 冻结正式语料（或启用 6.2 fallback）；T4 定稿 QA 结构 | **I1 语料快照冻结**；每人 1 个 PR 合入 |
| Day 3 | 并行开发；T4 冻结 `qa_set.csv`；T5 产出答案产物；T2 / T3 完成实验与诊断脚本 | **≥20 组 QA 全部通过 `locate_evidence()`**；I4 答案产物可被 metrics 读取 |
| Day 4 | 联合 dry run、修接口问题、完成引用与拒答的真实链路验证 | 端到端冒烟通过；所有模块测试全绿 |
| Day 5 | **正式实验**：同一冻结语料 + 同一 QA + 同一参数，跑 chunking 对比与完整评测 | `eval/results/summary/` 下可复现汇总结果（命令 / 配置 / 日期 / 快照 id） |
| Day 6 | 结果分析、失败案例、报告 introduction / methodology / experiments and discussions | 报告初稿 ≤6 页；图表与指标可追溯 |
| Day 7 | 15 分钟 slides、贡献比例 + **全体签名单独一页**、AI 使用披露、Canvas 提交 | G1 / G3 / G4 / G5 全部满足 |

### 6.6 冻结规则

| 名称 | 内容 | 冻结时点 | 约束 |
| --- | --- | --- | --- |
| `CORPUS_V0` | 已提交的 4 篇 `data/raw/*.txt` | 已冻结（开发基线） | 只供开发与自测，doc_id 与文本不得修改；启用 6.2 fallback 时才升格为正式语料并如实说明 |
| 正式语料快照 | T1 采集的文档 + `frozen_manifest.json`（含 `corpus_id` 与 `sha256`） | T1 的 PR 合并并经 review（Day 2） | 冻结后不得改 doc_id / 文本 / manifest；所有正式实验引用同一 `corpus_id` |
| 正式评测集 | T4 的 `eval/qa_set.csv` | T4 的 PR 合并并经 review（Day 3） | 冻结后所有对比使用同一份 QA、同一 `top_k` / `min_coverage` / embedding / LLM |

---

## 7. 测试、实验、展示和最终交付标准

### 7.1 三层验证，不能互相替代

| 层 | 内容 | 能证明什么 | 不能证明什么 |
| --- | --- | --- | --- |
| L1 单元 / 静态检查 | `pytest -q`、`ruff check .`、CI 密钥扫描（当前 57 passed / 2 skipped） | 契约、纯函数、边界条件与流水线没坏 | 不能证明 R1d / R4 / R5，也不能证明任何实验数字 |
| L2 集成 / 运行验证 | `cli ingest` / `retrieve` / `ask` / `offline-demo`、每日集成自检、Day 4 dry run | 五个模块接得上、出处与引用可回查 | `offline-demo` 是 MOCK，不能当实验结果 |
| L3 正式实验 | 冻结语料 + 冻结 QA + 固定参数下的真实运行 | 命中率、正确率、拒答、chunking 对比 | 不保证事实绝对正确；不代表未收录文档的表现 |

### 7.2 正式实验矩阵（Day 5，同一基准）

| 实验 | 变量 | 固定项 | 报告指标 |
| --- | --- | --- | --- |
| E1 chunking 对比（R1d） | `fixed` vs `paragraph`（或不同 size / overlap） | 语料、QA、`top_k`、`min_coverage`、embedding、LLM | chunk 数、长度分布、hit@1、hit@3、失败案例 |
| E2 系统评测（R5） | 全量 QA | 同上 + 选定策略 | 检索命中率、回答正确率、正确拒答率、误拒答率、引用结构率 |
| E3 消融（C-6，需 C3 批准） | 零上下文 LLM vs RAG | 同一 LLM、同一 QA | 正确率、可核验引用比例、幻觉案例 |
| E4 检索诊断（T3） | `top_k`、score 分布、gold 证据排名 | 同一索引 | 定性诊断与失败原因（不发布正式命中率） |

所有汇总结果按 `eval/results/README.md` 提交到 `eval/results/summary/`，逐题原始输出留在本地。
**禁止**硬编码指标、把 MOCK 当 REAL、把结构校验率称作回答正确率、写"已运行"而实际没跑。

### 7.3 15 分钟展示的证据链

一条真实问题贯穿全流程：文档表与许可 → 清洗前后 → 两种 chunk → 向量入库 → top-k 检索输出 →
带引用的答案 → 逐字引文回查 → 拒答案例 → chunking 对比表 → 命中率 / 正确率 / 拒答指标 →
局限与失败案例。每个数字指向 `summary/` 里的命令与配置。

### 7.4 最终交付清单（Canvas）

- [ ] 报告 PDF：introduction / methodology / experiments and discussions，正文 ≤6 页；
      参考文献与附录不限；slides 附在报告末尾（G3 / G4）。
- [ ] **单独一页**：五人贡献比例(%) + 全体签名，位于 slides 之前（G5，缺页直接 desk reject）。
- [ ] 源码 `.py`（或 `.ipynb`）与 `requirements*.txt`；干净环境可跑通 7.1 的 L1 / L2。
- [ ] 冻结语料与 `frozen_manifest.json`、`eval/qa_set.csv`、`judge_protocol.md`。
- [ ] `eval/results/summary/` 下真实可复现的汇总指标、图表、配置快照与运行清单。
- [ ] 15 分钟展示 slides 与可运行 demo。
- [ ] `docs/DEV_LOG.md` / `docs/AI_USAGE.md` 中五人各自的真实贡献与 AI 辅助披露。

### 7.5 学术诚信红线

不提交 `.env` / API key / `data/index/` / `eval/results/raw/`；不硬编码指标、不伪造运行记录、
不把 MOCK 输出写进报告、不把没跑过的命令写成"已验证"；不产生未授权付费调用；
贡献比例按实际人工工作填写并由本人签名，不由 AI 代填。

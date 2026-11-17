# 实际开发记录

用途：课程要求报告写明**每人贡献比例 + 全体签名**，并遵守学术诚信要求。本文件按时间记录
「谁执行了什么、验证结果来自哪里」。**不要把「代码已生成」或「测试通过」记成「作业已完成」。**
项目定义与交付标准见 [`PROJECT_PLAN.md`](PROJECT_PLAN.md)。

## 记录口径（重要）

| 主体 | 含义 | 本文件如何记 |
| --- | --- | --- |
| **AI Agent** | WorkBuddy AI 在仓库账号持有人授权下实际执行的命令与代码生成 | 写实际执行者，不写成任何组员本人执行 |
| **人工复核（本人确认）** | 执行者本人或指定复核人阅读、判断、修改或亲自运行 | 只有存在可核验记录（PR review、本人确认）时才记；否则写「待确认」 |
| **GitHub Actions** | 云端 runner 上的 CI 验证 | 单独记为云端验证，不与本地命令混同，也不等于人工复核 |

**截至本记录，除仓库账号持有人本人已在做的 T4 之外，其余组员尚未开始正式开发**，仓库中也
还没有其他组员的贡献记录。以下内容全部属于
bootstrap、仓库规范化与文档定稿阶段，由 AI Agent 在仓库账号持有人授权下执行。是否逐项人工复核，
仓库内没有可核验记录，**需由本人确认后补充**；不能据本文件推断为「某人已亲自执行/审阅」。

PR 历史与 commit message 是贡献比例的**证据来源**，本文件只是索引，不替代报告中的贡献声明页。

---

## 已发生的记录

| 日期 (GMT+8) | 阶段 | 实际执行者 | 做了什么 | 验证来源 | 人工复核（本人确认） |
| --- | --- | --- | --- | --- | --- |
| 2026-11-13 18:12–19:00 | 基础工程搭建 | AI Agent（WorkBuddy），在仓库账号持有人授权下 | 读课程 PDF；设计五模块契约；实现 `loaders/chunking/embeddings/store/generation/pipeline/cli`；抓取 4 篇 CC BY-SA 语料；写 README / ARCHITECTURE / CONTRIBUTING / RUNLOG / CI / PR 模板；45 个测试 | Agent 本地执行：`ruff` 通过、`pytest` 43 passed / 2 skipped、`cli ingest` 4→28 chunks、`cli retrieve` top-3、`cli offline-demo` 3 案例、密钥扫描无命中；原始输出见 `RUNLOG.md` 第 1 节 | 待本人确认 |
| 2026-11-13 19:52–20:10 | 基线修订 | AI Agent（WorkBuddy），依据账号持有人转述的审阅意见 | gold 改共同证据标准（`eval/evidence.py` + `qa_template.csv`）；引用三层概念拆分；`ParagraphChunker` overlap 与元数据修正；加固薄弱断言 | Agent 本地执行：`ruff check .` 通过、`pytest` 57 passed / 2 skipped、`cli offline-demo` / `ingest` / `retrieve` 真实运行；输出见 `RUNLOG.md` 第 2 节 | 待本人确认 |
| 2026-11-13 20:10–20:20 | GitHub 仓库建立 | AI Agent（WorkBuddy），使用仓库账号持有人账号 | 创建私有仓库 `537Lab/cs5481-rag-project`；推送首次提交 `a12bb14`；配置 CI；关闭自动合并；确认分支保护/Rulesets 受套餐限制；写 `TASKS.md`、`START_HERE.md`、本文件与 `AI_USAGE.md` | **云端验证**：GitHub Actions `ci` run `43423374183` → `conclusion=success`（ruff / pytest / 密钥扫描）；API 核验 `allow_auto_merge=false`、保护规则 403 | 待本人确认 |
| 2026-11-13 20:20–20:30 | bootstrap 收尾 | AI Agent（WorkBuddy） | 推送 `3f3176a`；创建 5 个 task Issue（#1–#5）；核查远端文件树 | **云端验证**：CI run `43424432557` → `success`；`gh issue list` 5 个 task Issue | 待本人确认 |
| 2026-11-13 21:20–21:40 | 仓库规范化整理 | AI Agent（WorkBuddy），由账号持有人发起 | 重写 README；厘清 START_HERE / CONTRIBUTING / ARCHITECTURE 职责；修正错误路径、过期状态与矛盾描述；清理团队文档中的个人环境信息（本地归档）；核查本文件与 `AI_USAGE.md` 的真实性；明确语料/评测集冻结规则；制定实验结果提交规范 | Agent 本地执行：`ruff check .` 通过、`pytest` 57 passed / 2 skipped、`cli offline-demo` / `ingest` / `retrieve` 真实运行、密钥扫描无命中；输出见 `RUNLOG.md` 第 4 节。**云端验证**：该 PR 的 `ci / check`（见 PR 页面） | 待本人确认（建议在 PR review 中完成） |
| 2026-11-14 17:20– | 项目定义与协作计划定稿 | AI Agent（WorkBuddy），由账号持有人发起 | 核对课程 PDF 原文（Instructions 1–5、Topic 5 Requirements 1–5）；新增 `docs/PROJECT_PLAN.md`（背景/目标/要求映射/架构/任务/排期/交付）；重写 README 与 `docs/TASKS.md`；清理面向组员资料中的预设身份标签；同步五个 Issue；**只改文档，未改 `ragkit/` 代码** | Agent 本地执行：`ruff check .`、`pytest -q`、文档相对链接检查、预设身份标签与过时文件名残留扫描、Issue 与文档一致性核对；输出见 `RUNLOG.md` 第 6 节。**云端验证**：本 PR 的 `ci / check` | 待本人确认 |
| 2026-11-14 | T4 首轮（任务包 #4，分支 `t4-eval-qa-metrics` 的 PR） | 组员（仓库账号持有人，PR 作者）+ AI 编码 agent 辅助写，组员本人阅读并修改 | 新增 `eval/qa_set.csv`（35 条：27 answerable + 8 unanswerable）、`eval/metrics.py`（validate/retrieval/score/mock-demo）、`eval/judge_protocol.md`、`tests/test_eval_metrics.py`（39 例）；改写 `eval/README.md`；`RUNLOG.md` 记录首轮命令与输出 | Agent 本地执行：`eval.metrics validate` → 27 条 gold quote 逐字定位、10 个 absent token 确认不存在；`retrieval --hits 1,3 --min-coverage 0.5` → **hit@1 16/27=0.5926、hit@3 23/27=0.8519**（两轮一致）；`ruff check .` 通过；`pytest` 96 passed / 2 skipped。**零付费调用**；人工 judge 尚未开始，因此无 `answer_correctness` 数字。原始输出见 `RUNLOG.md` 第 7 节 | 待其他组员在本 PR review 中确认（合并时该记录一度被覆盖，见 `RUNLOG.md` 第 8.7 节） |
| 2026-11-15 | T4 同步修订（按 PR #8 接口 I3/I4/I5） | 组员（仓库账号持有人，PR 作者）+ AI 编码 agent 辅助，组员本人阅读并修改 | 处理组员 5 条意见：`git merge origin/main`（4 处文档冲突以 main 为准）；按 I3 暴露四个公开指标函数；按 I4 读 `eval/answers/<run_id>.jsonl` 与 `retrieved_chunk_ids`；正确率分母改为已评分的 answerable 题并新增 `grading_coverage`；`ABSENT_TOKENS` 降为必要条件 + `REVIEWED_BY`/`--require-reviewed`/`--formal` 复核门；按 I5 字段名写 config 快照与 summary 三件套；35 题定为 `CORPUS_V0` 开发集。测试 39 → 67 例（验收双文件 45 → 73），首轮用例全部保留 | Agent 本地执行：`ruff check .` 通过；`pytest` **124 passed / 2 skipped**（验收双文件 73 passed）；`validate`、`retrieval`（hit@1 16/27、hit@3 23/27，与首轮一致）、`score --run-id`、四道护栏的 `exit=2` 逐一实跑。原始输出见 `RUNLOG.md` 第 8 节。**云端验证**：本 PR 的 `ci / check`（待跑） | 待另一位组员 review 后合并 |

> 说明：上表前五行由账号持有人**发起**，命令与代码均由 AI Agent 执行；
> T4 两行是账号持有人以组员身份提交的任务 PR，代码与文档经本人阅读修改，但验证命令同样由
> AI 编码 agent 在本机执行（组员可在 review 自己重跑后改写本列）。
> 「本人审阅」「全组确认」等表述在没有 PR review 或本人确认记录时一律不写。

---

## 已知限制与需人工处理

- 仓库为私有，**尚未邀请另外 4 名组员**为 Collaborator；他们看不到仓库，也还没有任何贡献记录。
- GitHub Free + 私有仓库不支持强制分支保护 / Rulesets（API 403），PR review 规则靠人工执行。
- 技术取舍、应用领域与协作规则仍需五人共同确认；五个任务中**只有 T4 已提交 PR**（本表后两行），
  T1–T3 / T5 尚未认领，不能写成「全组已确认」。
- `eval/qa_set.csv` 的 35 题是 **`CORPUS_V0` 开发集**：`data/raw/frozen_manifest.json`（I1）还不存在，
  正式语料冻结后需重验 gold 引文；8 条 `unanswerable` 标注**至今无人写 `REVIEWED_BY`**，
  因此拒答类指标只能标为 provisional（`validate --require-reviewed` 会直接失败）。
- 真实 LLM API 调用需要密钥与费用方案；**尚未执行，零付费调用**。
- 贡献比例 + 全体签名单独一页是课程硬性要求，须在全员开工后据实填写，不得由 AI 代填。

---

## 组员追加记录模板

组员开始开发后，请各自在 PR 中追加一行（执行者写本人，验证写自己真实跑过的命令）：

```
| 日期 (GMT+8) | 阶段/任务 | 实际执行者 | 做了什么（含 PR 号） | 验证来源（本地命令 / 云端 CI，分开写） | 本人复核了什么 |
```

## T3 追加记录 / Retrieval delivery（2026-11-18）

本节仅追加本轮事实，以上旧状态不替代当前 GitHub 核验。

| 阶段 | 实际执行者 | 工作与证据 | 人工状态 |
| --- | --- | --- | --- |
| 现状与基线 | Hermes Agent | 核对 Issues/PR/main；PR #7/#8 已合入、#10 核查时仍 open；新隔离 clone，`t3-retrieval-diagnostics` 从 `4f865c10232f8d7890e9e1c019569276bcb9638e` 起步，无原有修改被覆盖。基线 124 passed / 2 skipped，Ruff 通过；项目独立 `.venv`，未修改依赖文件 | 本人尚未亲自复跑 |
| 实现与首次整合 | Hermes + Codex CLI Luna High / Sol Medium | TDD 增强向量库/Embedding，新增可导入诊断 CLI、自己的诊断测试和 RETRIEVAL 文档；首次整合 66 个 store/embedding 测试通过、全量 200 passed / 2 skipped、Ruff/help/offline-demo/ingest/retrieve/35QA 诊断通过 | Agent 执行，非人工批准 |
| 真实开发期验证 | Hermes Agent | 4 文档，fixed 28 块、paragraph 33 块；28 个同名 ID 跨集合隔离；重复 upsert 幂等，clear paragraph 不改 fixed；另一个 Python 进程逐字段回查两集合 61 块。105 条 top-k 回查与原文出处一致。A03/A14/A17/A18 本轮指定 gold 的首个达标 rank 为 6/4/8/5；A18 不能照抄旧的纯边界失败结论 | DEVELOPMENT / REAL_LOCAL；非正式指标 |
| 独立审查与修复 | 独立 Sol High Reviewer + 新 Sol Medium 修复 Worker + 主控 | 首轮实际复现多客户端策略污染与 float32 cosine 数值问题，另发现分箱边界及薄弱 NaN 测试。主控为直方图精确边界和导入 API 歧义补 RED/GREEN；存储/Embedding 修复、最终回归与复查结果在 PR 记录 | 仍须其他组员 review / Approve；贡献比例和签名不代填 |

原始逐条输出与输入/代码指纹保留在执行者本地交接包及 gitignored `eval/results/raw/`；每轮诊断含真实命令、UTC 日期、内容快照 SHA256、模型、collection 和参数。正式 I1 冻结未到位，未运行生成/付费 API，未发布 T3 自定义命中率。最终质量门禁与远端 CI 不以首次整合结果冒充，见本 PR 最新验收记录。

**最终本地验收（2026-11-18 04:41 HKT，Agent 执行）**：`pytest tests/test_store.py tests/test_embeddings.py` 106 passed；诊断测试 37 passed；全量 257 passed / 2 skipped；`ruff check .`、diagnostics `--help`、T4 `validate`、MOCK `offline-demo`、真实 `ingest` / `retrieve`、双集合独立进程回查与 35QA 诊断均通过。最终原始输出在 gitignored `eval/results/raw/t3-20261118-fixed-final/`；105 条 top-k 回查成功、每题深度排名完整，代码 SHA256 与运行版本一致。I1 缺失、unanswerable 人工复核 0/8，因此不称正式实验。云端 CI 与组员批准仍须看 PR 实际状态。

**独立终审**：Sol High 在修复后独立运行三个受影响文件 143 passed，结论通过、无阻断逻辑/安全缺陷；主控比对六个代码/测试 SHA256 与被审版本完全一致，并修掉文档 EOF 空行。另行真实跨进程并发写入检查中，一方写入、一方拒绝混策略，第三进程重开只有一种策略（Chroma 真实、向量 MOCK，零模型调用）。Windows 分支与大规模性能仍未验证；组员人工批准未代办。

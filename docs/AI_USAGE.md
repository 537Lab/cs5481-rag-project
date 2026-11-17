# AI 辅助使用记录（学术诚信 / 贡献声明用）

课程要求报告写明**每位成员的贡献比例与全体签名**。使用 Coding Agent / LLM 辅助开发时，
请在报告中如实披露，并保留可追溯记录。本文件是登记处，**不替代**报告里的贡献声明页。
项目定义与交付标准见 [`PROJECT_PLAN.md`](PROJECT_PLAN.md)。

## 原则

1. AI 可以辅助写代码、测试、文档和 debug，但**组员必须亲自检查并能解释实现**。
2. AI 生成的数字、运行结果、「已完成」声明**不算验证**；以自己真实执行的命令与输出为准。
   本地 Agent 执行、人工复核、GitHub Actions 云端 CI 是三件不同的事，必须分开记录。
3. 不把 MOCK 输出或 AI 编造的结果写进报告；不硬编码实验指标。
4. 贡献比例按**实际人工工作**填写（设计、复核、实验、分析、报告），不是按代码行数。
5. 报告最后一页需**单独一页**写贡献比例 + 全体成员签名（缺页会 desk reject）。

## 已记录的使用（bootstrap 与整理阶段；除 T4 外组员尚未开始）

| 日期 | AI / Agent | 用于 | 实际执行了什么 | 可核验的验证来源 | 人工复核 |
| --- | --- | --- | --- | --- | --- |
| 2026-11-13 | WorkBuddy AI | 基础工程 | 读课程 PDF、设计架构、生成全部基础代码与文档、抓取公开语料、编写测试 | Agent 本地执行 `pytest` / `ruff` / CLI；原始输出见 `RUNLOG.md` 第 1 节 | **待本人确认**（仓库内无可核验的人工复核记录） |
| 2026-11-13 | 外部 LLM 审阅（由账号持有人转述） | 审阅源码与运行记录，提出若干修改意见 | 审阅意见由账号持有人转述给 Agent；审阅原文未入库，**无法独立核验** | 修订后的验证见 `RUNLOG.md` 第 2 节（Agent 本地执行） | **待本人确认** |
| 2026-11-13 | WorkBuddy AI | 基线修订与仓库建立 | 按转述意见做最小修订；创建私有仓库与 CI；写任务包与启动文档 | Agent 本地执行 57 passed / 2 skipped；**云端** GitHub Actions `ci` 三次 `success`（见 `RUNLOG.md` 第 3 节） | **待本人确认**（CI 是机器验证，不等于人工复核） |
| 2026-11-13 | WorkBuddy AI | 仓库规范化整理 | 重写 README 与协作/架构文档、修正路径与事实、清理个人环境信息、核查本表与 `DEV_LOG.md` 的真实性、制定实验结果规范 | Agent 本地执行 `ruff` / `pytest` 57 passed 2 skipped / CLI；**云端** 该 PR 的 `ci / check` | **待本人确认**（建议在 PR review 中完成） |
| 2026-11-14 | WorkBuddy AI | 项目定义与协作计划定稿 | 核对课程 PDF 原文；新增 `docs/PROJECT_PLAN.md`；重写 README / `docs/TASKS.md`；清理预设身份标签；同步五个 Issue；只改文档，未改 `ragkit/` 代码 | Agent 本地执行 `ruff` / `pytest` / 文档链接与标签检查；**云端** 本 PR 的 `ci / check` | **待本人确认** |

> 上表**没有**任何一条可写成「某位组员亲自运行了这些命令」：命令由 AI Agent 执行，CI 由云端 runner 执行。
> 仓库账号持有人提供了账号、课程材料与任务指令，是否逐项人工复核需本人确认后补记。

## 组员登记模板（请各自追加，PR 时一并提交）

```
| 日期 | 任务包 | AI / Agent 名称 | 具体用途（生成什么、改哪些文件） | 我亲自复核了什么 | 我亲自跑了哪些命令 | 云端 CI 结果 | PR 号 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| YYYY-MM-DD | T3 |  |  |  |  |  | # |
```

## 组员追加记录（T4，任务包 #4）

| 日期 | 任务包 | AI / Agent 名称 | 具体用途（生成什么、改哪些文件） | 我亲自复核了什么 | 我亲自跑了哪些命令 | 云端 CI 结果 | PR 号 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-14 | T4 | Qoder（编码 agent）辅助写 | 起草 `eval/qa_set.csv` 题目候选、`eval/metrics.py`、`eval/judge_protocol.md`，并辅改 `eval/README.md`；未让 AI 写 gold 以外的实验数字 | 逐条比对 `qa_set.csv` 的 gold quote 确实来自 `data/raw/` 原文；确认 `metrics.py` 没硬编码任何命中率/正确率，无 `--grades` 时只输出 pending | 由 agent 在本机执行，本人未逐条重跑（review 时建议重跑）：`eval.metrics --help/validate/retrieval`、`ruff check .`、`pytest` | 待本 PR 的 `ci / check` | 分支 `t4-eval-qa-metrics` |
| 2026-11-15 | T4（同步修订，按 PR #8 的 I3/I4/I5） | Qoder（编码 agent）辅助改 | 按组员 5 条意见改 `eval/metrics.py`（I3 函数名、I4 JSONL、分母、`REVIEWED_BY` 门、I5 快照与 summary）与 `tests/test_eval_metrics.py`（+28 例，验收双文件 45 → 73 passed），同步 `eval/README.md`、`eval/judge_protocol.md`、`RUNLOG.md` 第 7/8 节；未重写首轮代码 | 逐条核对组员意见与 `docs/PROJECT_PLAN.md` §6.1 表格；阅读并改回 agent 写的两处描述不准的注释；**发现自己造成的一个真实问题**：合并 `origin/main` 时用 `git checkout --theirs` 处理 4 个冲突文档，把首轮写在 `RUNLOG.md`/`DEV_LOG.md`/`AI_USAGE.md` 里的 T4 记录一起覆盖了（已恢复，见 `RUNLOG.md` 第 8.7 节） | 同上：全部验证命令由 agent 执行（原始输出逐条存入 `RUNLOG.md` 第 8 节），本人阅读输出但**未亲手重跑**；因此本行不能记为「组员亲自执行」 | 待本 PR 的 `ci / check` 变绿后由另一位组员 review | 分支 `t4-eval-qa-metrics` |

> 注意：AI 辅写的 QA 题目仍须由**非作者的组员逐题校对原文**后才能当作正式 gold（gold 质量
> 直接影响命中率与正确率的可信度）；`judge_protocol.md` 规定 LLM 不得用于编撰或审查 gold quote。
> 两轮均**零付费 API 调用**，`answer_correctness` 尚无数字（人评未开始）。

## 写报告时建议披露的句子（示例，必须按实际情况改写）

> 本项目的基础工程脚手架、单元测试与部分文档由 AI 编码助手在仓库账号持有人授权下生成，
> 对应命令由该助手执行；仓库建立后的持续集成验证由 GitHub Actions 在云端完成。
> 各模块后续实现由对应负责人审阅、修改并亲自运行验证。实验数据均来自本组实际执行的命令，
> 未使用 AI 生成的模拟结果。各成员贡献比例与签名见本报告最后一页。

不要把示例句直接照抄：除 T4 之外，其余组员尚未开始开发，上表里的验证命令**全部是 AI Agent
而非组员本人跑出来的**，而正式的实验数据（冻结语料上的命中率与人工评分的正确率）至今为 0。
贡献比例页须在全员开工后据实填写。


## T3 追加记录 / T3 disclosure（2026-11-18）

本节为追加，不覆盖以上历史记录或替其他成员确认贡献。当前 T3 分支是 `t3-retrieval-diagnostics`，关联 Issue #3。

| 实际执行者 / Tool | 用途 | 已核实的模型配置与证据 | 人工环节 |
| --- | --- | --- | --- |
| Hermes 主控（当前会话报告 `gpt-6.1-sol`） | 核对最新 main/任务与权限，设计及实现诊断、测试、文档，整合并实跑 | 主控模型按会话标识记录；不将 CLI 子进程的推理档位冒充主会话已独立核验的档位 | 本人读代码、亲自跑关键命令与理解检查 **待完成** |
| Codex CLI Repository Explorer | 只读调用链与测试边界调查 | `--model gpt-6-luna -c model_reasoning_effort="high"`；实际启动头显示 Luna / high，冒烟返回 SMOKE_OK | 不是组员人工 review |
| Codex CLI Implementation / Review-fix Workers | 独立文件所有权下实现 store/embeddings 和其测试；审查后修复真实缺陷 | `gpt-6.1-sol / medium`，实际启动头验证；未让全部子任务继承 Sol High | 主控集成与复跑，不能记作本人亲手执行 |
| 独立 Codex CLI Reviewer | 读实际 diff、新文件、真实调用链与测试，复现问题 | `gpt-6.1-sol / high`，实际启动头验证；首轮指出交错客户端策略污染、float32 数值问题及分箱边界等，修复与复查记录以 PR 为准 | AI 审查不替代另一位组员 Approve |

- 本轮未改全局 Codex 配置、Agent Policy、共享契约、其他成员核心代码或依赖文件，未切换账号/启用额外付费额度。
- 初次边界测试漏设本地替身，意外触发免费模型下载；随后已修正测试并重跑。不能声称整个开发过程从未联网。真实本地 ONNX 检索本身也与离线 MOCK 测试分开记录。
- 输入为开发语料 `CORPUS_V0` 和现有 T4 开发 QA；没有生成/修改 gold 或伪造人工 `REVIEWED_BY`，不把机械字符定位写成人工 gold 质量复核。没有真实调用收费 Embedding / LLM / judge API；编码助手使用的是本轮明确授权的 Codex。
- Agent 实际执行了 pytest、Ruff、CLI、35 题本地诊断及双 collection 的独立进程持久化检查；最终命令/计数、审查修复和远端状态见本 PR、`DEV_LOG.md` 与 `RETRIEVAL.md`。未声明本人已亲自复跑或签字。
- 修复后独立 Sol High 终审实际通过三个受影响文件 143 项测试并核验真实运行指纹；主控再核对六份源码/测试哈希未改变，且追加了真实 Chroma 跨进程协作写入检查。以上仍是机器验证，不记成人工批准。

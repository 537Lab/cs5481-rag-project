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

## 组员追加记录（T2，任务包 #2）

| 日期 | 任务包 | AI / Agent 名称 | 具体用途（生成什么、改哪些文件） | 我亲自复核了什么 | 我亲自跑了哪些命令 | 云端 CI 结果 | PR 号 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-17 | T2 | Cursor Grok 4.7（编码 agent） | 新增 `eval/chunking_experiment.py` 与 `docs/CHUNKING_EXPERIMENT.md`；`ragkit/chunking.py` 只改模块说明；测试加在 `tests/test_chunking.py`。命中率调用 `eval.metrics.retrieval_hit_rate`，未改 `metrics.py`。开发数字只写进 gitignore 的 `eval/results/raw/`，未写入 `summary/` | 代码是 agent 写的。组员随后重跑了验收命令，见下一行；逐行阅读代码没有单独留下记录 | agent 先跑过一轮，输出在 `RUNLOG.md` 第 9 节。组员重跑见下一行，不要把两轮记成同一次 | 待本分支 PR 的 `ci / check` | 分支 `t2-chunking-experiment`，尚未开 PR |
| 2026-11-17 20:50 GMT+8 | T2 | 同上；本行是组员自己重跑，不是又一次生成代码 | 未改代码。在仓库根目录、已激活 `.venv` 的终端重跑任务卡上的验收命令 | 重跑了命令。终端里留存的最后一条是 `python -m eval.chunking_experiment`，exit 0。`comparison.json` 的 `generated_at` 为 `2026-11-17T12:50:10+00:00`，hit@1 / hit@3 与 20:43 的 agent 运行相同 | 组员本人重跑：`python -m pytest tests/test_chunking.py -q`、`python -m pytest -q`、`ruff check .`、`python -m eval.chunking_experiment --help`、`python -m eval.chunking_experiment`。屏幕上只留住了最后一条实验命令（exit 0）；pytest、ruff、`--help` 的通过行数没有留在终端记录里，这里不补写 | 仍待 PR 的 `ci / check` | 尚未开 PR |
| 2026-11-20 | T2（按 PR #10 审阅意见） | Cursor Grok 4.7（编码 agent） | 只改 `eval/chunking_experiment.py`、`tests/test_chunking.py` 和 `docs/CHUNKING_EXPERIMENT.md` 的一句说明。开发模式的 `--out` 不能落在 `eval/results/summary/`（含相对路径和符号链接）；`--formal` 把实际 `--qa` 交给门槛，并拒绝 `qa_set_dev_v0.csv` 以及任何非 `eval/qa_set.csv` 的路径。未改 `metrics.py`，未重跑对比实验，未改已有数字 | 待组员阅读这次门槛改动 | 待组员重跑 `pytest tests/test_chunking.py -q` 和 `ruff check .`。agent 在改完后本地跑这两条，结果写在 `docs/DEV_LOG.md` 本轮对应行 | 待推送后看本 PR 的 `ci / check` | #10 |

## 写报告时建议披露的句子（示例，必须按实际情况改写）

> 本项目的基础工程脚手架、单元测试与部分文档由 AI 编码助手在仓库账号持有人授权下生成，
> 对应命令由该助手执行；仓库建立后的持续集成验证由 GitHub Actions 在云端完成。
> 各模块后续实现由对应负责人审阅、修改并亲自运行验证。实验数据均来自本组实际执行的命令，
> 未使用 AI 生成的模拟结果。各成员贡献比例与签名见本报告最后一页。

不要把示例句直接照抄。T4 的验证命令仍是编码 agent 跑的。T2 的第一行也是 agent 跑的；第二行才是组员本人于 2026-11-17 20:50 重跑验收命令，其中只有 `python -m eval.chunking_experiment` 的退出码和 JSON 时间戳留在本机记录里。
T2 的 hit@k 仍是开发集上的检索，不是冻结语料上的正式实验；回答正确率至今为 0。
贡献比例页须在全员开工后据实填写。

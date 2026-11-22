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
| 2026-11-21 | T2（PR #14 冻结语料之后的重跑） | Cursor Grok 4.7（编码 agent） | 从 `origin/main` 开分支 `t2-chunking-frozen-corpus`。在 16 篇冻结语料上重跑 `python -m eval.chunking_experiment`。开发说明改为引用当次 `corpus_ref`，不再把已冻结语料写成 `CORPUS_V0`。改 `eval/chunking_experiment.py`、`tests/test_chunking.py`、`docs/CHUNKING_EXPERIMENT.md`。未改 `metrics.py`、语料、QA、`config.toml`。`--formal` 仍退出 2，未写 `summary/` | 待组员阅读这次重跑和门槛输出 | agent 跑了 `--formal`（exit 2）、开发对比（exit 0，JSON `generated_at` `2026-11-21T01:24:36+00:00`）、`ruff check .`、`pytest`。组员本人尚未重跑。原始输出在 `RUNLOG.md` 第 10 节 | 待本分支 PR 的 `ci / check` | 新分支，尚未开 PR |
| 2026-11-22 | T2（PR #15 正式 QA 合并后的正式对比） | Cursor Grok 4.7（编码 agent） | 从 `origin/main` 开分支 `t2-chunking-formal`。`python -m eval.chunking_experiment --formal` 退出码 0，写入 `eval/results/summary/chunking_comparison/`（`config.json`、`metrics.json`、`run.md`、`hit_rates.svg`）。`metrics.json` 带上分歧列表。改 `eval/chunking_experiment.py`、`tests/test_chunking.py`、`docs/CHUNKING_EXPERIMENT.md`。未改 `metrics.py`、语料、QA、`config.toml` | 待组员阅读正式结果 | agent 跑了 `--formal`（exit 0，`generated_at` `2026-11-22T02:13:25+00:00`）、`ruff check .`、`pytest`。组员本人尚未重跑。原始输出在 `RUNLOG.md` 第 12 节 | 待本分支 PR 的 `ci / check` | 新分支，尚未开 PR |
| 2026-11-22 | T2（正式对比图） | Cursor Grok 4.7（编码 agent） | 只改 `hit_rates.svg` 的布局：数字改到柱子右侧的固定槽里，并加宽画布。用已有 `metrics.json` 重画，没有重跑检索，没有改命中率。`eval/chunking_experiment.py`、`tests/test_chunking.py` | 待组员看图 | agent 跑了 `pytest tests/test_chunking.py::test_formal_bundle_keeps_the_hit_rate_objects` 和 `ruff`。组员本人尚未重跑 | 待本分支 PR 的 `ci / check` | 新分支，尚未开 PR |

## 组员追加记录（T1，任务包 #1）

| 日期 | 任务包 | AI / Agent 名称 | 具体用途（生成什么、改哪些文件） | 我亲自复核了什么 | 我亲自跑了哪些命令 | 云端 CI 结果 | PR 号 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-17 | T1 | OpenAI Codex（编码 agent） | 辅助认领 Issue #1；修改 `ragkit/loaders.py`，增加 UTF-8、必填出处/许可、重复路径与重复内容校验；扩充 `tests/test_loaders.py` 边界测试；未采集或改动正式语料 | **尚未由负责人逐项人工复核**；需在 PR review 时阅读实现并确认能解释失败策略与 MOCK 例外 | 无；以下命令均由 Codex 在本机执行：`pytest tests/test_loaders.py -q`、`pytest -q`、`ruff check .`、`ragkit.cli offline-demo` | `ci / check` 已通过 | PR #13 |

## 组员追加记录（T1，正式语料快照）

| 日期 | 任务包 | AI / Agent 名称 | 具体用途（生成什么、改哪些文件） | 我亲自复核了什么 | 我亲自跑了哪些命令 | 云端 CI 结果 | PR 号 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-19 | T1 | OpenAI Codex（编码 agent） | 按全组确认的 Kubernetes v1.35 方向核验 CC BY 4.0 许可与 12 个固定来源；改写采集脚本；生成正式语料、`manifest.json`、`frozen_manifest.json`、来源表与统计文档；定位并最小修正 T4 开发 QA 的两处集成冲突 | **尚未由负责人逐项人工复核**；需在 PR review 时抽查固定来源、清洗前后正文、SHA-256 和 T4 兼容修正 | 无；以下均由 Codex 在本机执行：两次 `fetch_corpus.py` 与全量哈希比较、`pytest`、`ruff check .`、真实 `cli ingest`（16 文档 → 651 chunks）、真实 `cli retrieve` | 待本 PR 的 `ci / check` | 分支 `t1-corpus-kubernetes-v135` |

### T1 清洗遗漏修订（2026-11-19，PR #12）

Codex 对照固定来源确认旧清洗器遗漏了 2 处共享 prerequisites、15 处 YAML
code_sample，以及 8 处 currentVersion 占位符。修订后从同一 commit 内联依赖，
保留版本值、图片说明及 API 标签；未展开的 include/code_sample 会报错。
本地 Agent 验证：132 passed / 2 skipped，Ruff 通过，重复采集逐文件字节一致；
真实入库 16 篇 → 668 chunks。新快照为 `cs5481-k8s-v135-16docs-36fd3eedf33f`，
替代 PR 初版快照；旧字符偏移及 chunk 编号需重新生成。人工复核与云端 CI 尚待确认。

### T1 来源追踪与交接准备（2026-11-19，PR #12）

Codex 为 28 个固定上游文件记录 URL 与 SHA-256（12 个页面、1 个共享 include、
15 个 YAML 示例），补充来源署名和 T2–T5 交接说明；下载遇到临时 TLS 故障后，
加入最多三次重试。正文、doc_id 和 corpus_id 未变。本地检查两种基础分块策略：
fixed 668 chunks、paragraph 775 chunks，全部偏移逐字匹配、出处及许可一致，
覆盖全部非空白正文。该检查不属于正式检索质量对比实验。人工复核仍待完成。

## 写报告时建议披露的句子（示例，必须按实际情况改写）

> 本项目的基础工程脚手架、单元测试与部分文档由 AI 编码助手在仓库账号持有人授权下生成，
> 对应命令由该助手执行；仓库建立后的持续集成验证由 GitHub Actions 在云端完成。
> 各模块后续实现由对应负责人审阅、修改并亲自运行验证。实验数据均来自本组实际执行的命令，
> 未使用 AI 生成的模拟结果。各成员贡献比例与签名见本报告最后一页。

不要把示例句直接照抄。T4 的验证命令仍是编码 agent 跑的。T2 的第一行也是 agent 跑的；第二行才是组员本人于 2026-11-17 20:50 重跑验收命令，其中只有 `python -m eval.chunking_experiment` 的退出码和 JSON 时间戳留在本机记录里。
T2 在 2026-11-22 对已冻结语料和 PR #15 的正式 QA 跑了 `--formal`（exit 0）。那次命令是 Cursor 编码 agent 执行的，组员本人尚未重跑。回答正确率至今没有在这次对比里计算。
贡献比例页须在全员开工后据实填写。
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
## 组员追加记录（T1，任务包 #1）

| 日期 | 任务包 | AI / Agent 名称 | 具体用途（生成什么、改哪些文件） | 我亲自复核了什么 | 我亲自跑了哪些命令 | 云端 CI 结果 | PR 号 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-17 | T1 | OpenAI Codex（编码 agent） | 辅助认领 Issue #1；修改 `ragkit/loaders.py`，增加 UTF-8、必填出处/许可、重复路径与重复内容校验；扩充 `tests/test_loaders.py` 边界测试；未采集或改动正式语料 | **尚未由负责人逐项人工复核**；需在 PR review 时阅读实现并确认能解释失败策略与 MOCK 例外 | 无；以下命令均由 Codex 在本机执行：`pytest tests/test_loaders.py -q`、`pytest -q`、`ruff check .`、`ragkit.cli offline-demo` | `ci / check` 已通过 | PR #13 |

## 组员追加记录（T1，正式语料快照）

| 日期 | 任务包 | AI / Agent 名称 | 具体用途（生成什么、改哪些文件） | 我亲自复核了什么 | 我亲自跑了哪些命令 | 云端 CI 结果 | PR 号 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-19 | T1 | OpenAI Codex（编码 agent） | 按全组确认的 Kubernetes v1.35 方向核验 CC BY 4.0 许可与 12 个固定来源；改写采集脚本；生成正式语料、`manifest.json`、`frozen_manifest.json`、来源表与统计文档；定位并最小修正 T4 开发 QA 的两处集成冲突 | **尚未由负责人逐项人工复核**；需在 PR review 时抽查固定来源、清洗前后正文、SHA-256 和 T4 兼容修正 | 无；以下均由 Codex 在本机执行：两次 `fetch_corpus.py` 与全量哈希比较、`pytest`、`ruff check .`、真实 `cli ingest`（16 文档 → 651 chunks）、真实 `cli retrieve` | 待本 PR 的 `ci / check` | 分支 `t1-corpus-kubernetes-v135` |

### T1 清洗遗漏修订（2026-11-19，PR #12）

Codex 对照固定来源确认旧清洗器遗漏了 2 处共享 prerequisites、15 处 YAML
code_sample，以及 8 处 currentVersion 占位符。修订后从同一 commit 内联依赖，
保留版本值、图片说明及 API 标签；未展开的 include/code_sample 会报错。
本地 Agent 验证：132 passed / 2 skipped，Ruff 通过，重复采集逐文件字节一致；
真实入库 16 篇 → 668 chunks。新快照为 `cs5481-k8s-v135-16docs-36fd3eedf33f`，
替代 PR 初版快照；旧字符偏移及 chunk 编号需重新生成。人工复核与云端 CI 尚待确认。

### T1 来源追踪与交接准备（2026-11-19，PR #12）

Codex 为 28 个固定上游文件记录 URL 与 SHA-256（12 个页面、1 个共享 include、
15 个 YAML 示例），补充来源署名和 T2–T5 交接说明；下载遇到临时 TLS 故障后，
加入最多三次重试。正文、doc_id 和 corpus_id 未变。本地检查两种基础分块策略：
fixed 668 chunks、paragraph 775 chunks，全部偏移逐字匹配、出处及许可一致，
覆盖全部非空白正文。该检查不属于正式检索质量对比实验。人工复核仍待完成。

## 写报告时建议披露的句子（示例，必须按实际情况改写）

> 本项目的基础工程脚手架、单元测试与部分文档由 AI 编码助手在仓库账号持有人授权下生成，
> 对应命令由该助手执行；仓库建立后的持续集成验证由 GitHub Actions 在云端完成。
> 各模块后续实现由对应负责人审阅、修改并亲自运行验证。实验数据均来自本组实际执行的命令，
> 未使用 AI 生成的模拟结果。各成员贡献比例与签名见本报告最后一页。

不要把示例句直接照抄。T4 的验证命令仍是编码 agent 跑的。T2 的第一行也是 agent 跑的；第二行才是组员本人于 2026-11-17 20:50 重跑验收命令，其中只有 `python -m eval.chunking_experiment` 的退出码和 JSON 时间戳留在本机记录里。
T2 的 hit@k 仍是开发集上的检索，不是冻结语料上的正式实验；回答正确率至今为 0。
贡献比例页须在全员开工后据实填写。

## T5 additional records

| 2026-11-21 | T5 offline handoff smoke check | Codex | Added `demo.validate_export` to export two synthetic I4 answers, consume them with the existing T4 loader and verify MOCK provenance. Agent ran the command and Ruff successfully; no paid API or formal metrics. | Human review and personal rerun Pending. |

| 2026-11-21 | T5 demo guide | Codex | Added a classroom walkthrough, REAL-run prerequisites and synthetic qualitative failure examples. Agent executed `python -m demo.run` and an explicit MOCK batch export (2 records); no real LLM call or formal metric. | Human review and personal rerun Pending. |

| 2026-11-20 | T5 | Codex | Added heuristic citation coverage, invalid-output refusal, batch I4 export, offline demo and tests on branch t5-generation-validation. Agent ran the checks documented in ANSWER_QUALITY.md. | User review and personal rerun Pending. No human review signatures or formal metrics supplied. |
| 2026-11-20 | T5 follow-up | Codex | Added shared refusal diagnostics, MOCK batch subprocess coverage and atomic-publication failure cleanup tests, updated demo instructions. | Agent executed 37 T5/offline tests and 156 passing tests with test_store.py excluded (3 skipped). Full suite still crashes in Chroma outside sandbox. Human code review and personal rerun Pending. |

## T4 additional records（本分支 `t4-k8s-qa-set`，PR #15）

> 解这次冲突的口径见 `RUNLOG.md` 第 11 节：main 侧已有内容一字不动，本分支自己的行
> 只做追加，因此本节以上那份带重复块（一级标题在第 1 与第 96 行）的 `docs/AI_USAGE.md`
> 是原样继承的，不在本 PR 里删别人写的行；已知缺陷由 #16 / #17 的作者另开 PR 修。
> 本节以下几行取代上文里属于 T4 的旧口径（含标题句中「除 T4 外组员尚未开始」——
> T4 的登记就在下表）。

| 日期 | 任务包 | AI / Agent 名称 | 具体用途（生成什么、改哪些文件） | 我亲自复核了什么 | 我亲自跑了哪些命令 | 云端 CI 结果 | PR 号 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-20 | T4（正式 Kubernetes QA 集，分支基于尚未合并的 PR #14） | Qoder（编码 agent）辅助写 | 35 题 `git mv` 为 `eval/qa_set_dev_v0.csv`；生成正式集 `eval/qa_set.csv`（36 条：26 answerable + 10 unanswerable，逐字引自 #14 冻结快照的 12 篇文档）与签名工作单 `eval/review/formal_qa_review.md`；改 `eval/metrics.py`（`token_occurs()` 词边界、`qa_set_status()` 由文件与行内容推导、`assert_formal_inputs()` 两类新拒绝）、`tests/test_eval_metrics.py`（67 → 82 例）、`eval/README.md`、`eval/judge_protocol.md`、`RUNLOG.md` 第 11 节；新增 `.gitattributes` | **题目正文、gold 行号与 `notes` 理由均由 agent 起草**（生成脚本留在本地 `.tmp/`、未入库，因此 csv 是唯一正式工件）；本人抽查了按行号切出的引文，拦下并改掉 agent 写的四处问题（见 `RUNLOG.md` 第 11.4 节）；确认 agent **没为任何一条 `unanswerable` 填 `REVIEWED_BY`**，也没把 hit@k 写进代码常量 | 全部由 agent 在本机执行、本人阅读但未亲手重跑：`ruff check .`、`pytest`（148 passed / 2 skipped）、`validate`（正式与开发两份均 `exit=0`）、`validate --require-reviewed`（`exit=2`）、`cli ingest`（16 docs → 668 chunks）、`retrieval`（两份 hit@k）；原始输出见 `RUNLOG.md` 第 11 节 | 未执行：run 页报 "The job was not started because recent account payments have failed or your spending limit needs to be increased"（账号级 Actions 计费，job 未被调度）；已用 `git worktree` 干净检出复现 ruff + pytest 全绿（`RUNLOG.md` 第 11.9 节） | 分支 `t4-k8s-qa-set` |
| 2026-11-21 | T4（合并 `origin/main` 后的冲突处理） | Qoder（编码 agent）执行，组员本人阅读 | 只动 `RUNLOG.md`、`docs/DEV_LOG.md`、`docs/AI_USAGE.md` 三个文档：main 上 T2 的第 9 节与本分支 T4 的第 9 节撞号，**T4 一节整体改编号为第 10 节**并同步全部交叉引用，T2 的原文一字未改；代码层交给 git 自动合并，未手工改写 T1/T2 的实现 | 逐条确认解冲突没有丢掉任何一边的记录（合并前后行数与标题都对照过）；确认没有替组员补写任何「亲自执行/复核」表述；另：agent 试图用浏览器更新 PR 描述，因会话未登录而按预定停止条件退出（**未输入任何凭据**），但从 PR 列表页得到 #15 / #16 与两个新账号，据此更正了 DEV_LOG 里「T5 无人认领」的错误推断（见 `RUNLOG.md` 第 11.11 节） | 全部由 agent 在本机执行、本人未亲手重跑：`ruff check .` 通过、`pytest` **168 passed / 2 skipped**、`validate`（正式与开发两份 `exit=0`）、`validate --require-reviewed` `exit=2`、`chunking_experiment --formal` `exit=2`（只剩未签名拒答一条理由） | PR 页显示 1 successful check（组员浏览器截图，仓库内无可核验 run id）；11-20 那轮的账号级 Actions 计费故障已恢复 | 分支 `t4-k8s-qa-set` |
| 2026-11-21 | T4（第二次合并 `origin/main`（`0ee7d5e`，含 T5 的 PR #16），并把拒答题核对转交组员） | Qoder（编码 agent）执行，组员本人阅读 | 解唯一冲突 `docs/AI_USAGE.md`：本分支全文保留，main 新增的 `## T5 additional records`（2 行）逐字节原样附到文件末尾，别人写的行一字未改（脚本断言追加块与 main 相同、本分支行零丢失）；本次合并未触碰 `eval/`、`tests/`、`data/raw/`、`.gitattributes`。另用 `metrics.token_occurs()` 逐条重跑 10 题共 23 个声明 token（个数依次 3/2/2/2/3/2/2/3/2/2）确认全部不存在，据此生成 KN01–KN10 判定表与候选段落摘录，以组员已登录会话发成 PR #15 评论（`issuecomment-7058643165`） | 阅读并确认解冲突只做追加、**没有替任何组员写 `REVIEWED_BY`**（仍 0/10）；读回 `537Lab` 的 non-approving review 原文并逐条对仓库核验——它对 KN03 的疑问（`services` 页链到 `.go` 源码）针对的是 `93bfb03`，而 `b2263d9` 已查明该链接实际指向 `pkg/kubelet/envvars/envvars.go`，与 kube-proxy 的实现语言无关 | 全部由 agent 在本机执行、本人未亲手重跑：`ruff check .`、`pytest -o addopts="" -q`（**186 passed / 2 skipped**）、`validate`（正式与开发均 `exit=0`）、`validate --require-reviewed`（`exit=2`）、`chunking_experiment --formal`（`exit=2`） | 已取得的 run：`44779731964`（旧 head，49s）、`44780982969`（`ac173a2`，29s）、`44877582328`（`f4cc5fa`，**succeeded in 28s**，步骤含 Static check (ruff) / Tests (offline) / Verify no secret）——本列更正上一行的「无可核验 run id」 | 分支 `t4-k8s-qa-set`（PR #15） |
| 2026-11-21 | T4（更正上一行已过期的口径 + 登记人工复核落地） | Qoder（编码 agent）执行取证与登记，组员本人阅读 | **本轮未改任何代码**：`git fetch` 后发现远端分支 head 已被他人从 `11470fb` 推到 `d39d658`（`ziqilin669` 经 GitHub 网页上传已签名的 `eval/qa_set.csv` 与签名工作单；`ldk13856478627-cell` 把门禁测试由「关闭」翻为「打开」），本地 `git merge --ff-only` 跟上，未为追赶而制造新提交；逐行 csv 比对确认除 `notes` 外无列被改、`b2263d9` 的 KN03 纠正未被回退；在 `d39d658` 的 detached worktree 实跑四项命令；登记写入 `RUNLOG.md` §11.13 / §11.14 | 本人阅读了 agent 输出的 diff 与四项命令结果。**人工复核本身不是 agent 做的**：10 条 `REVIEWED_BY` 由 `ziqilin669` 本人逐条复核后以自己账号写入（签名原文：`Reviewer name(s) and date: ziqilin669, 2026-11-21`、`Items changed after review: none; KN07 kept as written`）。同时记录两处我怀疑过但**实测不成立**的问题（`REVIEWED_BY` 写在 `ABSENT_TOKENS` 同一行尾不会污染解析；负向对照测试仍在），以及一处待 T2 表态的越界改动（T1 账号改了 T2 拥有的 `tests/test_chunking.py`） | 全部由 agent 在 `d39d658` 本机执行、本人未亲手重跑：`ruff check .` 通过、`pytest -o addopts="" -q` **186 passed / 2 skipped**、`validate` `exit=0`（`10/10 carry REVIEWED_BY`）、`validate --require-reviewed` **`exit=0`**（上一行仍为 `exit=2`，已过期） | 本轮未取 —— 该 head 由他人推送且 PR 处于冲突态，页面 Checks 未复核，不写云端结论 | 分支 `t4-k8s-qa-set`（PR #15） |
| 2026-11-21 | T4（第三次合并 `origin/main`（`30e6e98`，含 #18 / #20），解 6 处文档冲突） | Qoder（编码 agent）执行，组员本人阅读 | **本轮只动文档，未改代码与测试**：`git merge origin/main` 后共 6 处冲突（`RUNLOG.md` 1、`docs/DEV_LOG.md` 1、本文件 4），代码与测试 0 处。本文件的解法按上一行登记的口径：main 那 195 行**逐字作为前缀继承**（包括一级标题重复出现在第 1 与第 96 行、`0ee7d5e → main` 为 `+195 / −98` 的已知缺陷，本 PR 不删别人写的 98 行），本分支自己的行只追加到本节；`RUNLOG.md` 里 T4 一节改号为第 11 节（main 上 T2 已占用第 10 节，那份 46 行逐字不动） | 本人阅读了 agent 给出的解冲突口径与 37 项断言脚本的输出；确认**没有删改任何一行别人写的记录**；改号脚本只作用于本分支自己的行，**T2 指向自己第 10 节的指针未被代改**；本行与上一行仍只反映 agent 取证，人工复核仍由 `ziqilin669` 本人于上一行完成 | 全部由 agent 在本机（`.venv`，Python 3.13.5）执行、本人未亲手重跑：合并后 `ruff check .` 通过、`pytest -o addopts="" -q` **195 passed / 2 skipped**（合并前 186，+9 例来自 #18 / #20）、`validate` `exit=0`、`validate --require-reviewed` **`exit=0`**；过程见 `RUNLOG.md` 第 11.15 节 | 本轮未取 —— 本次合并产生的 head 尚未推送，不写云端结论 | 分支 `t4-k8s-qa-set`（PR #15） |

**人工评分的正确率仍为 0**（无答案产物、无人评分）；10 条拒答题已由 `ziqilin669` 本人逐条复核并署名（2026-11-21，见 `RUNLOG.md` §11.13），但 26 道 answerable 题仍未经第二人逐题阅读。

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

### 2026-11-21 T3 同步说明（Agent 核查 GitHub）

PR #14 的冻结 Kubernetes 语料已进入 `main`，PR #15 的正式 QA 人工签名仍待完成。上方 T3 记录只描述 2026-11-18 的四篇开发语料实验；该历史记录不能替代冻结语料上的重跑。此次仅同步分支及保全披露记录，没有在本执行环境运行 ONNX 检索或伪造新的实验数字；T3 新实验与学生本人亲自复核均待完成。旧版其它成员登记原样保留。

### 2026-11-22 T3 同步与 T4 API 兼容修复（ChatGPT / GitHub 连接）

本次由 ChatGPT 在账号持有人请求下检查 PR #11 和最新 main：保全 main 的已有记录并追加原 T3 分支披露；修复 T3 对已移除 `QA_SET_STATUS` 的引用，改用 T4 新增的 `qa_set_status(qa, items)`，不修改 T4 文件。PR #15 的正式 36QA 与全部 10 个拒答人工签名现已合入；PR #23/T2 的正式策略对比数字只作为独立交叉检查，不登记为 T3 实跑。
本次仅通过 GitHub API 读取源码和组织合并；当前执行容器没有 Chroma/ONNX，且不能联网下载依赖，因此**没有在此环境运行本地模型、真实检索诊断或完整 pytest**。GitHub CI 应在最终 head 上另核查，学生本人阅读/重跑与他人 Approve 仍是待办。不虚构人工签名或实验数据。

### 2026-11-22 T3 冻结输入真实运行（Codex / 本机）

Codex 在 PR #11 的 `c4516bf29317270b876193f66e864f8f053f785f` 独立检出中使用已缓存的 ONNX `all-MiniLM-L6-v2` 与本机 Chroma，实际进行 fixed / paragraph 入库，分别执行 36 道正式 QA 的完整排名诊断并用新进程复查。执行命令、时间、输入和输出指纹见 [RETRIEVAL.md](RETRIEVAL.md)。测试 `143 passed`、全量 `328 passed / 2 skipped`，Ruff 通过。

本轮实验使用本机 embedding，生成、收费 embedding 及 judge 的 API 调用均为 0。Codex 补充了本节、开发记录和检索复跑说明。刘悦伟本人复核与组员 Approve 均待完成。

### 2026-11-22 T3 合并后维护（Draft PR #27；ChatGPT / GitHub 连接）

- 用户授权继续推进 T3 后，ChatGPT 通过 GitHub 连接只读审查已合并 `ragkit/store.py` 与 `tests/test_store.py`，发现先打开的第二个 Chroma 客户端在首个客户端 `clear()` 重建 collection 后可能保留过期 UUID 的读路径。创建独立分支 `t3-postmerge-read-rebind`；仅在 T3 自有 `tests/test_store.py` 中新增真实 Chroma 回归测试。
- GitHub Actions [RED run 45028359710](https://github.com/537Lab/cs5481-rag-project/actions/runs/45028359710) 复现该故障：`test_preopened_client_reads_after_other_client_rebuild` 的 `second.count()` 报 `chromadb.errors.NotFoundError`。这是真实云端运行证据，不是模型推测。
- ChatGPT 随后仅在 `ragkit/store.py` 中添加按需的 stale-reader 重绑定：正常读取不追加查找，读操作因 collection UUID 失效抛出 `NotFoundError` 时，使用 collection 写锁获取当前句柄并校验策略绑定，然后重试一次；同时更新 `docs/RETRIEVAL.md`。后续 GREEN / 最终精确 HEAD 以 PR #27 的 CI 记录为准。
- 当前助手环境没有本机 Chroma/ONNX 运行依赖，未在用户 Mac 上亲手重跑；上述实测来自 GitHub Actions。没有收费 embedding / LLM / judge 请求，没有修改冻结语料、正式 QA、T4 指标、旧 raw 实验产物或其他模块。AI 编码/日志不冒充学生本人亲自验收，也不冒充非作者组员的人工 APPROVED / merge。

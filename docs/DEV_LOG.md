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

**截至本记录，仓库账号持有人本人在做 T4。main 上已合并的组员 PR：T1 的 #13（loader 加固）、
T2 的 #10（分块对比）、T4 的 #7（评测指标）**；仍 open：T1 的 #14（冻结 Kubernetes 语料）、
T3 的 #11（检索诊断）、T4 本轮的 **#15**（分支 `t4-k8s-qa-set`）、T5 的 **#16**。
因此「全组已确认」一类表述仍不能写。以下 bootstrap 内容全部属于
规范化与文档定稿阶段，由 AI Agent 在仓库账号持有人授权下执行。是否逐项人工复核，
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
| 2026-11-15 | T4 同步修订（按 PR #8 接口 I3/I4/I5） | 组员（仓库账号持有人，PR 作者）+ AI 编码 agent 辅助，组员本人阅读并修改 | 处理组员 5 条意见：`git merge origin/main`（4 处文档冲突以 main 为准）；按 I3 暴露四个公开指标函数；按 I4 读 `eval/answers/<run_id>.jsonl` 与 `retrieved_chunk_ids`；正确率分母改为已评分的 answerable 题并新增 `grading_coverage`；`ABSENT_TOKENS` 降为必要条件 + `REVIEWED_BY`/`--require-reviewed`/`--formal` 复核门；按 I5 字段名写 config 快照与 summary 三件套；35 题定为 `CORPUS_V0` 开发集。测试 39 → 67 例（验收双文件 45 → 73），首轮用例全部保留 | Agent 本地执行：`ruff check .` 通过；`pytest` **124 passed / 2 skipped**（验收双文件 73 passed）；`validate`、`retrieval`（hit@1 16/27、hit@3 23/27，与首轮一致）、`score --run-id`、四道护栏的 `exit=2` 逐一实跑。原始输出见 `RUNLOG.md` 第 8 节。**云端验证**：本 PR 的 `ci / check`（未拿到可核验的 run 结论） | 已由仓库账号持有人合并进 main（`4f865c1` = PR #7 merge commit，git 可验）；无其他组员 review 记录 |
| 2026-11-17 20:43 GMT+8 | T2 分块对比（分支 `t2-chunking-experiment`，尚未开 PR） | Cursor Grok 4.7 编码 agent | 新增 `eval/chunking_experiment.py`：`fixed` / `paragraph` 分 collection 入库，命中率只调用 `retrieval_hit_rate()`。`chunking.py` 只改说明。写 `docs/CHUNKING_EXPERIMENT.md`。未改契约、`config.toml`、`metrics.py`、语料与 QA | Agent 本地执行：`ruff check .` 通过；`pytest` **134 passed / 2 skipped**；`--help` exit 0；`--formal` exit 2 且未创建 `summary/chunking_comparison/`；开发对比 exit 0。`fixed` hit@1 16/27、hit@3 23/27，`paragraph` hit@1 17/27、hit@3 23/27。零付费调用。原始输出见 `RUNLOG.md` 第 9 节。**云端验证**：尚未开 PR | 组员重跑见下一行；逐行阅读代码未另行记录 |
| 2026-11-17 20:50 GMT+8 | T2 组员重跑验收命令 | 组员本人，仓库根目录，已激活 `.venv` | 未改代码。重跑任务卡列出的 pytest、ruff、`--help` 和开发对比 | 终端只保留最后一条：`python -m eval.chunking_experiment`，exit 0。JSON `generated_at` 为 `2026-11-17T12:50:10+00:00`，汇总与 20:43 的 agent 运行相同。pytest、ruff、`--help` 的屏幕输出没有留在终端文件里，不在此补写通过行数。见 `RUNLOG.md` 第 9.1 节。**云端验证**：尚未开 PR | 组员重跑了这些命令 |
| 2026-11-20 | T2 按 PR #10 审阅意见补门槛 | Cursor Grok 4.7 编码 agent | 开发运行不能把 `--out` 指到 `eval/results/summary/`；`--formal` 使用实际 QA 路径，并拒绝已提交集合以外的文件。未改 `eval/metrics.py`，未重跑命中率 | Agent 本地：`ruff check .` 通过；`pytest` **137 passed / 2 skipped**（`tests/test_chunking.py` 27 passed，含相对路径、符号链接、`qa_set_dev_v0.csv` 三个反例）。未重跑对比实验，已有 hit 数字不变。组员本人尚未重跑这轮。**云端验证**：待推送到 PR #10 | 待组员阅读门槛改动 |
| 2026-11-21 09:24 GMT+8 | T2 在 PR #14 冻结语料上重跑 | Cursor Grok 4.7 编码 agent，分支 `t2-chunking-frozen-corpus` | 16 篇冻结语料、同一开发 QA、同一 size/overlap/top_k。命中率仍只调用 `retrieval_hit_rate()`。`--formal` 因 N01–N08 无 `REVIEWED_BY` 退出 2，未写 `summary/`。开发说明改为跟着 `corpus_ref` 走 | Agent 本地：`ruff check .` 通过；`pytest` **154 passed / 2 skipped**；`--formal` exit 2；开发对比 exit 0。`fixed` 668 chunks，hit@1 16/27、hit@3 23/27；`paragraph` 775 chunks，hit@1 17/27、hit@3 23/27。零付费调用。原始输出见 `RUNLOG.md` 第 10 节。组员本人尚未重跑。**云端验证**：尚未开 PR | 待组员阅读这次重跑 |
| 2026-11-20 | T4 第二轮（正式 Kubernetes QA 集，分支 `t4-k8s-qa-set`，**基于尚未合并的 PR #14**） | 组员（仓库账号持有人，PR 作者）+ AI 编码 agent 辅助，组员本人阅读并修改 | 复核 #14 对 `eval/qa_set.csv` / `tests/test_eval_metrics.py` 的调整（含只在 Windows 复现的换行哈希缺陷根因）；35 题 `git mv` 为 `eval/qa_set_dev_v0.csv`（保留历史），新建正式集 `eval/qa_set.csv`：36 条 = 26 answerable + 10 unanswerable，逐字引用 #14 冻结快照的 12 篇 Kubernetes 文档并全覆盖；`metrics.py` 三处改造（`token_occurs()` 词边界、`qa_set_status()` 由文件与行内容推导、`assert_formal_inputs()` 增两类拒绝）；新增签名工作单 `eval/review/formal_qa_review.md`；`.gitattributes`（`* text=auto eol=lf`）；测试 67 → 82 例 | Agent 本地执行：`ruff check .` 通过；`pytest` **148 passed / 2 skipped**；`validate`（正式集与开发集均 `exit=0`）、`validate --require-reviewed` `exit=2`、`cli ingest` 16 docs → 668 chunks、`retrieval` 正式集 **hit@1 8/26=0.3077 / hit@3 18/26=0.6923**，同一索引上开发集 16/27=0.5926 / 23/27=0.8519。原始输出见 `RUNLOG.md` 第 11 节。**零付费调用**。**云端验证**：未执行 —— run 页 Annotation 为 "The job was not started because recent account payments have failed or your spending limit needs to be increased"（账号级 Actions 计费，job 从未被调度，非代码失败）；已用干净检出（`git worktree`，全 LF）复现 `ruff check .` 通过 + `pytest -q` `exit=0`，见 `RUNLOG.md` 第 11.9 节 | **10 条拒答标注无人签名**（`REVIEWED_BY` 全空），故 `--require-reviewed` / `--formal` 仍关闭；题目亦未经第二人逐题阅读，待组员在 `eval/review/formal_qa_review.md` 签署 |
| 2026-11-21 | T4 第二次合并 `origin/main`（`0ee7d5e`，含 T5 的 PR #16）+ 把拒答题人工核对转交组员（分支 `t4-k8s-qa-set`，PR #15） | AI 编码 agent 执行，组员本人阅读 | 唯一冲突 `docs/AI_USAGE.md` 采用**纯追加**解法：本分支全文保留，main 新增的 `## T5 additional records`（含 2 行 T5 记录）逐字节原样附到文件末尾，别人写的行一字未动；脚本断言本分支行零丢失、追加块与 `origin/main` 相同。这次合并未改动 `eval/`、`tests/`、`data/raw/`、`RUNLOG.md` 与 `.gitattributes`（`git diff --cached --name-only HEAD` 只列出 T5 的 9 个文件）。另在 PR #15 发出 KN01–KN10 逐题核对请求（判定表 + 候选段落摘录），并读回 `537Lab` 的 non-approving review 原文逐条比对 | Agent 本地执行：`ruff check .` 通过；`pytest -o addopts="" -q` **186 passed / 2 skipped**（比上轮 168 多 18 例，增量来自 #16 的 `tests/test_generation.py`）；`validate` 正式与开发均 `exit=0`、`validate --require-reviewed` `exit=2`（`REVIEWED_BY` 仍 0/10）、`chunking_experiment --formal` `exit=2`（拒绝理由只剩未签名一条）；23 个声明 token 逐条重跑词边界机检均不存在。**零付费调用**。**云端验证**：`f4cc5fa` 上 `ci / check` **succeeded in 28s**（run `44877582328` / job `136765583598`，步骤含 Static check (ruff)、Tests (offline)、Verify no secret，唯一 annotation 仍只是 Node.js 20 弃用警告）；同时更正下一行「仓库内无可核验 run id」——另已取得 run `44779731964`（旧 head，49s）与 `44780982969`（`ac173a2`，29s） | 本轮**没有发生任何人工核对**：`REVIEWED_BY` 仍 0/10；核对请求已由 agent 在组员已登录会话上发成 PR 评论（`issuecomment-7058643165`，以 `wangsaorui` 名义），**待 `ziqilin669` 本人逐条回答后由他自己落笔** |
| 2026-11-21 | T4 合并 `origin/main`（`848d7c6`）后的冲突处理（分支 `t4-k8s-qa-set`） | AI 编码 agent 执行，组员本人阅读 | 解 `RUNLOG.md`、本文件与 `docs/AI_USAGE.md` 三处冲突：main 上 T2 的第 9 节与本分支 T4 的第 9 节撞号，**T4 一节整体改编号为第 10 节**（含内部小节号与交叉引用），T2 的第 9 节与三行记录原文保留未改；代码层由 git 自动合并（`ragkit/loaders.py`、`ragkit/chunking.py`、`eval/chunking_experiment.py`、两个测试文件），未手工改写他人实现 | Agent 本地执行：`ruff check .` 通过；`pytest` **168 passed / 2 skipped**；`validate`（正式集与开发集均 `exit=0`）、`validate --require-reviewed` `exit=2`；`python -m eval.chunking_experiment --formal` `exit=2`，拒绝理由只剩「10 条 `REVIEWED_BY` 未签」，`frozen_manifest.json` 与 `eval/qa_set.csv` 两项检查已通过（见 `RUNLOG.md` 第 11.10 节） | 待组员重跑；云端 CI 已恢复（PR 页 1 successful check），run 结论目前只有浏览器截图，仓库内无可核验 run id |
| 2026-11-21 | T4 更正过期登记 + 记录人工复核落地（分支 `t4-k8s-qa-set`，PR #15，head `d39d658`） | AI 编码 agent 执行取证与登记，组员本人阅读 | `git fetch` 后发现远端分支 head 已被他人推进三个提交：`da3c82d` / `5eaf1e2`（`ziqilin669` 经 GitHub 网页上传已签名的 `eval/qa_set.csv` 与签名工作单）、`d39d658`（`ldk13856478627-cell` 把门禁测试由「关闭」翻为「打开」，含 **T2 拥有**的 `tests/test_chunking.py`）。本地 `git merge --ff-only` 跟上，未为追赶而制造新提交；逐行 csv 比对确认除 `notes` 外无列被改、`b2263d9` 的 KN03 纠正未被回退；在 `d39d658` 的 detached worktree 实跑四项命令；`RUNLOG.md` 新增 §11.13 / §11.14，本文件与 `docs/AI_USAGE.md` 的 QA 现状口径同步更正 | Agent 本地（`.venv`，Python 3.13.5，在 `d39d658` 上）：`ruff check .` 通过；`pytest -o addopts="" -q` **186 passed / 2 skipped**；`validate` `exit=0`（`10/10 carry REVIEWED_BY`）；`validate --require-reviewed` **`exit=0`**（此前各轮为 `exit=2`）。**零付费调用**。**云端验证**：本轮未取 —— 该 head 由他人推送且 PR 处于冲突态，页面 Checks 未复核，不写结论 | 人工复核本身由 `ziqilin669` 本人完成（签名与日期由他以自己账号写入，agent 未代填任何归属字段）；agent 只做了取证、实跑与登记。`tests/test_chunking.py` 的翻转**待 T2 认可** |
| 2026-11-21 | T4 第三次合并 `origin/main`（`30e6e98`，含 #18 / #20）+ 解 6 处文档冲突（分支 `t4-k8s-qa-set`，PR #15） | AI 编码 agent 执行，组员本人阅读 | `git merge-tree` 判定冲突只在三份追加式审计文档：`RUNLOG.md` 1 处、本文件 1 处、`docs/AI_USAGE.md` 4 处，**代码与测试 0 处**（`ragkit/*`、`tests/test_generation.py`、`tests/test_chunking.py`、`eval/chunking_experiment.py`、`demo/README.md` 等 8 个文件由 git 自动合并）。解法：main 上 T2 的 `## 10. T2 在冻结语料上重跑`（46 行）**逐字置于 T4 一节之前，一字未改**，**T4 一节整体改号为第 11 节**（`### 10.x` → `### 11.x`，节内指针同步；叙述上一次 9→10 改号的三句原句保留）；本文件只逐字插入 main 新增的那一行 T2 记录，不重排别人的行，改号脚本也不碰别人的行；`docs/AI_USAGE.md` 按 §11.14 口径取 main 那 195 行为逐字前缀（包括一级标题重复出现在第 1 与第 96 行的已知缺陷），本分支自己的登记追加到新开的 `## T4 additional records` 一节。详情见 `RUNLOG.md` 第 11.15 节 | Agent 本地（`.venv`，Python 3.13.5）合并后实跑：`ruff check .` 通过；`pytest -o addopts="" -q` **195 passed / 2 skipped**（合并前 186，+9 例来自 #18 / #20）；`validate` `exit=0`（`10/10 carry REVIEWED_BY`）；`validate --require-reviewed` **`exit=0`**。解冲突结果另由 37 项断言脚本核对（别人写的行零丢失、零修改）。**零付费调用**。**云端验证**：本轮未取 —— 本次合并产生的 head 尚未推送，不写云端结论 | 待组员对新的 head review；`tests/test_chunking.py` 现在同时含 main 上 T2 自己的改动与 `d39d658` 里 T1 账号做的门禁翻转，文本自动合并且测试全绿，但叠加后的语义**仍只待 T2 认可** |
| 2026-11-22 10:13 GMT+8 | T2 正式分块对比（分支 `t2-chunking-formal`） | Cursor Grok 4.7 编码 agent | PR #15 合并后 `--formal` 通过。同一冻结语料、正式 QA、size 600 / overlap 80 / top_k 3。命中率只调用 `retrieval_hit_rate()`。汇总写入 `eval/results/summary/chunking_comparison/`。认可 `tests/test_chunking.py` 里「评审门打开后正式目录可以创建」那条；开发 QA 路径和 `--out` 指向 `summary/` 的拒绝仍然保留 | Agent 本地：`ruff check .` 与 `pytest` 见 `RUNLOG.md` 第 12 节。`--formal` exit 0。`fixed` 668 chunks，hit@1 8/26 (0.3077)、hit@3 18/26 (0.6923)；`paragraph` 775 chunks，hit@1 10/26 (0.3846)、hit@3 17/26 (0.6538)。与 T4 先前单独跑的 `fixed` 正式集数字一致。零付费调用。组员本人尚未重跑。**云端验证**：尚未开 PR | 待组员阅读正式结果 |
| 2026-11-22 | T2 修正正式对比图 | Cursor Grok 4.7 编码 agent | `hit_rates.svg` 里 hit@1 的数字画进了 hit@3 的柱子。数字改到每根柱子右侧的固定槽，画布加宽。用同一份 `metrics.json` 重画，命中率未变，未重跑 `--formal` | Agent 本地：图的标签与柱子不再相交的测试通过；`ruff` 通过。组员本人尚未重跑 | 待组员看图 |

> 说明：上表前六行由账号持有人**发起**，命令与代码均由 AI Agent 执行；
> T4 在本分支上那几行（已增至 5 行）是账号持有人以组员身份提交的任务 PR，代码与文档经本人阅读修改，但验证命令同样由
> AI 编码 agent 在本机执行（组员可在 review 自己重跑后改写本列）；T2 三行随 PR #10 合并进 main，
> 其中 2026-11-17 20:50 那一行是组员本人重跑，其余两行由 Cursor 编码 agent 执行。
> 「本人审阅」「全组确认」等表述在没有 PR review 或本人确认记录时一律不写。

---

## 已知限制与需人工处理

- 仓库为私有。PR 列表页观察到的账号：`wangsaorui`（本账号，T4）、`ldk13856478627-cell`（#14 作者）、
  `ziqilin669`（#16 / T5 作者）；按 commit author 还能看到 `yafeili39-arch`、`null1024-ws`、`usagi`。
  **账号 ↔ 任务 ↔ 真人姓名的对应关系仍未核实**，且这些观察来自浏览器页面（本机无 `gh` CLI，
  仓库内无可核验记录），是否已把 5 人都加为 Collaborator 同样待确认；
  报告里的贡献声明页需本人逐人核实。
- GitHub Free + 私有仓库不支持强制分支保护 / Rulesets（API 403），PR review 规则靠人工执行。
- 技术取舍、应用领域与协作规则仍需五人共同确认；五个任务中 T1–T4 已各有 PR
  （#14 / #10 / #11 / #7），**已合并的是 T4 的 #7、T1 的 #13 与 T2 的 #10**，T1 的 #14（正式语料）
  与 T3 的 #11 仍未合并；T5 已开 #16（标题含 citation coverage / I4 batch export / offline demo），
  之前写的「T5 无人认领、看不到 PR」已被 PR 列表页证伪，不能写成「全组已确认」。
- QA 集现状：`eval/qa_set.csv` 已是**正式 Kubernetes 集**（36 条 = 26 answerable + 10 unanswerable，
  逐字引自 `data/raw/frozen_manifest.json` 快照的 12 篇文档并全覆盖）；35 题 Wikipedia 集保留为
  `eval/qa_set_dev_v0.csv`（开发集）。**10 条 `unanswerable` 标注已由 `ziqilin669` 本人于 2026-11-21 署名**
  （他用自己的账号把改好的 csv 与签名工作单传上分支，提交 `da3c82d` / `5eaf1e2`，不是任何人代填），
  `validate --require-reviewed` 现 `exit=0`，拒答类指标已不再是「无人签」状态。
  仍未完成的：**26 道 answerable 题未经第二人逐题阅读**，且 `answer_correctness` 仍无数字
  （无答案产物、无人评分）。签名工作单见
  [`../eval/review/formal_qa_review.md`](../eval/review/formal_qa_review.md)，过程见 `RUNLOG.md` §11.13。
- 本轮 T4 分支**基于尚未合并的 PR #14**（正式语料快照就在 #14 里），所以应等 #14 合并后再合并本 PR；
  若 #14 的语料有变动，需重跑 `python -m eval.metrics validate` 重验 gold 引文。
- 换行符：`core.autocrlf=true` 的 Windows 工作副本上 #14 的 `data/raw/` 是 CRLF，而哈希按字节算，
  会导致 T1 的哈希测试只在 Windows 红（Linux CI 掩盖）。本轮加了 `.gitattributes`（`* text=auto eol=lf`），
  但它不重写已存在的工作副本（实测 `git checkout --force` 无效），已有副本的人重新 clone 最简单；
  详情见 `RUNLOG.md` 第 11.2 节。
- **云端 CI 一度对所有 PR 都不可执行，现已恢复**：2026-11-20 的 run 页 Annotation 为“The job was not
  started because recent account payments have failed or your spending limit needs to be increased”，
  同时出现在 T1 的 #14 与本 PR 上（账号级问题，不是某个分支的问题）。2026-11-21 本 PR 页面显示
  **1 successful check**，说明已恢复。Actions 分钟数/付款属于账号级，只有账号持有人能在
  <https://github.com/settings/billing> 处理。恢复前那轮的本地判据见 `RUNLOG.md` 第 11.9 节，
  本轮合并后的实跑结果见第 11.10 节。**仓库内仍没有可核验的 run id**（`gh` CLI 在本机不可用），
  结论只来自组员浏览器截图，报告引用前需组员把 run 链接补进来。
  `CONTRIBUTING.md` 里「CI 绿才能合并」这条本轮**没有**改。
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

### 2026-11-21 T3 后续状态（Agent 核查 GitHub）

同步最新 `main`，保留 T1/T2/T4/T5 的现有记录和 T3 原始追加部分，且未调整其他成员历史声明。冻结语料文件现已存在；本轮仅整理 Git 历史和文档，不将旧四篇开发语料的 35QA 检索观察作为 Kubernetes 结果。冻结语料上的 T3 diagnostics、真实运行产物与学生本人重跑仍待完成；PR #15 的拒答人工复核仍未关闭。

### 2026-11-22 T3 最新集成状态（ChatGPT / GitHub 连接）

主线已完成 I1 冻结语料和 I2 36QA/10 条人工 REVIEWED_BY，T2 通过 PR #23 提交正式策略比较；本轮将 T3 修改与主线整合，保留各任务成员的文档记录，并修复 T3 原导入不存在的 T4 `QA_SET_STATUS` 常量（改用动态 `qa_set_status()`）。这项改动仅为接口兼容与分支同步，**非**冻结 Kubernetes 36QA 真实 T3 诊断。待执行本地 ONNX/Chroma ingest、fixed/paragraph diagnostics、来源与 rank 核验、真实运行记录；云端 CI 和组员人工审查应另行核对。

### 2026-11-22 T3 冻结输入复跑（HKT，Codex 本机执行）

在 PR #11 `c4516bf29317270b876193f66e864f8f053f785f` 的干净工作副本中运行 T4 `validate --require-reviewed`，确认 16 篇冻结文档和 36 题（26 条引文定位，10 条拒答有组员复核）。用本地 ONNX + Chroma 重新入库 fixed 668 块、paragraph 775 块，每个 collection 跑完 36 道题的完整排名。新进程读回两套索引，全部 1443 块及 216 条 top-3 的原文出处和字段回查一致。

定向测试 143 passed，全量 328 passed / 2 skipped，Ruff 通过。排名案例、真实命令与 SHA-256 见 [RETRIEVAL.md](RETRIEVAL.md)。原始产物在 `eval/results/raw/`。执行记录为 Codex 本机验证。组员审批和本人复核待完成。

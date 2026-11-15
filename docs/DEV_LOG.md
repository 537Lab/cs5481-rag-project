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

**截至本记录，五名组员尚未开始正式开发**，仓库中也**没有任何组员贡献记录**。以下内容全部属于
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

> 说明：账号持有人**发起**了这些工作、提供了账号与课程材料，但上表中的命令与代码均由 AI Agent 执行。
> 「本人审阅」「全组确认」等表述在没有 PR review 或本人确认记录时一律不写。

---

## 已知限制与需人工处理

- 仓库为私有，**尚未邀请另外 4 名组员**为 Collaborator；他们看不到仓库，也还没有任何贡献记录。
- GitHub Free + 私有仓库不支持强制分支保护 / Rulesets（API 403），PR review 规则靠人工执行。
- 技术取舍、应用领域与协作规则仍需五人共同确认；五个任务尚未认领，
  不能写成「全组已确认」。
- 真实 LLM API 调用需要密钥与费用方案；**尚未执行，零付费调用**。
- 贡献比例 + 全体签名单独一页是课程硬性要求，须在全员开工后据实填写，不得由 AI 代填。

---

## 组员追加记录模板

组员开始开发后，请各自在 PR 中追加一行（执行者写本人，验证写自己真实跑过的命令）：

```
| 日期 (GMT+8) | 阶段/任务 | 实际执行者 | 做了什么（含 PR 号） | 验证来源（本地命令 / 云端 CI，分开写） | 本人复核了什么 |
```

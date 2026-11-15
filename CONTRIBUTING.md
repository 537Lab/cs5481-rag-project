# 协作规范

仓库：https://github.com/537Lab/cs5481-rag-project （私有，`main` 为默认分支）
目标：**`main` 永远可运行**，五人同时改代码不互相覆盖。

项目背景、目标、老师要求映射、五个任务、依赖排期与交付标准的**唯一来源**是
[`docs/PROJECT_PLAN.md`](docs/PROJECT_PLAN.md)；本文件只讲协作规则，不重复项目定义。

> **状态**：五个任务尚未认领；协作规则、应用领域与技术方案仍需五人共同确认。
> 在此之前按本文档执行，但不要把任何一条写成「全组已确认」。

新组员的操作步骤见 [`START_HERE.md`](START_HERE.md)；技术设计见
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)；任务卡见 [`docs/TASKS.md`](docs/TASKS.md)。

---

## 1. 仓库现状（可核验）

| 项 | 状态 |
| --- | --- |
| 私有仓库 / 默认分支 | 已建立，`main` |
| 基础工程 | 首次提交 `a12bb14`，由 AI Agent 在仓库账号持有人授权下执行并推送 |
| GitHub Actions `ci` | 已配置；`ruff` + 离线 `pytest` + 密钥扫描，在 `main` 上的运行结论为 `success` |
| 自动合并 | 已关闭（`allow_auto_merge=false`） |
| 任务 Issue | 5 个 `task` Issue（T1–T5）已创建，供认领 |
| 强制分支保护 / Rulesets | 当前套餐下相关 API 返回 403，**未启用**；review 规则靠人工执行 |

CI 完全离线：不需要 API 密钥，也不下载模型；`tests/test_e2e_real.py` 默认跳过。

### 需要人工处理（尚未完成）

1. 由拥有仓库管理员权限的组员在 `Settings → Collaborators → Add people` 把其余 4 人加为
   Collaborator（Write）。私有仓库未被邀请的人看不到仓库。
2. 五人共同确认协作规则、应用领域与 LLM 方案，再由各人自行认领任务（Assignee 体现归属）。
3. 真实 LLM API 调用需要密钥与费用方案；目前未执行，也未产生任何付费调用。
4. 若希望启用强制分支保护，需升级套餐或由全组讨论是否改为 public；**不要擅自改动仓库可见性**。

## 2. 分支保护缺失时的替代流程

当前账户无法启用强制分支保护与 Rulesets（API 403）。因此采用以下**由人执行、非系统强制**的流程：

| 原本想要的强制规则 | 替代做法 |
| --- | --- |
| Require PR before merging | 除最初的 bootstrap 提交外，禁止直接 push 到 `main`，一律走 PR |
| Require 1 approval | PR 须由**作者之外的至少 1 名组员** Approve |
| Require status checks | 合并前人工确认 PR 页面 `ci / check` 为绿色 |
| 禁止自动合并 | 仓库已关闭 `allow_auto_merge`；一律手动 `Squash and merge` |
| 禁止 force push / 删除 main | 写入规范；所有人只 push 自己的分支，不使用 force push |

如果之后账户升级或全组同意改为 public，再在 `Settings → Branches` 启用强制保护，并同步更新本文件。

## 3. 认领任务与分工

GitHub `Issues` 中的 5 个 `task` Issue（T1–T5）与 `docs/TASKS.md` 对应。在 Issue 里评论认领并把
Assignee 设成自己，一人一个；五人地位平等，本文件不指定任何人承担哪个任务。
每人都有**代码开发 + 自动化测试 + 运行验证 + 实验分析**四项责任。

| 任务 | 主题 | 分支前缀 | 主要可改文件（详见 `docs/TASKS.md`） |
| --- | --- | --- | --- |
| T1 | 正式知识库与文档处理 | `t1-corpus-*` | `ragkit/loaders.py`, `data/raw/**`, `scripts/fetch_corpus.py`, `tests/test_loaders.py`, `docs/CORPUS.md` |
| T2 | Chunking 策略与对比实验 | `t2-chunking-*` | `ragkit/chunking.py`, `tests/test_chunking.py`, `eval/chunking_experiment.py`, `docs/CHUNKING_EXPERIMENT.md` |
| T3 | 检索层与向量库 | `t3-retrieval-*` | `ragkit/store.py`, `ragkit/embeddings.py`, `tests/test_store.py`, `tests/test_embeddings.py`, `eval/retrieval_diagnostics.py`, `docs/RETRIEVAL.md` |
| T4 | 评测集与唯一指标实现 | `t4-eval-*` | `eval/qa_set.csv`, `eval/metrics.py`, `eval/judge_protocol.md`, `tests/test_eval_metrics.py` |
| T5 | LLM 问答、引用支持性与演示 | `t5-generation-*` | `ragkit/generation.py`, `ragkit/cli.py`, `tests/test_generation.py`, `eval/answers/**`, `demo/**`, `docs/ANSWER_QUALITY.md` |

- 只改自己任务包列出的文件 + 自己的测试；要改别人的文件先告知对方。
- 分支短生命周期，合并后立即删除；不要长期开一条大分支。
- `CORPUS_V0`（已提交的 4 篇语料）保持冻结，仅用于开发与自测，详见 `docs/TASKS.md` 的冻结规则。

## 4. 每天的标准流程

```bash
git checkout main && git pull
git checkout -b t3-retrieval-hitk      # 换成自己的分支

# 改代码 + 补测试，然后本地自检（两条都必须过）
python -m pytest -q
ruff check .

git add <你改的文件>
git commit -m "t3: isolate collections per chunking strategy"
git push -u origin t3-retrieval-hitk
```

到 GitHub 点 `Compare & pull request`，按模板勾选自检清单，指定**另一位组员** review。
提交信息格式：`t3: 一句话说清改了什么`，不要写 `update` / `fix` —— 报告里的贡献比例页要靠它举证。

## 5. PR 与合并规则

一个 PR 合并前必须同时满足（**人工确认**）：

1. `ci / check` 绿灯（`ruff check .` + 离线 `pytest -q` + 密钥扫描）。
2. 至少 **1 位其他组员** Approve（作者不能自己批准自己的 PR）。
3. PR 模板自检清单全部勾选，写清「reviewer 用哪条命令验证、预期输出是什么」。
4. 没有提交 `.env`、密钥、`data/index/`、`eval/results/raw/`；若提交了汇总实验结果，
   必须来自真实运行并附带命令、配置与日期（见 `eval/README.md`）。
5. 冲突已用 `git rebase main` 解决。

由**非作者**手动 `Squash and merge`，合并后删除源分支。所有人随后 `git pull` 并 rebase。

## 6. 「影响全组」的变更需 ≥2 人同意

`ragkit/contracts.py`（数据契约）、`config.toml`、`requirements*.txt`、`pyproject.toml`、
`docs/PROJECT_PLAN.md`、`docs/ARCHITECTURE.md`、`docs/TASKS.md`、`CONTRIBUTING.md`、
`ragkit/pipeline.py`、`ragkit/cli.py`，以及 `PROJECT_PLAN.md` §6.1 中的 I1–I5 数据 / 接口契约。
改契约的 PR 描述必须写：改了哪个字段、哪些模块要跟着改、影响哪些测试。

## 7. 绝对禁止提交

- `.env`、任何 API key / token（代码、注释、测试、提交信息、CI 都不行）。
- `data/index/`（Chroma 生成物）、`eval/results/raw/`（原始逐条输出、日志、缓存）、
  `__pycache__`、`.venv/`。
- 硬编码命中率 / 正确率、MOCK 输出冒充真实实验、把没跑过的命令写成「已验证」、
  没有来源或无法复现的实验数字。
- 未经全组确认的**付费 LLM API 调用**。

**真实、可复现的结果不属于禁止项**：汇总指标、图表、实验配置与运行清单应提交，
保存路径与格式见 [`eval/README.md`](eval/README.md) 与 `eval/results/README.md`。

误提交密钥：立刻在服务商后台吊销并重新生成，再告知全组；不要只靠「再提交一次删掉」。

## 8. 报告与学术诚信

老师明文要求、逐项覆盖情况与最终交付清单统一见
[`docs/PROJECT_PLAN.md` §3、§7](docs/PROJECT_PLAN.md)。其中**单独一页**写每人贡献比例 +
**全体成员签名**（位于 slides 之前）是硬性红线，缺页或缺签名会被 desk reject。

- 从第一天起用规范 PR 和清晰 commit message；AI 辅助使用情况登记在
  [`docs/AI_USAGE.md`](docs/AI_USAGE.md)，实际开发记录登记在 [`docs/DEV_LOG.md`](docs/DEV_LOG.md)。
- 目前这两份文件**只有 bootstrap 阶段的 AI 执行记录，尚无任何组员贡献记录**。
  贡献比例页须在全员开工后依据 PR 历史与各人真实工作据实填写，不能由 AI 代填或推断。

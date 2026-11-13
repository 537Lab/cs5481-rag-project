# 五人协作规范（GitHub）

仓库：https://github.com/537Lab/cs5481-rag-project （私有，`main` 为默认分支）
目标：**main 永远可运行**，五人同时改代码不互相覆盖。新手先读 `START_HERE.md`。

---

## 1. 已完成的设置（组长/bootstrap）

- 私有仓库已建、首次提交 `a12bb14` 已推 `main`。
- GitHub Actions `ci` 已配置并**真实运行成功一次**（`ruff` + 离线 `pytest` + 密钥扫描）。
- **自动合并已关闭**（`allow_auto_merge=false`）。
- 5 个任务 Issue（T1–T5）与 `docs/TASKS.md` 已准备，供认领。

### 还需要组长本人手动做的

1. `Settings → Collaborators → Add people`：把另外 4 名组员加为 Collaborator（Write）。
   私有仓库未被邀请的人看不到仓库。
2. `Settings → General`：建议勾选 "Automatically delete head branches"（合并后自动删分支）。

> CI 完全离线：不需要 API 密钥，也不下载模型；`tests/test_e2e_real.py` 在 CI 默认跳过。

## 2. 分支保护：当前账户不支持，采用人工替代流程

尝试过 Branch Protection 与 Repository Rulesets，均返回：

```
403 Upgrade to GitHub Pro or make this repository public to enable this feature.
```

即 **GitHub Free + 私有仓库无法启用强制保护**。按"不要卡住项目"的原则，采用以下
**安全且简单的替代流程**（由人执行，不是系统强制）：

| 原本想要的强制规则 | 替代做法 |
| --- | --- |
| Require PR before merging | 规定：除首次 bootstrap 提交外，**禁止直接 push 到 main**，一律走 PR |
| Require 1 approval | PR 必须由**作者之外的至少 1 名组员** Approve；合并前人工确认 |
| Require status checks | 合并前人工确认 PR 页面 `ci / check` 为绿色 |
| 禁止自动合并 | 仓库设置已关闭 `allow_auto_merge`；合并一律手动 `Squash and merge` |
| 禁止 force push / 删除 main | 写入规范；所有人只 push 自己的分支 |

如果之后账户升级到 GitHub Pro，或全组同意把仓库改为 public，再由组长在
`Settings → Branches` 启用强制保护，并同步更新本文件。**不要为了启用保护而擅自公开仓库。**

## 3. 认领任务

GitHub `Issues` 里有 5 个 `task` Issue（T1–T5），内容与 `docs/TASKS.md` 一致。
在 Issue 里评论认领并把 Assignee 设成自己，一人一个。每人都有**代码开发 + 自动化测试 +
运行验证 + 实验分析**四项责任，组长承担 T1 技术模块。

## 4. 分工与分支名

| 任务 | 主题 | 分支前缀 | 主要可改文件（详见 `docs/TASKS.md`） |
| --- | --- | --- | --- |
| T1 | 正式知识库与文档处理（组长） | `t1-corpus-*` | `ragkit/loaders.py`, `data/raw/**`, `scripts/fetch_corpus.py`, `tests/test_loaders.py`, `docs/CORPUS.md` |
| T2 | Chunking 策略与对比实验 | `t2-chunking-*` | `ragkit/chunking.py`, `tests/test_chunking.py`, `eval/chunking_experiment.py`, `docs/CHUNKING_EXPERIMENT.md` |
| T3 | 检索层与向量库 | `t3-retrieval-*` | `ragkit/store.py`, `ragkit/embeddings.py`, `tests/test_store.py`, `tests/test_embeddings.py`, `eval/retrieval_metrics.py` |
| T4 | 评测集、指标与拒答评估 | `t4-eval-*` | `eval/qa_set.csv`, `eval/metrics.py`, `eval/judge_protocol.md`, `tests/test_eval_metrics.py` |
| T5 | LLM 问答、引用支持性与演示 | `t5-generation-*` | `ragkit/generation.py`, `ragkit/cli.py`, `tests/test_generation.py`, `demo/**`, `docs/ANSWER_QUALITY.md` |

- 只改自己任务包列出的文件 + 自己的测试；要改别人的文件先在群里说。
- 分支短生命周期，合并后立即删除；不要长期开一条大分支。
- 约定 `CORPUS_V0`（已提交的 4 篇语料）保持冻结，五人可并行开发、互不等待。

## 5. 每天的标准流程

```bash
git checkout main && git pull
git checkout -b t3-retrieval-hitk      # 换成你的分支

# 改代码 + 补测试，然后本地自检（两条都必须过）
python -m pytest -q
ruff check .

git add <你改的文件>
git commit -m "t3: add hit@k computation"
git push -u origin t3-retrieval-hitk
```

到 GitHub 点 `Compare & pull request`，按模板勾选自检清单，指定**另一位组员** review。

提交信息格式：`t3: 一句话说清改了什么`。不要写 `update` / `fix` —— 报告里的贡献比例页要靠它举证。

## 6. PR 与合并规则

一个 PR 合并前必须同时满足（**人工确认**）：

1. `ci / check` 绿灯（`ruff check .` + `pytest -q` + 密钥扫描）。
2. 至少 **1 位其他组员** Approve（作者不能自己批准自己的 PR）。
3. PR 模板自检清单全部勾选，写清"reviewer 用哪条命令验证、预期输出是什么"。
4. 没有 `.env`、密钥、`data/index/`、`eval/results/`、实验数字被提交。
5. 冲突已用 `git rebase main` 解决。

由**非作者**手动 `Squash and merge`，合并后删除源分支。所有人随后 `git pull` 并 rebase。

## 7. 「影响全组」的变更需 ≥2 人同意

`ragkit/contracts.py`（数据契约）、`config.toml`、`requirements*.txt`、`pyproject.toml`、
`docs/ARCHITECTURE.md`、`CONTRIBUTING.md`、`ragkit/pipeline.py`、`ragkit/cli.py`。
改契约的 PR 描述必须写：改了哪个字段、哪些模块要跟着改、影响哪些测试。

## 8. 绝对禁止提交

- `.env`、任何 API key / token（代码、注释、测试、提交信息、CI 都不行）。
- `data/index/`（Chroma 生成物）、`eval/results/`、`__pycache__/`、`.venv/`。
- 硬编码命中率/正确率、MOCK 输出冒充真实实验、没跑过的命令写成"已验证"。
- 未经全组确认的**付费 LLM API 调用**。

误提交密钥：立刻在服务商后台吊销并重新生成，再告知组长；不要只靠"再提交一次删掉"。

## 9. 报告与学术诚信

- 报告需 introduction / methodology / experiments and discussions，正文 ≤6 页，末尾附 slides。
- **单独一页**写每人贡献比例 + **全体成员签名**（在 slides 之前）；缺页或缺签名会被 desk reject。
- 从第一天起用规范 PR 和清晰 commit message；AI 辅助使用情况登记在 `docs/AI_USAGE.md`，
  实际开发记录登记在 `docs/DEV_LOG.md`，两者都是贡献声明的证据。

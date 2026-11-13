# 组员上手指南

**仓库**：https://github.com/537Lab/cs5481-rag-project （私有，默认分支 `main`）

本文件只讲「怎么开始动手」。项目介绍看 [`README.md`](README.md)，协作规则看
[`CONTRIBUTING.md`](CONTRIBUTING.md)，技术设计看 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)，
任务定义看 [`docs/TASKS.md`](docs/TASKS.md)。

---

## 1. 先拿到权限

仓库是私有的，需要组长先把你加为 Collaborator：
GitHub → 仓库 → `Settings` → `Collaborators` → `Add people` → 输入你的 GitHub 用户名。
在邮箱里点 Accept 之后才能 clone 和 push。看不到仓库就找组长发邀请，不要换账号或让同学转发代码。

## 2. 克隆并跑通（复制粘贴即可）

```bash
git clone https://github.com/537Lab/cs5481-rag-project.git
cd cs5481-rag-project

python3 -m venv .venv
source .venv/bin/activate                 # Windows: .venv\Scripts\activate
python -m pip install -r requirements-dev.txt

python -m ragkit.cli offline-demo         # MOCK 演示，零配置
python -m pytest -q                       # 离线测试
ruff check .                              # 静态检查
```

**所有命令都在仓库根目录执行**，否则 `import ragkit` 会失败。

预期结果：

- `offline-demo` 顶部打印 `[MOCK / OFFLINE DEMO]` 横幅，随后给出 1 条带引用的答案和 2 条拒答案例；这是模拟运行，**不能**写进报告。
- `pytest -q` 全绿，`tests/test_e2e_real.py` 的 2 个 `real` 用例默认 skip。
- `ruff check .` 输出 `All checks passed!`。

若出现 `ModuleNotFoundError: No module named 'ragkit'`：确认已 `cd cs5481-rag-project`
并激活了虚拟环境。若 `Index is empty`：先跑一次 `ingest`。

## 3. 可选：跑真实入库与检索（不需要密钥）

```bash
python -m ragkit.cli ingest
python -m ragkit.cli retrieve "What is retrieval-augmented generation?" --top-k 3
```

首次 `ingest` 需联网下载约 80 MB 本地模型到 `~/.cache/chroma`，之后可离线使用。
若所在网络无法访问模型 CDN，请自行配置可用网络或预置模型缓存；**个人网络配置不要提交到仓库**。

`cli ask` 和 `pytest -m real` 需要 `OPENAI_API_KEY`，目前均未执行。密钥只放 `.env`
（已被 gitignore）。任何付费 API 调用必须先由全组确认方案。

## 4. 认领任务

任务清单：GitHub `Issues` 中的 T1–T5（带 `task` 标签），完整说明见 [`docs/TASKS.md`](docs/TASKS.md)。
在对应 Issue 里评论认领、把 Assignee 设成自己，一人一个。

使用 Coding Agent 时：

1. 把该 Issue 正文 + `docs/ARCHITECTURE.md` 的契约部分一起贴给 Agent，让它先给方案再写代码；
2. 自己读一遍生成的代码，能在组会上解释实现与取舍；
3. 自己跑任务包里的验收命令并保存输出，不把 Agent 的「已完成」当成验证；
4. 在 [`docs/AI_USAGE.md`](docs/AI_USAGE.md) 登记用了哪个 Agent、做了什么、自己复核了什么；
5. 不把 Agent 生成的数字当作实验结果。

## 5. 提交修改并发起 PR（操作步骤）

```bash
git checkout main && git pull
git checkout -b t3-retrieval-hitk          # 换成自己的分支名，前缀见 CONTRIBUTING.md

# 只改自己任务包列出的文件 + 自己的测试
python -m pytest -q && ruff check .         # 两条都要过

git add <你改的文件>
git commit -m "t3: add hit@k computation"
git push -u origin t3-retrieval-hitk
```

然后到 GitHub 点 `Compare & pull request`，按 PR 模板勾选自检清单，指定**另一位组员** review。
合并条件、分支命名、review 人数、影响全组的文件清单等规则统一以
[`CONTRIBUTING.md`](CONTRIBUTING.md) 为准；这些规则目前由人工执行，不是系统强制。

## 6. 怎么判断任务做完了

每个任务在 [`docs/TASKS.md`](docs/TASKS.md) 都有「验收命令」和「完成标准」。最低要求：

- 自己的测试：`python -m pytest tests/<你的测试文件>.py -q` 全绿；
- 全量回归：`python -m pytest -q` 全绿；
- 静态检查：`ruff check .` 通过；
- 按任务包给出的 CLI/脚本命令**真实跑一次**，保存输出与实验配置，结果按
  [`eval/README.md`](eval/README.md) 的规范提交；
- 任务包要求的分析写进对应 `docs/*.md`，数字来自真实运行，不硬编码、不伪造「已运行」。

「测试通过」不等于「任务完成」，完成标准还包含输出物、分析与可解释性。

## 7. 进度速览

- **已可用**：基础流水线、离线测试、静态检查与云端 CI；真实语料 4 篇、本地 embedding、Chroma 入库与检索。
- **尚未开展**（正是五个任务包的内容）：正式语料扩充、≥20 组 QA、两种 chunking 的对比实验、命中率 / 正确率 / 拒答率、回答正确性的 judge、真实 LLM 回答、报告与 slides。
- 任务之间的依赖，以及 T1 正式语料、T4 正式评测集的冻结规则，见 [`docs/TASKS.md`](docs/TASKS.md)。
- 逐条真实命令与原始输出见 [`RUNLOG.md`](RUNLOG.md)；开发记录见 [`docs/DEV_LOG.md`](docs/DEV_LOG.md)。

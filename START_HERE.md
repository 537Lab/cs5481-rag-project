# 组员启动说明（没用过 GitHub 也能照做）

**仓库**：https://github.com/537Lab/cs5481-rag-project （**私有**）
**分支**：`main`　**当前状态**：基础工程 v1.1 已跑通，正式实验尚未开始。

> 这个仓库现在只有"地基"，不是做完的作业。自动化测试全绿只说明地基没坏，
> **不代表课程项目已完成**。20 组 QA、chunking 对比实验、检索命中率、回答正确率
> 和最终报告都还没做 —— 那是五个任务包的内容。

---

## 1. 拿到权限（第一步）

仓库是私有的，**组长需要先把你加为 Collaborator**：
GitHub → 仓库 → `Settings` → `Collaborators` → `Add people` → 输入你的 GitHub 用户名。
你会在邮箱收到邀请，点 Accept 后才能 clone 和 push。

> 如果你看不到仓库，先找组长发邀请，不要换账号或让同学把代码发给你。

## 2. 获取并跑起来（复制粘贴即可）

```bash
git clone https://github.com/537Lab/cs5481-rag-project.git
cd cs5481-rag-project

python3 -m venv .venv
source .venv/bin/activate                 # Windows: .venv\Scripts\activate
python -m pip install -r requirements-dev.txt

python -m ragkit.cli offline-demo         # MOCK 演示，零配置
python -m pytest -q                       # 应显示 57 passed, 2 skipped
ruff check .                              # 应显示 All checks passed
```

**所有命令都要在仓库根目录执行**（否则会找不到 `ragkit`）。

想看真实的入库与检索（不需要任何密钥）：

```bash
python -m ragkit.cli ingest               # 真实文档 → 28 个 chunk → Chroma
python -m ragkit.cli retrieve "What is retrieval-augmented generation?"
```

首次 `ingest` 会下载约 80MB 本地模型到 `~/.cache/chroma`，之后离线可用。
若下载卡住，见 `README.md` 的代理 FAQ（Clash 7897 优先，肥猫云 7892 兜底）。

`cli ask` 需要 `OPENAI_API_KEY`，**目前没有执行过**；任何付费 API 调用必须先由全组确认方案。
密钥只放 `.env`（已被 gitignore），**永远不要提交**。

## 3. 认领任务 / 让 Coding Agent 参与

任务清单有两处，内容一致：

- GitHub 页面 → `Issues`（5 个 `task` Issue，T1–T5）
- 仓库内 `docs/TASKS.md`（更详细：输入/输出/可改文件/依赖/验收命令/完成标准）

**认领**：在对应 Issue 里评论 `I'll take T3` 并把 Assignee 设成自己。一人一个，不要抢。

**用 Coding Agent**：把该 Issue 的正文 + `docs/ARCHITECTURE.md` 的契约部分一起贴给你的
Coding Agent，让它先给方案再写代码。但你必须：

1. 自己读一遍生成的代码，能在组会上解释实现和取舍；
2. 自己跑第 5 节的验收命令并保存输出；
3. 在 `docs/AI_USAGE.md` 登记用了哪个 Agent、做了什么、你复核了什么；
4. 不把 Agent 生成的数字当实验结果。

## 4. 提交修改并发起 PR

```bash
git checkout main && git pull
git checkout -b t3-retrieval-metrics      # 换成你的分支名，见下表

# 只改自己任务包列出的文件 + 自己的测试
python -m pytest -q && ruff check .        # 两条都要过

git add <你改的文件>
git commit -m "t3: add hit@k computation"
git push -u origin t3-retrieval-metrics
```

然后到 GitHub 点 `Compare & pull request`，按模板勾选自检清单，指定**另一位组员** review。

| 规则 | 说明 |
| --- | --- |
| 分支名 | `t1-corpus` / `t2-chunking` / `t3-retrieval` / `t4-eval` / `t5-generation` 加短描述 |
| 禁止 | 直接 push 到 `main`；改别人任务包的文件而不先说 |
| 合并条件 | CI（`ruff` + `pytest`）绿灯 **且** 至少 **1 名其他组员** Approve；由非作者手动 `Squash and merge` |
| 自动合并 | **已关闭**（`allow_auto_merge=false`） |
| 契约变更 | 改 `ragkit/contracts.py` / `config.toml` / `requirements*.txt` 需 ≥2 人同意并提前通知全组 |

⚠️ 当前账户（GitHub Free + 私有仓库）**无法启用强制分支保护 / Rulesets**（API 返回 403）。
所以上述 review 规则靠**人工执行**，不是系统强制：合并前请自己确认 CI 状态和 Approve 人数。
详见 `CONTRIBUTING.md`。

## 5. 怎么判断自己的模块做完了

每个任务在 `docs/TASKS.md` 都有"验收命令"和"完成标准"。最低要求：

| 检查 | 命令 / 标准 |
| --- | --- |
| 自己的测试 | `python -m pytest tests/<你的测试文件>.py -q` 全绿 |
| 全量回归 | `python -m pytest -q`（57 passed, 2 skipped 起步；你新增的测试也要过） |
| 静态检查 | `ruff check .` 通过 |
| 运行验证 | 按任务包给出的 CLI/脚本命令真实跑一次，保存输出 |
| 实验分析 | 任务包要求的分析写进对应 `docs/*.md`，数字来自真实运行 |
| 诚实性 | 无硬编码结果、无伪造"已运行"、MOCK 明确标注 |

**不要在 PR 里写"测试通过 = 任务完成"**：完成标准还包含输出物、分析与可解释性。

## 6. 五个任务之间的依赖

```
CORPUS_V0 = 已提交的 4 篇真实文档（doc_id 与文本冻结，所有人立即可用）
```

- **T1** 扩充正式语料，但**不阻塞**其他人：大家先用 CORPUS_V0 + `tests/fixtures/` 并行开发；T1 后续另出 `frozen_manifest.json` 供正式实验。
- **T2 / T3 / T4 / T5** 之间靠**已冻结的契约**并行：`Chunk`、`Answer` 数据类和共同证据标准，不需要等对方写完。
- 最后一步才需要集成：五人合并 PR 后一起跑一次完整对比实验（T2+T3+T4+T5）。
- 详见 `docs/TASKS.md` 的依赖图与建议 Day 1–7 顺序。

## 7. 现在到底哪些是真验证 / 哪些是 MOCK / 哪些没做

| 状态 | 内容 |
| --- | --- |
| ✅ **REAL 已验证** | 本地 ONNX 384 维 embedding；4 篇真实文档 → 28 chunks 入 Chroma；语义检索返回带出处/许可/字符偏移的 top-k；`ruff` 通过；57 个离线测试通过；GitHub Actions 云端 CI 成功运行一次 |
| 🧪 **MOCK（明确标注，不能写进报告当结果）** | `cli offline-demo`、`tests/fakes.py` 的替身、`tests/fixtures/` 的合成文档、绝大多数单元测试 |
| ❌ **尚未执行** | 真实 LLM 回答（`cli ask`）、`pytest -m real` —— 无 API 密钥，且付费调用需全组先确认 |
| ❌ **尚未完成（五人任务）** | ≥20 组正式 QA、两种 chunking 对比实验、检索命中率 / 回答正确率 / 拒答率、引用内容支持性 judge、可运行演示、正式语料扩充、报告与 slides |
| ⚠️ **需人工遵守** | PR review 规则（账户套餐不支持强制保护）；贡献比例 + 全体签名单独一页（课程硬性要求，缺页会 desk reject） |

完整命令与原始输出见 `RUNLOG.md`；本次修复与 AI 辅助记录见 `docs/DEV_LOG.md`、`docs/AI_USAGE.md`。

# 五人协作规范（GitHub）

目标：**main 永远是可运行的**，五个人同时改代码也不互相覆盖。规则不多，但请照做。

---

## 1. 一次性设置（由组长做，10 分钟）

1. 建私有仓库，把 `main` 设为默认分支，把 5 人加为 Collaborator（Write 权限）。
2. **Settings → Branches → Add branch ruleset / protection rule**，对 `main` 勾选：
   - Require a pull request before merging
   - Require approvals: **1**（改 `contracts.py` 的 PR 由组长临时改成 2，见第 5 节）
   - Require status checks to pass：勾选 `ci / check`
   - Require branches to be up to date before merging（可选，建议勾）
   - **不允许 force push、不允许删除 main**
3. Settings → General：勾选 "Automatically delete head branches"（合并后自动删分支）。
4. 把本仓库 `.github/workflows/ci.yml` 随第一次提交一起推上去，之后每个 PR 会自动跑 `ruff` + 离线 `pytest`。

> CI 完全离线：不需要任何 API 密钥，也不会下载模型。`tests/test_e2e_real.py` 标了 `real`，在 CI 里默认跳过。

---

## 2. 分工与分支名

| 成员 | 模块 | 固定分支 | 主要可改文件 |
| --- | --- | --- | --- |
| A | M1 文档接入 | `m1-ingest` | `ragkit/loaders.py`, `tests/test_loaders.py`, `data/raw/`, `scripts/fetch_corpus.py` |
| B | M2 分块 | `m2-chunking` | `ragkit/chunking.py`, `tests/test_chunking.py` |
| C | M3 向量化 | `m3-embedding` | `ragkit/embeddings.py`, `tests/test_embeddings.py` |
| D | M4 存储检索 | `m4-store` | `ragkit/store.py`, `tests/test_store.py` |
| E | M5 生成引用 | `m5-generation` | `ragkit/generation.py`, `tests/test_generation.py` |

- 每人**只改自己模块的文件 + 自己模块的测试**。想改别人的文件，先在群里说，让对方自己改或一起开 PR。
- 分支短生命周期：一个功能一个分支，合并后立即删除；**不要长期开一条大分支**。
- `main` 禁止直接 push。第一次克隆后先 `git checkout -b m2-chunking`（换成你自己的）。

---

## 3. 每天的标准流程（复制即可）

```bash
# 1) 开始工作前：把 main 的最新内容同步过来
git checkout main
git pull origin main
git checkout m2-chunking              # 换成你的分支
git rebase main

# 2) 改代码 + 补测试，然后本地自检（两条都必须过）
python -m pytest -q
ruff check .

# 3) 提交并推送
git add ragkit/chunking.py tests/test_chunking.py
git commit -m "m2: add paragraph chunker boundary tests"
git push origin m2-chunking

# 4) 到 GitHub 网页点 "Compare & pull request"，按模板填写，指定至少 1 位 reviewer
```

提交信息格式：`<模块>: <一句话说清改了什么>`，例如 `m4: return cosine similarity instead of distance`。
**不要用** `update` / `fix` / `asdf` 这种看不出内容的 message —— 报告里的贡献比例页要靠它举证。

---

## 4. PR 与合并规则

一个 PR 能被合并，**必须同时满足**：

1. CI 的 `ci / check` 全绿（`ruff check .` + `pytest -q`）。
2. 至少 **1 位**其他成员 Approve（不能自己批自己）。
3. PR 模板的自检清单全部勾选，写清楚"reviewer 用哪条命令验证、预期输出是什么"。
4. 没有把 `.env`、密钥、`data/index/`、`eval/results/`、实验数字提交进来。
5. 冲突已解决（用 `git rebase main`，不要在网页上盲点 resolve）。

**合并方式统一用 Squash and merge**（一个 PR 在 main 上留一条干净记录），合并后删除源分支。
合并后所有人执行一次 `git checkout main && git pull`，再 `rebase` 自己的分支。

---

## 5. 「影响全组」的变更要额外审批

下列文件任何人都能提 PR，但**需要 ≥2 人 Approve，并提前在群里说明**：

- `ragkit/contracts.py`（数据类型 / 接口，改了所有人都要跟着改）
- `config.toml`、`requirements*.txt`、`pyproject.toml`（影响每人的环境）
- `docs/ARCHITECTURE.md`、`CONTRIBUTING.md`（协作约定）
- `ragkit/pipeline.py`、`ragkit/cli.py`（编排与命令，由组长维护较好）

改 `contracts.py` 的 PR 描述里必须写：**改了哪个字段、哪个模块要跟着改、预计影响哪些测试**。

---

## 6. 绝对禁止提交

- `.env`、任何 API key / token（代码、注释、测试、提交信息、CI 里都不行）。
- `data/index/`（Chroma 索引，每人本地 `ingest` 重建）。
- `eval/results/`、任何"看起来像实验结果"的硬编码数字。
- MOCK 输出冒充真实实验记录；没跑过的命令写成"已验证"。
- `~/.cache/chroma`、虚拟环境 `.venv/`、`__pycache__/`、`.DS_Store`。

万一误提交了密钥：**立刻在服务商后台吊销并重新生成**，然后告诉组长；不要只靠"再提交一次删掉"，历史里仍然看得见。

---

## 7. 冲突与求助

- 冲突绝大多数来自都改了 `contracts.py` 或 `config.toml` → 先在第 5 节的流程里对齐，再动手。
- 测试挂了先看是不是忘了 `source .venv/bin/activate`、是不是不在仓库根目录、是不是 `data/index/` 被别人改动。
- 真实 E2E 需要密钥：`RUN_REAL_E2E=1 python -m pytest -m real -q`。**不要**为了"让 CI 变绿"而把它改成默认执行。

---

## 8. 别忘了报告的硬性要求

课程说明要求：报告的**单独一页**写明每位成员贡献比例，并有**全体成员签名**，该页位于正文之后、slides 之前；缺页或缺签名会被直接 desk reject。

因此：
- 从第一天起用规范 PR 和清晰的 commit message，最后用 GitHub 的 commit / PR 历史统计贡献，不要靠回忆。
- 组长在截止前至少 2 天收齐 5 人签名，别留到最后一晚。
- 报告还需要 introduction / methodology / experiments and discussions、≤6 页正文、末尾附 slides。

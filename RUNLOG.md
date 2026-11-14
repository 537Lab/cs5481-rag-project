# 实际运行记录（基础工程 v1）

记录日期：**2026-11-13（GMT+8）**。

记录原则：只写**真实执行过的命令**和**原始输出**。没有执行的命令明确标注「未执行」。
**MOCK**（模拟）与 **REAL**（真实端到端）严格分开，不把模拟输出当实验结果，
不硬编码任何命中率 / 正确率数字，也不伪造"运行成功"。

---

## 1. 环境与依赖探测（真实执行）

```
Python 3.13.12 / pip 26.0 / git 2.x（无 uv、无 ollama、无 brew）
pip index versions chromadb -> 1.5.9 可用
```

建立独立探测虚拟环境并验证核心依赖可安装、可导入：

```
python3 -m venv /tmp/cs5481-probe-venv
pip install "chromadb>=1.0,<2" "openai>=1.40,<2" "python-dotenv>=1.0,<2" "pytest>=8,<9" "ruff>=0.6,<1"
INSTALL_EXIT=0
chromadb 1.5.9
openai 1.109.1
IMPORT_OK
```

> 注：`python-dotenv` 只是探测时装过，最终工程**没有**采用（`config.py` 用约 10 行 stdlib 自读 `.env`），
> 所以 `requirements.txt` 只有 `chromadb` 与 `openai` 两个运行时依赖。

### 网络 / 代理探测（为什么要专门测）

用户环境同时有 Clash 与肥猫云两个客户端，终端注入的 `HTTPS_PROXY` 不一定能出外网，
因此按"Clash 优先、肥猫云兜底、注入代理降级"逐条实测目标域名，而不是只看端口能否连上。

| 线路 | Wikipedia REST | Chroma 模型 CDN | 结论 |
| --- | --- | --- | --- |
| 注入 `HTTPS_PROXY=http://127.0.0.1:55013` | `curl: (7) CONNECT tunnel failed, response 502` | 超时 | **不可用** |
| Clash `127.0.0.1:7897` | `HTTP 200` | `HTTP 200` | **可用**（端口 OPEN） |
| 肥猫云 `127.0.0.1:7892` | 连接失败（端口未监听） | — | 本次未启用，保留为兜底 |

切换热点后模型 CDN 实测速度从约 1 MB/s 提升到约 **11–12.6 MB/s**（83,178,821 字节在 12 秒内下载完成）。

---

## 2. 真实语料与本地模型准备（真实执行）

**为什么**：用户选择"混合：本地向量 + 云 LLM"和"公开授权资料"，但本机没有任何 API 凭据，
所以必须确认「无密钥也能真实跑通入库与检索链路」。

语料抓取（走 Clash 7897，Wikipedia MediaWiki API 纯文本接口）：

```
OK rag_wikipedia                  4166 chars  <- Retrieval-augmented generation
OK vector_db_wikipedia            3245 chars  <- Vector database
OK word_embedding_wikipedia       3327 chars  <- Word embedding
OK bm25_wikipedia                 2874 chars  <- Okapi BM25
Wrote 4 documents and data/raw/manifest.json
```

出处 / 许可写入 `data/raw/SOURCES.md`（Wikipedia, CC BY-SA 4.0），每篇在 `manifest.json`
里带 `source_uri` 与 `license`。**模拟文档只在 `tests/fixtures/`，首行标注 MOCK。**

本地 ONNX 模型：Chroma 内置下载器在注入代理下 `ReadTimeout`（7 分钟后手动终止），
改为经 Clash 7897 预置到 `~/.cache/chroma/onnx_models/all-MiniLM-L6-v2/onnx.tar.gz`：

```
HTTP=200 bytes=83178821 speed=12603838B/s
file: gzip compressed data ... onnx/model.onnx 等 6 个条目
LOCAL_ONNX_OK n= 2 dim= 384 secs= 0.5
```

即：**真实开源模型、384 维向量、本机推理，无需 API key**。首次下载后完全离线。
README 的 FAQ 已写明两条代理线路与手工预置缓存的方法。

---

## 3. 静态检查与自动化测试（真实执行，成功）

使用 `/tmp/cs5481-probe-venv`（Python 3.13.12，依赖版本与项目 `.venv` 相同）：

```
$ ruff check . --fix
Found 10 errors (10 fixed, 0 remaining).     # 10 处均为 import 排序 / 未使用导入
$ ruff check .
All checks passed!
```

```
$ python -m pytest -q
...........ss................................                            [100%]
```

` .pytest_cache/v/cache/nodeids ` 记录共 **45 个测试**，其中
`tests/test_e2e_real.py` 的 2 个标 `real` 且默认 skip →
**43 passed, 2 skipped, 0 failed**。

测试覆盖：M1 出处/异常、M2 逐字切片不变式与两种策略、M3 契约与缺密钥报错、
M4 真实 Chroma 持久化与 top-k 排序、M5 引用校验与四类拒答、MOCK 全链路。
**这些是单元测试与 MOCK 结果，不是实验指标。**

---

## 4. CLI 真实运行（真实执行，成功）

### 4.1 MOCK 演示（明确标注，不可用于报告）

```
$ python -m ragkit.cli offline-demo
==============================================================================
[MOCK / OFFLINE DEMO] synthetic fixtures + scripted doubles. No network, no API key, no vector database, no real documents.
==============================================================================
MOCK fixtures: 2 docs -> 7 chunks
--- normal answer with a citation ---
abstained=False  citations=['mock_alpha#0002']
citations_verified=True
--- fabricated citation must be rejected ---
abstained=True  citations=[]
--- unanswerable question must be refused ---
abstained=True  citations=[]
EXIT=0
```

### 4.2 REAL 入库（真实语料 + 真实本地 embedding + 真实 Chroma）

```
$ python -m ragkit.cli ingest
[REAL] real documents / real embeddings / real Chroma index
    strategy : fixed (size=600, overlap=80)
    embedding: local (dim=384)
OK: 4 documents -> 28 chunks stored in collection 'chunks_fixed'
EXIT=0
```

### 4.3 REAL 语义检索

```
$ python -m ragkit.cli retrieve "What is retrieval-augmented generation?"
[REAL] real documents / real embeddings / real Chroma index
#1 score=0.6146 id=rag_wikipedia#0006  chars 3101-3701
   source   : https://en.wikipedia.org/wiki/Retrieval-augmented_generation
   license  : CC BY-SA 4.0
#2 score=0.6006 id=rag_wikipedia#0000  chars 0-598
#3 score=0.5792 id=rag_wikipedia#0003  chars 1547-2143
These chunk ids are exactly what `cli ask` may cite.
EXIT=0
```

> 上面的 score 是**单次检索的原始输出**，不是"检索命中率"，也不是 chunking 对比实验结果。
> 它只用于证明向量检索链路可用、chunk id 与出处可回查。

### 4.4 无密钥时的 `ask`（预期失败，如实记录）

```
$ python -m ragkit.cli ask "When was RAG first proposed?"
Cannot run a REAL LLM answer: OPENAI_API_KEY is not set. ...
EXIT=2
```

系统明确拒绝，而不是伪造一条答案。

---

## 5. 按 README 建立项目 `.venv`：安装成功，复跑遇到会话级沙箱限制

```
python3 -m venv .venv
./.venv/bin/python -m pip install -q -r requirements-dev.txt
INSTALL_EXIT=0
venv OK: chromadb 1.5.9 | openai 1.109.1 | pytest 8.4.2
ruff 0.17.5
```

随后**用该 `.venv` 复跑**时，当前工具会话的沙箱开始阻止临时文件创建，出现：

```
pytest: FileNotFoundError: No usable temporary directory found in
  ['/tmp', '/tmp', '/var/tmp', '/usr/tmp', '<project dir>']  (tempfile.TemporaryFile)
chromadb.errors.InternalError: error returned from database: (code: 2570) disk I/O error
git init: fatal: could not set 'core.repositoryformatversion' to '0'
```

诊断命令确认这**不是项目代码问题**：

```
$ TMPDIR=/tmp python -c "import tempfile; print(tempfile.mkdtemp())"        -> 同样报错
$ TMPDIR=<project>/.tmp python -c "import tempfile; print(tempfile.mkdtemp())" -> 同样报错
$ ruff check .                                                              -> All checks passed!
$ grep -nE '^(from|import) ' ragkit/contracts.py
  from __future__ import annotations
  from collections.abc import Sequence
  from dataclasses import dataclass, field
  from typing import Any, Protocol        # 零第三方依赖，验收项 8 通过
```

同一套代码在几分钟前用同一 Python 3.13.12、同一依赖版本的独立 venv 已完整跑通（第 3、4 节）。
按沙箱提示，没有反复重试同一条命令；改为在项目内新建临时目录重试也失败，故判定为会话级限制。

**因此验收结论以第 3、4 节的真实成功输出为准**；安装步骤本身也确实成功（INSTALL_EXIT=0）。
该限制属于本机当前会话环境，换一个终端 / 新会话即可按 README 正常复现。

---

## 6. 仓库安全核对（真实执行）

```
Grep "sk-[A-Za-z0-9]{16,}"            -> No matches found
Grep "OPENAI_API_KEY\s*=\s*\S+"       -> No matches found
```

`.gitignore` 已排除：`.env` / `.env.*`（保留 `.env.example`）、`.venv/`、`__pycache__/`、
`.pytest_cache/`、`.ruff_cache/`、`data/index/*`（保留 `.gitkeep`）、`eval/results/`、
`*.log`、`.tmp/`，以及工具会话残留的无扩展名 8 字符临时文件。
`config.toml` 只含非敏感参数；密钥只从环境变量 / `.env` 读取。

**本地 `git init` 未成功完成**（见第 5 节），且没有连接任何 GitHub 远程仓库。
因此 **GitHub Actions CI 未在云端实际运行过** —— `ci.yml` 与分支保护规则是交付的配置，
由组长按 `CONTRIBUTING.md` 第 1 节在 GitHub 侧启用。这两项均如实标注为「未执行」。

---

## 7. 明确「未执行 / 未做」清单

| 项 | 状态 | 原因 |
| --- | --- | --- |
| `cli ask` 真实 LLM 生成 | **未执行** | 本机无 `OPENAI_API_KEY`；命令已实现并验证缺密钥时明确拒绝 |
| `pytest -m real`（真实 E2E） | **未执行** | 默认 skip；需 `RUN_REAL_E2E=1`，LLM 用例另需密钥 |
| GitHub Actions 云端 CI / 分支保护 | **未执行** | 无远程仓库，配置已交付 |
| 20 组正式 QA 与 gold chunk id | **未做** | 按约束，本期只定义格式（`eval/qa_template.csv` 仅 2 行示例） |
| 两种 chunking 对比实验、命中率/正确率/拒答率数字 | **未做** | 按约束，不提前完成正式实验 |
| 评测脚本、阈值调参、rerank、UI、报告与 slides | **未做** | 后续 PR |

---

## 8. 本次交付的文件

```
README.md  CONTRIBUTING.md  RUNLOG.md  docs/ARCHITECTURE.md
config.toml  pyproject.toml  requirements.txt  requirements-dev.txt
.env.example  .gitignore
.github/workflows/ci.yml  .github/pull_request_template.md
ragkit/{__init__,contracts,config,loaders,chunking,embeddings,store,generation,pipeline,cli}.py
data/raw/{SOURCES.md,manifest.json,rag_wikipedia.txt,vector_db_wikipedia.txt,
          word_embedding_wikipedia.txt,bm25_wikipedia.txt}
data/index/.gitkeep
eval/{README.md,qa_template.csv}
scripts/fetch_corpus.py
tests/{__init__,fakes,test_loaders,test_chunking,test_embeddings,test_store,
       test_generation,test_pipeline_offline,test_e2e_real}.py
tests/fixtures/{manifest.json,mock_alpha.txt,mock_beta.txt}
```

`data/index/` 内的 Chroma 生成物是**本地生成物、已 gitignore**；每位组员按 README 自行
`ingest` 重建，不需要也不应该提交。

---

## 9. v1.1 修复记录（2026-11-13 晚，外部审阅后）

审阅结论：架构保留，修 5 处基础问题。**只修影响多人开发的基础缺陷，未提前完成任何正式实验。**

### 修了什么

| # | 问题 | 修复 |
| --- | --- | --- |
| 1 | `qa_template.csv` 用 `expected_chunk_ids` 当 gold；不同 chunking 策略 chunk id 不同，比较不可比 | 改为 `evidence_doc_id` + `evidence_quote`（原文逐字片段）；新增 `eval/evidence.py` 把引文定位到原始文档字符区间，用 `evidence_coverage()` 评分。`eval/README.md` 重写指标定义。示例引文实测位于 `rag_wikipedia.txt` chars **1651–1727** |
| 2 | `verify_citations()` 只证明来源存在，却被当作"回答正确" | 拆成 `citation_ids_valid()`（ID）、`citation_quotes_verbatim()`（原文）、`verify_citation_structure()`（1+2）、兼容别名 `verify_citations()`；明确第 3 层"内容支持回答"只能由人工/披露的 LLM judge 判定。CLI 输出改为分别打印三层状态 + 免责说明。新增回归测试：答案说 9090 而引文是 8080，结构校验仍为 True |
| 3 | `ParagraphChunker` 忽略 `overlap`，meta 却写 `chunk_overlap` | paragraph 现在通过 `_apply_overlap()` 真正应用 overlap（以前一个 chunk 的 end 为基准，避免段落空行导致少 2 字符）；`chunk_overlap_actual` 记录**实际**字符重叠数，并同步写入/读出 Chroma 元数据。`fixed` 原滑动窗口行为不变（最小修改） |
| 4 | 部分断言只验证输出非空；拒答可能通过正常回答测试 | 正常回答测试现在断言 `not abstained` + 答案含 `8080` + 引用的 `doc_id` + 三层校验；新增"正常回答 vs 拒答可区分"测试；拒答测试断言 `ABSTAIN_MESSAGE` 与 `raw == "NO_ANSWER"`；检索测试断言命中文档；ingest 计数改为确定性精确值 6；新增 overlap 元数据回归测试 |
| 5 | 需确认正常本地环境可安装运行 | 见下方真实输出 |

新增文件：`eval/evidence.py`、`eval/__init__.py`、`tests/test_eval_evidence.py`。
修改：`ragkit/chunking.py`、`ragkit/store.py`、`ragkit/generation.py`、`ragkit/cli.py`、
`eval/README.md`、`eval/qa_template.csv`、`tests/test_chunking.py`、
`tests/test_generation.py`、`tests/test_pipeline_offline.py`、`docs/ARCHITECTURE.md`。

### 真实运行输出（本轮）

```
$ ruff check .
All checks passed!

$ python -m pytest -o addopts="" --basetemp=.tmp/pytest-basetemp-confirm -ra
tests/test_chunking.py .................                              [ 23%]
tests/test_e2e_real.py ss                                            [ 27%]
tests/test_embeddings.py .....                                        [ 35%]
tests/test_eval_evidence.py ......                                   [ 45%]
tests/test_generation.py .............                               [ 67%]
tests/test_loaders.py ........                                        [ 81%]
tests/test_pipeline_offline.py ......                                 [ 91%]
tests/test_store.py .....                                             [100%]
================ 57 passed, 2 skipped in 3.41s =================

$ python -m ragkit.cli offline-demo        # MOCK
[MOCK / OFFLINE DEMO] ...
MOCK fixtures: 2 docs -> 7 chunks
abstained=False  citations=['mock_alpha#0002']
structure_verified=True (id + verbatim quote ONLY; NOT factual correctness)
--- 编造引用被拒 / 无答案拒答：两个 case 均 abstained=True ---
```

```
$ python -m ragkit.cli ingest             # REAL
[REAL] real documents / real embeddings / real Chroma index
OK: 4 documents -> 28 chunks stored in collection 'chunks_fixed'

$ python -m ragkit.cli retrieve "When was retrieval-augmented generation first proposed?" --top-k 2
#1 score=0.5770 id=rag_wikipedia#0003  chars 1547-2143
#2 score=0.5449 id=rag_wikipedia#0000  chars 0-598
   source: https://en.wikipedia.org/wiki/Retrieval-augmented_generation
```

> #1 的原文片段正好包含 gold 证据引文 "The term ... introduced in a 2020 paper"，
> 与 `eval/qa_template.csv` 的 SAMPLE-001 一致。这是单次检索输出，**不是命中率指标**。

### 本轮遇到的环境异常（与代码无关）

一次 `pytest -q` 报 `FileExistsError: EEXIST: mkdir '/private/tmp/pytest-of-unknown'`，
来自工具沙箱的 `sitecustomize` 对系统临时目录的拦截。改用项目内独立
`--basetemp=.tmp/pytest-basetemp*` 后完整通过。GitHub Actions 的干净 runner
不受此影响，CI 仍使用标准 `python -m pytest -q`。

### 本轮仍未执行

- 真实 LLM 回答（`cli ask`）、`pytest -m real`：**未执行**，无 `OPENAI_API_KEY`，
  且任何付费 API 调用需全组先确认方案。
- 20 组正式 QA、chunking 对比实验、任何命中率/正确率数字：**未做**，属五人任务包 T2/T4。
- GitHub Actions 云端运行：见第 10 节（本轮后续补记）。

---

## 10. GitHub 共享工程建立记录（2026-11-13 晚）

### 环境检查（真实执行）

```
git version 2.54.0 (Apple Git-157)
gh version 2.102.0
gh auth status -> Logged in to github.com account 537Lab (keyring)
                  Token scopes: 'gist', 'read:org', 'repo', 'workflow'
                  （token 值未读取、未展示、未写入任何文件）
本地此前无完整 git 仓库（仅残留不完整的 .git 目录，已移到 .tmp/ 备份）
```

### 初始化、核查、提交、推送

```
git init -b main
git add -A                      -> 47 个文件
精确核查：无 .env / .venv / 缓存 / Chroma 生成物 / eval/results/
git grep --cached 'sk-[A-Za-z0-9]{16,}'                 -> 无命中
git grep --cached 'OPENAI_API_KEY\s*=\s*\S+'            -> 无命中
git show :.env.example                                  -> OPENAI_API_KEY= （空值模板）
git commit a12bb14 "chore: v1.1 baseline after external review ..."

gh repo create cs5481-rag-project --private --source=. --remote=origin --push
  -> 仓库创建成功（PRIVATE），但 git push 报 "HTTP2 framing layer"
git -c http.version=HTTP/1.1 push  -> "CONNECT tunnel failed, response 502"（注入代理 55013 不通）
实测：Clash 7897 对 github.com HTTP 200；肥猫云 7892 端口未监听
https_proxy=http://127.0.0.1:7897 git -c http.version=HTTP/1.1 push -u origin main
  -> * [new branch] main -> main（成功）
gh repo view -> {"defaultBranchRef":{"name":"main"},"visibility":"PRIVATE"}
```

仓库地址：**https://github.com/537Lab/cs5481-rag-project**

### GitHub Actions 真实运行（关键验收）

```
gh workflow list -> ci  active
gh run watch 43423374183 --exit-status -> WATCH_EXIT=0
gh run view 43423374183 --json status,conclusion,jobs
  -> {"conclusion":"success","status":"completed","steps":[
       "Set up job","Run actions/checkout@v4","Run actions/setup-python@v5",
       "Install dependencies","Static check (ruff)","Tests (offline)",
       "Verify no secret was committed", ... "Complete job"]}
```

即**云端 CI 实际跑过并成功**：`ruff`、离线 `pytest`、密钥扫描三步全绿。
仅有 GitHub 的 Node.js 20 / ubuntu-latest 迁移提示（annotation），不影响结果。

### 协作规则与权限限制（如实记录）

```
gh api PATCH repos/... -f allow_auto_merge=false
  -> {"allow_auto_merge":false,"allow_merge_commit":true,"allow_squash_merge":true}

gh api PUT .../branches/main/protection    -> 403 Upgrade to GitHub Pro ...
gh api POST .../rulesets                   -> 403 Upgrade to GitHub Pro ...
```

GitHub Free + 私有仓库**不支持**强制分支保护 / Rulesets。按"不卡住项目"的要求，
采用文档化替代流程：关闭自动合并 + PR 模板自检 + `CONTRIBUTING.md` 规定
"CI 绿灯且至少 1 名其他组员 Approve，由非作者手动 Squash merge"，由人工执行。
**这不是系统强制**，已在 `START_HERE.md` 与 `CONTRIBUTING.md` 明确标注。

### 需要用户本人操作的事项

1. 在 GitHub `Settings → Collaborators` 邀请另外 4 名组员（私有仓库，未被邀请看不到）。
2. 若希望强制保护：升级 GitHub Pro，或全组讨论是否改为 public（**未擅自改动可见性**）。
3. 真实 LLM API 调用：需提供密钥并确认费用/额度方案后才执行；目前**零付费调用**。

### 补记：bootstrap 完成

- 二次提交 `3f3176a`（`START_HERE.md`、`docs/TASKS.md`、`docs/DEV_LOG.md`、
  `docs/AI_USAGE.md`、`CONTRIBUTING.md`、PR 模板、README、RUNLOG）已推 `main`；
  第二次 CI run `43424432557` → **completed / success**（`ruff` + `pytest` + 密钥扫描）。
- 5 个 GitHub Issues **#1–#5**（T1–T5）已创建，全部带 `task` 标签，供组员认领。
- 对**远端仓库文件树**做了最终核查（`gh api .../git/trees/main?recursive=1`）：
  62 个条目，**无** `.env` / `.venv` / 缓存 / `chroma.sqlite` / `.tmp/` / `eval/results/` /
  `__pycache__`；`START_HERE.md` 等关键文档均在远端。
- 本地 `git status --short` 为空（干净），`origin/main` 与本地 `main` 一致。
- 本地全量测试最终状态：`57 passed, 2 skipped`；`ruff check .` 通过。

---

## 11. T4 评测集与指标（2026-11-14，组员实际执行）

环境：Windows + 仓库内 `.venv`，`Python 3.13.5`（与第 1 节探测环境的 3.13.12 不同，
为组员本机新建的 venv）。**零付费调用**：本节所有数字都来自本地 ONNX embedding +
本地 Chroma，无需 `OPENAI_API_KEY`。索引沿用第 9 节 `cli ingest` 建立的
`chunks_fixed`（4 docs → 28 chunks），T4 未重新入库。

交付：`eval/qa_set.csv`（35 条）、`eval/metrics.py`、`eval/judge_protocol.md`、
`tests/test_eval_metrics.py`，并把 `eval/README.md` 从「只有定义、尚无实现」改写为
「定义 + T4 实现说明」。

### 11.1 验收命令（真实执行）

```
$ python -m eval.metrics --help
usage: python -m eval.metrics [-h] [--config CONFIG] {validate,retrieval,score,mock-demo} ...
CS5481 Topic 5 T4: QA set validation and evaluation metrics

$ python -m eval.metrics validate
exit=0
[REAL] validated qa_set.csv: 35 items (27 answerable, 8 unanswerable)
documents consulted: 4; all 27 gold quotes resolve to a source character span
  bm25_wikipedia               4 answerable items
  rag_wikipedia               10 answerable items
  vector_db_wikipedia          8 answerable items
  word_embedding_wikipedia     5 answerable items
gold span sample (strategy-independent):
  A01 rag_wikipedia chars 0-165
  A02 rag_wikipedia chars 166-255
  A03 rag_wikipedia chars 580-689
unanswerable absence checks: 10 tokens confirmed absent from the corpus

$ python -m pytest -o addopts="" -q tests/test_eval_metrics.py tests/test_eval_evidence.py
exit=0
45 passed in 0.37s

$ python -m ruff check .
All checks passed!

$ python -m pytest -o addopts="" -q
exit=0
96 passed, 2 skipped in 4.22s
```

> 注：`pyproject.toml` 里 `addopts = "-q"`，命令行再写 `-q` 等于 `-qq`，pytest 会
> **省略最后那行汇总**（只剩进度点）。上面的记录用 `-o addopts=""` 让汇总行显式出现；
> 不加该参数时命令同样 `exit=0`，只是看不到计数行。

### 11.2 REAL 检索命中率（真实执行，两轮结果一致）

```
$ python -m eval.metrics retrieval --hits 1,3 --min-coverage 0.5 --out eval/results/retrieval_fixed.json
exit=0
[REAL] retrieval evaluation: real corpus / real embeddings / real Chroma index
    collection : chunks_fixed (chunks=28)
    embedding  : local dim=384
    hit@k      : levels (1, 3), min_coverage=0.5

[REAL] retrieval metrics
  min_coverage               0.5
  n_items                    35
  n_answerable               27
  n_unanswerable             8
  hit@1                       16/27  0.5926
  hit@3                       23/27  0.8519

wrote eval\results\retrieval_fixed.json
```

同一条命令连跑两轮得到完全相同的 `16/27` 与 `23/27`，命中率对本地 embedding 是
确定性的。`eval/results/` 已在 `.gitignore` 中，结果文件不入库；报告引用时需同时
写明上面的命令与 `--min-coverage 0.5`。结果 JSON 自带 provenance：

```json
{
 "command": "python -m eval.metrics retrieval --hits 1,3 --min-coverage 0.5 --out eval/results/retrieval_fixed.json",
 "config": {"corpus_manifest": "data/raw/manifest.json", "chunking": "fixed",
            "chunk_size": 600, "chunk_overlap": 80, "collection": "chunks_fixed",
            "embedding": "local:384d", "llm_model": "gpt-4o-mini",
            "qa_items": 35, "python": "3.13.5"}
}
```

### 11.3 top-3 未命中的真实失败案例（供 T2/T5 分析）

`first_hit_rank` 分布：rank1 = 16、rank2 = 5、rank3 = 2、top-3 内未命中 = 4（合计 27）。
四个未命中逐个回查了索引中的块边界与实际排名（`retrieve(k=8)`）：

| qid | 问题 | gold span | 能完全覆盖的块 | 该块真实排名 | 定性 |
| --- | --- | --- | --- | --- | --- |
| A03 | When was RAG first proposed? | `rag_wikipedia` 580–689（109 字） | `rag_wikipedia#0001`（518–1113，覆盖率 1.0） | **6**（score 0.3588） | 排序问题；top-3 只拿到部分覆盖的 `#0000`（0.1651） |
| A14 | goal when feature vectors are computed from raw data? | `vector_db_wikipedia` 1170–1263（93 字） | `vector_db_wikipedia#0002`（1035–1635，1.0） | **4** | 差一名，top_k=4 就能命中 |
| A17 | at query time, what is computed from the user's prompt? | `vector_db_wikipedia` 2905–3040（135 字） | `vector_db_wikipedia#0005`（2584–3179，1.0） | **8** | 纯排序问题，目标块根本不在前列 |
| A18 | after retrieval, how does the LLM use the documents? | `vector_db_wikipedia` 3041–3221（180 字，跨块边界） | **没有单块完全覆盖**；`#0005` 0.7667 / `#0006` 0.6778 | 两者均不在 top-3 | 边界切开 + 排序双重问题 |

结论（写报告时按这个口径，不要笼统归因）：

- 四个 miss 中只有 A18 真正反映了**分块边界**问题；A03/A14/A17 的目标块本身完整存在、
  覆盖率 1.0，只是没进 top-3，属于**语义排序**问题，与 chunking 策略无关，换 `paragraph`
  不一定会好。
- A18 也说明了为什么 hit 用 `evidence_coverage >= 0.5` 而不是「块必须包含整个 gold span」：
  被切成 0.77 / 0.68 两块的句子，任一块都仍然包含足够语义。
- **分数不能当取舍依据**（对 T3 直接有用，均取自本轮 `retrieval_fixed.json` 的实记数据）：
  四个未命中查询的 top-3 score 为 `0.3932–0.5770`，而 A03/A14/A17 真正含证据的块
  score 只有 `0.3135–0.3588`；16 个 hit@1 查询的 top-1 score 区间为 `0.3450–0.8338`，
  27 题全部 top-3 score 区间为 `0.1934–0.8338`。三个区间相互重叠，所以加 score 阈值
  不会把证据捞回来；提高 top_k（A14 只差一名，在 rank 4）或加关键词混合检索才是方向。

### 11.4 策略切换的空索引护栏（真实执行，预期失败）

```
$ python -m eval.metrics retrieval --chunking paragraph
exit=2
Collection 'chunks_paragraph' is empty. Run: python -m ragkit.cli ingest (or pass --chunking paragraph)
```

collection 名由 `Settings.collection_name` 按策略派生（`chunks_<strategy>`），所以
`--chunking paragraph` 不会读到 fixed 的索引，两种策略的数据不混。段落策略的索引
**本机尚未建立**，因此本节没有 paragraph 的命中率——那是 T2 的实验。

### 11.5 MOCK 端到端（明确标注，不得写进报告）

```
$ python -m eval.metrics mock-demo --hits 1,3
exit=0
==============================================================================
[MOCK] metric code exercise: fixtures + scripted doubles. NOT an experiment.
==============================================================================
[MOCK] answers metrics
  min_coverage               0.5
  n_items                    3
  n_answerable               2
  n_unanswerable             1
  false_abstention_rate        0/2   0.0000
  correct_abstention_rate      1/1   1.0000
  citation_structure_rate      2/2   1.0000
  answer_correctness           2/2   1.0000
  n_graded                   2
  hit@1                        1/2   0.5000
  hit@3                        2/2   1.0000

These numbers describe MOCK fixtures only. Do not put them in the report.
```

这里的 `answer_correctness` 来自脚本化的 `grades={...: "correct"}`，属于双组件自测，
**不是**评测结果；只用于证明指标算式和 CLI 接线在离线环境可跑。

### 11.6 本轮明确未执行

- `python -m eval.metrics score --outputs ...`：**未真实执行**。它需要 T5 产出的
  `eval/results/run.json`，目前不存在。该路径由 `tests/test_eval_metrics.py` 用合成
  记录覆盖（含"结构校验通过但正确率为 0"的反例），加上上面的 MOCK 端到端。
- **人工 judge 尚未开始**，`eval/judge_protocol.md` 只是协议。因此
  **`answer_correctness` 目前没有任何数字**，不是 0，也不是待填占位，就是尚未测定；
  `metrics.py` 在没有 `--grades` 时输出 `"pending human grading"`。
- LLM-as-judge：**未执行**（无密钥、未经全组确认费用），条件见 `judge_protocol.md` §4。
- `paragraph` 策略的命中率：**未测定**（本机无该 collection）。
- 评分者一致性（raw agreement / Cohen's kappa）：**未计算**，需要两份人评 grades 文件。

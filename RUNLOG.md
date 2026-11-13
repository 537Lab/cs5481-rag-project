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

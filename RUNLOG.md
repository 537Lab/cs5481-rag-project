# 运行记录

记录日期：**2026-11-13（GMT+8）**。本文件只记录**真实执行过的命令与原始输出**；未执行的命令明确标注「未执行」。

记录原则：

- **区分执行主体**：本地命令由 AI Agent 在 bootstrap / 整理阶段代为执行；GitHub Actions 的结果来自云端
  runner。两者都不是「任何组员亲自运行」，也不等于人工复核。人工复核情况以
  [`docs/DEV_LOG.md`](docs/DEV_LOG.md) 和 [`docs/AI_USAGE.md`](docs/AI_USAGE.md) 为准。
- 项目定义、老师要求映射与交付标准见 [`docs/PROJECT_PLAN.md`](docs/PROJECT_PLAN.md)。
- MOCK（模拟）与 REAL（真实端到端）严格分开；不把 MOCK 输出当实验结果，不硬编码任何命中率 /
  正确率数字，不伪造「运行成功」。
- 本机网络、代理、临时目录等**个人环境排障**不属于团队共享信息，不写入本文件（已在本地归档）。
  本文件只保留与代码验收有关的命令与输出。

---

## 1. 基线阶段：本地验证（2026-11-13，由 AI Agent 执行）

### 1.1 依赖安装与静态检查

```
Python 3.13.12 / pip 26.0
chromadb 1.5.9   openai 1.109.1   pytest 8.4.2   ruff 0.17.5
INSTALL_EXIT=0

$ ruff check .
All checks passed!
```

### 1.2 离线测试（初始基线，历史数字）

```
$ python -m pytest -q
...........ss................................                            [100%]
collected 45 items -> 43 passed, 2 skipped, 0 failed
```

这是初始基线的历史记录；**当前**测试数量以第 4 节为准。这些是单元测试与 MOCK 结果，不是实验指标。

### 1.3 真实语料与本地模型

4 篇 Wikipedia CC BY-SA 4.0 摘录，出处与许可见 `data/raw/SOURCES.md`；每篇在
`data/raw/manifest.json` 中带 `source_uri` 与 `license`。模拟文档只在 `tests/fixtures/`，首行标注 MOCK。

```
OK rag_wikipedia                  4166 chars  <- Retrieval-augmented generation
OK vector_db_wikipedia            3245 chars  <- Vector database
OK word_embedding_wikipedia       3327 chars  <- Word embedding
OK bm25_wikipedia                 2874 chars  <- Okapi BM25
Wrote 4 documents and data/raw/manifest.json
```

本地 ONNX `all-MiniLM-L6-v2`：真实开源模型、384 维向量、本机推理、无需 API key；
首次下载约 80 MB 到 `~/.cache/chroma` 后完全离线。

```
LOCAL_ONNX_OK n=2 dim=384 secs=0.5
```

### 1.4 CLI 运行（MOCK 与 REAL 分开）

```
$ python -m ragkit.cli offline-demo             # MOCK
[MOCK / OFFLINE DEMO] synthetic fixtures + scripted doubles. No network, no API key, no vector database, no real documents.
MOCK fixtures: 2 docs -> 7 chunks
--- normal answer with a citation ---        abstained=False  citations=['mock_alpha#0002']
--- fabricated citation must be rejected --- abstained=True   citations=[]
--- unanswerable question must be refused --- abstained=True   citations=[]
EXIT=0

$ python -m ragkit.cli ingest                  # REAL
[REAL] real documents / real embeddings / real Chroma index
    strategy : fixed (size=600, overlap=80)
    embedding: local (dim=384)
OK: 4 documents -> 28 chunks stored in collection 'chunks_fixed'
EXIT=0

$ python -m ragkit.cli retrieve "What is retrieval-augmented generation?"   # REAL
#1 score=0.6146 id=rag_wikipedia#0006  chars 3101-3701
   source   : https://en.wikipedia.org/wiki/Retrieval-augmented_generation
   license  : CC BY-SA 4.0
#2 score=0.6006 id=rag_wikipedia#0000  chars 0-598
#3 score=0.5792 id=rag_wikipedia#0003  chars 1547-2143
EXIT=0

$ python -m ragkit.cli ask "When was RAG first proposed?"   # 预期失败
Cannot run a REAL LLM answer: OPENAI_API_KEY is not set. ...
EXIT=2
```

> 上面的 score 是**单次检索的原始输出**，不是「检索命中率」，也不是 chunking 对比实验结果；
> 它只用于证明向量检索链路可用、chunk id 与出处可回查。

---

## 2. 基线修订后的本地验证（2026-11-13，由 AI Agent 执行）

修订内容（设计说明见 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) 与
[`eval/README.md`](eval/README.md)，逐文件改动见 Git 历史）：

- gold 由 `expected_chunk_ids` 改为 `evidence_doc_id` + `evidence_quote`，新增
  `eval/evidence.py`、`eval/__init__.py`、`tests/test_eval_evidence.py`；
- 引用三层概念拆分，结构校验与事实正确性在命名、CLI 输出、测试与文档中区分；
- `ParagraphChunker` 真正应用 `overlap` 并记录 `chunk_overlap_actual`；
- 加固薄弱断言（拒答与正常回答可区分、ingest 计数用确定性精确值等）。

```
$ ruff check .
All checks passed!

$ python -m pytest -o addopts="" -ra --basetemp=<独立临时目录>
collected 59 items
tests/test_chunking.py ..............   tests/test_e2e_real.py ss
tests/test_embeddings.py .....         tests/test_eval_evidence.py ......
tests/test_generation.py ............. tests/test_loaders.py ........
tests/test_pipeline_offline.py ......  tests/test_store.py .....
================ 57 passed, 2 skipped in 3.41s =================
```

`cli offline-demo`（MOCK）、`cli ingest`（4 → 28 chunks，REAL）、`cli retrieve`（REAL，带出处）
在本阶段同样真实运行成功，输出与第 1.4 节同形态。

---

## 3. 云端 CI 与仓库设置（GitHub Actions / API，独立于本地命令）

```
gh run list
  43423374183  main push  completed/success  2026-11-13T12:13:39Z
  43424432557  main push  completed/success  2026-11-13T12:21:15Z
  43424841221  main push  completed/success  2026-11-13T12:24:12Z
ci / check steps: checkout, setup-python (3.11), Install dependencies,
                  Static check (ruff), Tests (offline), Verify no secret was committed

gh api repos/537Lab/cs5481-rag-project
  {"default_branch":"main","visibility":"PRIVATE","allow_auto_merge":false,
   "allow_squash_merge":true,"has_issues":true}
gh api .../branches/main/protection  -> 403 Upgrade to GitHub Pro or make this repository public ...
gh api .../rulesets                  -> 403 (同上)
gh issue list --state all           -> #1–#5，全部 OPEN 且带 task 标签
```

说明：

- 这三次 `success` 是**云端 runner** 的验证结果，不是本地命令，也不是任何人手工运行的结果。
- CI 完全离线：不需要密钥、不下载模型，`tests/test_e2e_real.py` 默认跳过。
- 强制分支保护 / Rulesets 在当前套餐下不可用；`CONTRIBUTING.md` 中的 review 规则靠人工执行。
- 早期记录中「尚无远程仓库、CI 未运行」的状态已过时，以本节为准。

---

## 4. 仓库规范化整理（2026-11-13，本轮，由 AI Agent 执行）

范围：文档重写、路径与事实修正、实验结果管理规范。**未改动 `ragkit/` 任何核心模块接口，
未新增或生成任何正式实验数据，未重写 Git 历史。**

按 README / START_HERE 的流程安装并复跑：

```
$ python3 -m venv .venv
$ python -m pip install -r requirements-dev.txt
INSTALL_OK  chromadb 1.5.9 | onnxruntime 1.32.0 | openai 1.109.1 | pytest 8.4.2 | ruff 0.17.5

$ ruff check .
All checks passed!                       EXIT=0

$ python -m pytest -o addopts="" -ra --basetemp=.tmp/pytest-QylZv3
platform darwin -- Python 3.13.12, pytest-8.4.2
collected 59 items
tests/test_chunking.py ..............   tests/test_e2e_real.py ss
tests/test_embeddings.py .....         tests/test_eval_evidence.py ......
tests/test_generation.py ............. tests/test_loaders.py ........
tests/test_pipeline_offline.py ......  tests/test_store.py .....
SKIPPED [1] tests/test_e2e_real.py:29: set RUN_REAL_E2E=1 to run real end-to-end checks
SKIPPED [1] tests/test_e2e_real.py:50: set RUN_REAL_E2E=1 to run real end-to-end checks
================ 57 passed, 2 skipped in 2.07s =================   EXIT=0

$ python -m ragkit.cli offline-demo   -> EXIT=0，[MOCK / OFFLINE DEMO] 横幅 + 3 个案例
$ python -m ragkit.cli ingest         -> OK: 4 documents -> 28 chunks stored in collection 'chunks_fixed'  EXIT=0
$ python -m ragkit.cli retrieve "What is retrieval-augmented generation?" --top-k 3
  #1 score=0.6146 id=rag_wikipedia#0006  chars 3101-3701  source=CC BY-SA 4.0   EXIT=0
```

仓库安全核对：

```
git grep -nE 'sk-[A-Za-z0-9]{16,}' -- . ':!*.md'   -> 无命中
git grep -nE 'OPENAI_API_KEY\s*=\s*\S+'            -> 无命中（.env.example 为空值模板）
暂存内容不含 .env / .venv / .tmp / data/index / eval/results/raw/
```

本轮 PR 的 GitHub Actions 结果见 PR 页面 `ci / check`；合并前须为绿色。

---

## 5. 明确「未执行 / 未做」清单

| 项 | 状态 | 原因 / 归属 |
| --- | --- | --- |
| `cli ask` 真实 LLM 生成 | **未执行** | 无 `OPENAI_API_KEY`；已验证缺密钥时明确拒绝（EXIT=2） |
| `pytest -m real`（真实 E2E） | **未执行** | 默认 skip；需 `RUN_REAL_E2E=1`，LLM 用例另需密钥 |
| ≥20 组正式 QA 与 gold 证据 | **未做** | T4；`eval/qa_template.csv` 目前只有 2 行格式示例 |
| 两种 chunking 对比实验、命中率 / 正确率 / 拒答率、图表 | **未做** | T2 / T4；真实可复现结果的提交规范见 `eval/README.md` |
| 评测脚本、judge、阈值调参、rerank、UI、报告与 slides | **未做** | 后续 PR |
| 付费 LLM API 调用 | **零次** | 需先由全组确认费用方案 |
| 正式语料扩充与冻结快照 | **未做** | T1；冻结规则见 `docs/PROJECT_PLAN.md` §6.6 |
| 四名组员的开发贡献 | **尚无** | 仓库为私有，尚未邀请 Collaborator；见 `CONTRIBUTING.md` 第 1 节 |

---

## 6. 项目定义与协作计划定稿（2026-11-14，本轮，由 AI Agent 执行）

范围：只改文档与 GitHub Issues。**未修改 `ragkit/` 任何核心模块、未生成语料 / QA / 实验结果、
未执行任何付费 API 调用。** 变更清单见对应 PR。

### 6.1 文档相对链接与锚点检查

```
$ python3 .tmp/check_links.py
markdown files: 13 | relative links checked: 67
OK: all relative links and anchors resolve
LINK_EXIT=0
```

### 6.2 身份标签与过时引用扫描

```
$ git grep -n -E '组[.]?长|gold[_]?v0' -- .
NONE
```

（模式用字符类写成 `组[.]?长` / `gold[_]?v0`，以便本行自身不被匹配；等价于扫描
「预设身份标签」与「不存在的旧文件名」。）

### 6.3 密钥形态扫描（与 CI 同规则）

```
$ git grep -nE 'sk-[A-Za-z0-9]{16,}' -- . ':!*.md'
NONE
```

### 6.4 未能在本机执行的检查（如实记录）

```
$ .venv/bin/ruff check --no-cache .
blocked: 本机沙箱禁止写入/删除临时目录（ruff 无法落临时文件），未得到检查结论

$ .venv/bin/python -m pytest -q
blocked: tempfile 无法找到可用临时目录（同一沙箱限制），未得到测试结论
```

- 这两项**不是通过**，也**不是失败**，而是本机环境限制导致未执行。
- 本轮**没有改动任何 `.py` 文件**，因此预期不影响现有 57 passed / 2 skipped；
  最终以 PR 的 GitHub Actions `ci / check`（ruff + 离线 pytest + 密钥扫描）为准。
- 不使用 MOCK 或推测结果替代真实运行。

### 6.5 GitHub Issues 同步

```
$ gh issue list --state open
#1 [T1] 正式知识库与文档处理              assignees: []
#2 [T2] Chunking 策略与对比实验            assignees: []
#3 [T3] 检索层与向量库                     assignees: []
#4 [T4] 评测集、指标实现与评分协议          assignees: []
#5 [T5] LLM 问答、引用支持性与可运行演示     assignees: []
```

五个 Issue 的正文已与 `docs/PROJECT_PLAN.md`、`docs/TASKS.md` 对齐：移除预设身份标签，
删除对不存在的旧 gold 文件（`tests/fixtures/` 下）的依赖，补上 T4 对 T1 冻结语料的依赖，
并明确 T4 是唯一指标实现。

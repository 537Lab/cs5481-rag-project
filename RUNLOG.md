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

---

## 7. T4 首轮交付：评测集与指标（2026-11-14，组员实际执行）

> **本节的来历**：这些内容首轮写在 `RUNLOG.md` 第 11 节（提交 `9465263`）。合并
> `origin/main`（PR #8）时四个团队文档按「以 main 为准」处理，main 重新编排了本文件的
> 章节，于是首轮记录被覆盖丢失。此处按新编号恢复为**历史快照**，输出内容未改写，
> 只把交叉引用 `第 9 节` 更正为 `第 1.4 节`、把已被新提交规范取代的结果文件路径标注出来。
> 合并事故本身的记录见第 8.7 节。

环境：Windows + 仓库内 `.venv`，`Python 3.13.5`（与第 1 节探测环境的 3.13.12 不同，
为组员本机新建的 venv）。**零付费调用**：本节所有数字都来自本地 ONNX embedding +
本地 Chroma，无需 `OPENAI_API_KEY`。索引沿用第 1.4 节 `cli ingest` 建立的
`chunks_fixed`（4 docs → 28 chunks），T4 未重新入库。

交付：`eval/qa_set.csv`（35 条）、`eval/metrics.py`、`eval/judge_protocol.md`、
`tests/test_eval_metrics.py`，并把 `eval/README.md` 从「只有定义、尚无实现」改写为
「定义 + T4 实现说明」。

### 7.1 验收命令（真实执行）

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

### 7.2 REAL 检索命中率（真实执行，两轮结果一致）

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

> **路径已变更**：首轮写在 `eval/results/retrieval_fixed.json`。PR #8 之后提交规范要求
> 原始逐条结果放 `eval/results/raw/`（已 gitignore），汇总放 `eval/results/summary/`（入库），
> 而当前 `.gitignore` 只忽略 `eval/results/raw/`。第 8 节改用 `--out eval/results/raw/retrieval_fixed.json`。

### 7.3 top-3 未命中的真实失败案例（供 T2/T5 分析）

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
- **分数不能当取舍依据**（对 T3 直接有用，均取自首轮 `retrieval_fixed.json` 的实记数据）：
  四个未命中查询的 top-3 score 为 `0.3932–0.5770`，而 A03/A14/A17 真正含证据的块
  score 只有 `0.3135–0.3588`；16 个 hit@1 查询的 top-1 score 区间为 `0.3450–0.8338`，
  27 题全部 top-3 score 区间为 `0.1934–0.8338`。三个区间相互重叠，所以加 score 阈值
  不会把证据捞回来；提高 top_k（A14 只差一名，在 rank 4）或加关键词混合检索才是方向。

### 7.4 策略切换的空索引护栏（真实执行，预期失败）

```
$ python -m eval.metrics retrieval --chunking paragraph
exit=2
Collection 'chunks_paragraph' is empty. Run: python -m ragkit.cli ingest (or pass --chunking paragraph)
```

collection 名由 `Settings.collection_name` 按策略派生（`chunks_<strategy>`），所以
`--chunking paragraph` 不会读到 fixed 的索引，两种策略的数据不混。段落策略的索引
**本机尚未建立**，因此本节没有 paragraph 的命中率——那是 T2 的实验。

### 7.5 MOCK 端到端（明确标注，不得写进报告）

首轮的 `mock-demo` 只跑通指标算式与 CLI 接线，`answer_correctness` 来自脚本化的
`grades={...: "correct"}`，属于双组件自测，**不是**评测结果。完整输出可在本机重跑
`python -m eval.metrics mock-demo --hits 1,3` 取得（第 8.6 节记录了本轮的实际输出）。

### 7.6 首轮明确未执行

- `python -m eval.metrics score --outputs ...`：**未真实执行**。它需要 T5 产出的
  答案产物，当时不存在。该路径由 `tests/test_eval_metrics.py` 用合成记录覆盖
  （含「结构校验通过但正确率为 0」的反例），加上 MOCK 端到端。
  （本轮已用 I4 格式产物打通，见第 8.4 节。）
- **人工 judge 尚未开始**，`eval/judge_protocol.md` 只是协议。因此
  **`answer_correctness` 没有数字**，不是 0，也不是待填占位，就是尚未测定；
  `metrics.py` 在没有 `--grades` 时输出 `"pending human grading"`。
- LLM-as-judge：**未执行**（无密钥、未经全组确认费用），条件见 `judge_protocol.md` §4。
- `paragraph` 策略的命中率：**未测定**（本机无该 collection）。
- 评分者一致性（raw agreement / Cohen's kappa）：**未计算**，需要两份人评 grades 文件。

---

## 8. T4 同步修订：按 PR #8 的 I3 / I4 / I5 接口对齐（2026-11-15，组员实际执行）

组员对 PR #8 提了 5 条意见，本轮逐条处理；**原有代码与测试保留**，只改与接口不一致的局部。
执行环境与首轮相同（Windows + `.venv` + Python 3.13.5，本地 ONNX embedding + 本地 Chroma，**零付费调用**）。

| # | 组员意见 | 本轮做法 | 锁定它的测试 |
| --- | --- | --- | --- |
| 1 | 分支与 main 有 4 个文档冲突 | `git merge origin/main`（合并提交 `0123745`），4 个冲突文件均**以 main 为准**；丢失的首轮记录恢复为第 7 节 | —（文档） |
| 2 | 支持 JSONL 与 `retrieved_chunk_ids` | `score --run-id <id>` 读 `eval/answers/<id>.jsonl`，嵌套 `answer` 扁平化，旧键 `retrieved_ids` 仍接受 | `test_jsonl_artifact_is_read_and_the_nested_answer_is_flattened`、`test_an_i4_record_scores_exactly_like_the_earlier_flat_record` |
| 3 | 正确率分母不能含不可回答题 | 分母改为**已评分的 answerable 题**；新增 `n_gradable` / `grading_coverage` / `grades_dropped_as_unanswerable` | `test_unanswerable_grades_never_enter_the_correctness_denominator`、`test_grading_coverage_exposes_the_ungraded_remainder` |
| 4 | `ABSENT_TOKENS` 只是必要条件 | 文档说明 + 机器门：每条拒答题需 `REVIEWED_BY: <name>` 佐证，`--require-reviewed` 与 `--formal` 都会卡住 | `test_formal_review_gate_is_currently_closed_on_the_committed_set`（有意的翻转门） |
| 5 | 指标函数名跟新项目方案统一 | 按 I3 只暴露 `retrieval_hit_rate` / `answer_correctness` / `abstention_rates` / `citation_structure_rate` 四个公开函数，两个聚合器变薄（只加逐条行与 provenance，不定义第二套公式） | `test_i3_functions_are_importable_with_the_frozen_names`、`test_the_public_function_and_the_aggregator_return_the_same_numbers` |

同时按 I5 字段名重写了配置快照（`strategy/size/overlap/top_k/min_coverage/embedding/llm/corpus_ref/qa_set_ref`），
并新增 `--summary-dir/--formal/--executor` 写出 `eval/results/README.md` 要求的 `config.json` /
`metrics.json` / `run.md` 三件套。35 题按组员补充说明被定位为 **`CORPUS_V0` 上的开发测试集**
（`QA_SET_STATUS` 常量与 `validate` 输出都写明），正式数据集冻结后再重验 gold 引文。

### 8.1 验收命令（真实执行）

```
$ python -m ruff check .
exit=0
All checks passed!

$ python -m pytest -o addopts="" -q tests/test_eval_metrics.py
exit=0
67 passed in 0.40s

$ python -m pytest -o addopts="" -q tests/test_eval_metrics.py tests/test_eval_evidence.py
exit=0
73 passed in 0.44s

$ python -m pytest -o addopts="" -q
exit=0
124 passed, 2 skipped in 5.04s
```

验收双文件从首轮 45 passed 到 73 passed（+28 例），全量从 96 到 124（同样 +28）；新增全部落在
`tests/test_eval_metrics.py`（首轮 39 例 → 67 例）。本轮未删除任何首轮测试，
首轮用例全部仍在上述计数内。那 2 个 skipped 与首轮同源，不是本轮新增的：
`tests/test_e2e_real.py` 的真实端到端用例需要 `RUN_REAL_E2E=1` 才跑（其中一个还要 `OPENAI_API_KEY`），本机未开启。

### 8.2 意见 5：I3 函数名（真实执行）

```
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
unanswerable absence checks: 10 tokens confirmed absent from the corpus - a NECESSARY condition only, the absence of a word does not prove the corpus cannot answer the question
human review of unanswerable labels: 0/8 carry REVIEWED_BY (pending: N01, N02, N03, N04, N05, N06, N07, N08)
corpus checked against: data/raw/manifest.json@b5bfc0d70e4a; frozen snapshot (I1) absent: data/raw/frozen_manifest.json
QA set status: development set on CORPUS_V0, not the frozen formal QA set
```

`eval/metrics.py` 顶部现在直接定义这四个名字，`from eval.metrics import retrieval_hit_rate,
answer_correctness, abstention_rates, citation_structure_rate` 即可（已有单测逐项验证）。

命中率**本轮重算与首轮一致**（分母本来就是 27 题，改动不影响检索侧）：

```
$ python -m eval.metrics retrieval --hits 1,3 --min-coverage 0.5 --out eval/results/raw/retrieval_fixed.json
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

wrote eval\results\raw\retrieval_fixed.json
```

### 8.3 意见 2：接口 I4 产物端到端（真实执行）

为了在 T5 交付前就把链路跑通，本轮用 `.tmp/make_i4_artifact.py` 造了一个**严格符合 I4 形状**的
产物：检索环节是真的（直接读 `chunks_fixed` 索引的 top-3），答案文本由脚本从检索块拼接而来，
`model` 字段写明 `scripted-mock-generator`。**它只证明管道能读能算，不是实验结果**，所以始终带
`--label MOCK` 跑，跑完从 `eval/answers/` 删除（MOCK 产物不能占着 T5 要交的位置）。

一行记录的实际形状（A01）：

```json
{
 "qid": "A01",
 "answer": {
  "answer_text": "…", "abstained": false,
  "citations": [{"chunk_id": "rag_wikipedia#0001", "doc_id": "rag_wikipedia", "quote": "…"}],
  "model": "scripted-mock-generator", "raw": "…"
 },
 "retrieved_chunk_ids": ["rag_wikipedia#0001", "rag_wikipedia#0000", "rag_wikipedia#0002"],
 "run_id": "20261115-mock-i4",
 "config_ref": "eval/results/summary/example/config.json"
}
```

```
$ python -m eval.metrics score --run-id 20261115-mock-i4 --label MOCK
exit=0
[MOCK] scoring answer run: eval/answers/20261115-mock-i4.jsonl (run_id=20261115-mock-i4, records=35)
[MOCK] answers metrics
  min_coverage               0.5
  n_items                    35
  n_answerable               27
  n_unanswerable             8
  correct_abstention_rate      8/8   1.0000
  false_abstention_rate        0/27  0.0000
  citation_structure_rate     27/27  1.0000
  answer_correctness         pending human grading (no --grades file supplied)
  n_graded                   0
  n_gradable                 27
  grading_coverage             0/27  0.0000
  grade_counts               {'correct': 0, 'incorrect': 0, 'unsure': 0}
  hit@1                       16/27  0.5926
  hit@3                       23/27  0.8519
```

上面的 `8/8` 与 `27/27` 是脚本化双组件自己写的产物，**不能当系统能力引用**：前者是因为脚本对
每条 N 题都设了 `abstained=true`，后者是因为引用直接从检索块拷出来。它们的作用只有一个：证明
`retrieved_chunk_ids` → 结构校验、`abstained` → 拒答率这两条读取路径接得住。

评分表的来回也真实跑了一次（未填任何分数，因此不会凭空产生正确率）：

```
$ python -m eval.metrics score --run-id 20261115-mock-i4 --label MOCK --grading-sheet .tmp/grades_sheet.csv
exit=0
（同上指标输出）
wrote grading sheet .tmp\grades_sheet.csv

$ python -m eval.metrics score --run-id 20261115-mock-i4 --label MOCK --grades .tmp/grades_sheet.csv
exit=2
ERROR: .tmp\grades_sheet.csv has no graded rows; every grade cell is empty
```

即：空评分表**不会被当成「全错」**，而是直接拒绝。以下三个护栏也都真实碰过：

```
$ python -m eval.metrics score --run-id no-such-run
exit=2
ERROR: no answer artifact for --run-id 'no-such-run' in eval/answers: no-such-run.jsonl, no-such-run.ndjson, no-such-run.json

$ python -m eval.metrics score
exit=2
ERROR: score needs --outputs PATH or --run-id ID (see eval/answers/)

$ python -m eval.metrics score --run-id some-other-run --outputs <root>/.tmp/answers/20261115-mock-i4.jsonl
exit=2
ERROR: --run-id 'some-other-run' does not match the run_id '20261115-mock-i4' recorded in .tmp/answers/20261115-mock-i4.jsonl
```

本轮自查补上的一个诚实护栏：脚本化产物的 `model` 名字自己报 mock，但命令默认 `--label REAL` 会把
一次管道测试打成 REAL。现在 `score` 会把这件事说出来（不改变退出码，不静默修正用户显式声明的标签）：

```
$ python -m eval.metrics score --run-id 20261115-mock-i4
exit=0
[REAL] scoring answer run: eval/answers/20261115-mock-i4.jsonl (run_id=20261115-mock-i4, records=35)
（指标同上）
WARNING: --label REAL, but every record in this artifact names a scripted double (scripted-mock-generator). Pass --label MOCK: these numbers test the plumbing, they are not an experiment result.
```

### 8.4 意见 4：拒答标注的复核门（真实执行，预期失败）

```
$ python -m eval.metrics validate --require-reviewed
exit=2
ERROR: unanswerable item(s) without a human REVIEWED_BY attestation: N01, N02, N03, N04, N05, N06, N07, N08 - absent tokens are a necessary condition, not proof that the corpus cannot answer

$ python -m eval.metrics retrieval --summary-dir eval/results/summary/dev_try
exit=2
ERROR: --summary-dir needs --formal: development numbers stay in eval/results/raw/ (see eval/results/README.md)

$ python -m eval.metrics retrieval --summary-dir eval/results/summary/dev_try --formal
exit=2
ERROR: --formal refused, this run is not on frozen inputs yet:
  - data/raw/frozen_manifest.json is missing: the I1 corpus snapshot is not frozen yet
  - unanswerable item(s) without a REVIEWED_BY attestation: N01, N02, N03, N04, N05, N06, N07, N08
Development numbers belong in eval/results/raw/ via --out, not in summary/.
```

这三处拒绝都**不是实现缺陷**，而是当前仓库状态的如实反映：`frozen_manifest.json` 不存在（I1 未冻结），
8 条 `unanswerable` 标注**目前没有任何一个组员签名**。所以下面这些数字现在都只能标为 provisional：

- `correct_abstention_rate` / `false_abstention_rate`：依赖「这 8 题真的无法回答」这个尚未复核的前提。
- `answer_correctness`：本轮**仍无数字**（`pending human grading`，`grading_coverage 0/27`）。

### 8.5 本轮明确未执行 / 未做

- `--summary-dir` + `--formal` 的**成功**路径：未执行，因为两个前提（I1 冻结、拒答复核）都还没满足；
  代码路径由 `tests/test_eval_metrics.py` 用临时目录覆盖（五件套字段、MOCK 拒写）。
- `score` 对 **REAL 答案产物**的打分：未执行。需要 T5 用真 LLM 产出 `eval/answers/<run_id>.jsonl`。
- `paragraph` 策略命中率：仍未测定（本机无该 collection）。
- 人工 judge：仍未开始；本轮只交付了可从 I4 产物一键生成评分表的能力（§8.3）。
- 35 题在冻结语料上的重新校对：未做，等 T1 的 I1 快照。

### 8.6 MOCK 端到端（本轮重跑，与首轮的差别只在新增的 coverage 字段）

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
  correct_abstention_rate      1/1   1.0000
  false_abstention_rate        0/2   0.0000
  citation_structure_rate      2/2   1.0000
  answer_correctness           2/2   1.0000
  n_graded                   2
  n_gradable                 2
  grading_coverage             2/2   1.0000
  grade_counts               {'correct': 2, 'incorrect': 0, 'unsure': 0}
  hit@1                        1/2   0.5000
  hit@3                        2/2   1.0000

These numbers describe MOCK fixtures only. Do not put them in the report.
```

### 8.7 合并事故：首轮文档记录被覆盖（如实记录）

意见 1 处理冲突时，`RUNLOG.md`、`docs/DEV_LOG.md`、`docs/AI_USAGE.md`、`eval/README.md` 四个文件
两边都改过，本轮选了 `git checkout --theirs`（以 main 的新编排为准）。这个选择有一个副作用：
首轮写在这三个文件里的 T4 记录（旧 `RUNLOG.md` 第 11 节、`DEV_LOG.md` 的 T4 行、`AI_USAGE.md` 的
组员追加表）**全部丢失**。代码与测试不受影响（它们在 `eval/` 下，没冲突）；
`eval/README.md` 属于另一种情况：main 已经重写过该文件，本轮只在其新结构上补 I3/I4/I5 口径，
不算丢内容。

处理：第 7 节按新编号恢复首轮快照（输出原文未改），本轮与首轮的组员记录已补回
`docs/DEV_LOG.md` 与 `docs/AI_USAGE.md`。

给后面合并同一个仓库的人一句提示：解冲突时先 `git show <自己的提交>:<文件>` 看一眼自己写过什么，
`--theirs` 不是免费的。

## 9. T2 分块对比（2026-11-17，Cursor 编码 agent 执行，组员尚未重跑）

分支 `t2-chunking-experiment`。解释器是仓库 `.venv` 里的 Python 3.12.10。下面命令都在仓库根目录执行。
开发对比的逐题 JSON 在 gitignore 的 `eval/results/raw/chunking_comparison/comparison.json`，不入库。
`eval/results/summary/chunking_comparison/` 这次运行之后仍然不存在。

ONNX 模型首次下载约 79.3 MB 到本机缓存，进度条省略。下载完成后的比较报告原文如下。

```
$ python -m ruff check .
All checks passed!

$ python -m pytest -q
134 passed, 2 skipped

$ python -m eval.chunking_experiment --help
exit=0
（打印 usage；无模型、无 API key）

$ python -m eval.chunking_experiment --formal
exit=2
ERROR: --formal refused, this run is not on frozen inputs yet:
  - data/raw/frozen_manifest.json is missing: the I1 corpus snapshot is not frozen yet
  - unanswerable item(s) without a REVIEWED_BY attestation: N01, N02, N03, N04, N05, N06, N07, N08
Development numbers belong in eval/results/raw/ via --out, not in summary/.

$ python -m eval.chunking_experiment
exit=0
==============================================================================
[DEVELOPMENT] chunking comparison — 开发用，非正式实验结果
开发用 / development. Not a formal experiment result. Numbers describe CORPUS_V0 and the current qa_set.csv, which are not frozen formal inputs.
==============================================================================
corpus       : data/raw/manifest.json@b5bfc0d70e4a (frozen=False)
qa set       : eval/qa_set.csv@80b1d950f652
qa status    : development set on CORPUS_V0, not the frozen formal QA set
held constant: size=600 overlap=80 top_k=3 min_coverage=0.5 embedding=local:all-MiniLM-L6-v2

strategy      chunks    min    max     mean  hit@1          hit@3
fixed             28    147    600 554.8571  16/27 (0.5926) 23/27 (0.8519)
paragraph         33     89    683 480.3939  17/27 (0.6296) 23/27 (0.8519)

disagreements: 5
  A06 hit@3 gold=[1312, 1413] fixed=hit(rank=2), paragraph=miss(rank=None)
  A08 hit@1 gold=[2260, 2388] fixed=miss(rank=3), paragraph=hit(rank=1)
  A16 hit@1 gold=[1760, 1845] fixed=hit(rank=1), paragraph=miss(rank=2)
  A17 hit@1 gold=[2905, 3040] fixed=miss(rank=None), paragraph=hit(rank=1)
  A17 hit@3 gold=[2905, 3040] fixed=miss(rank=None), paragraph=hit(rank=1)

not applicable: retrieval-only comparison. hit@k is retrieval_hit_rate(); it is not answer correctness
wrote eval/results/raw/chunking_comparison/comparison.json
```

时间戳来自当时 JSON 的 `generated_at`：`2026-11-17T12:43:21+00:00`。
这次没有调用 LLM。`fixed` 的 16/27 与 23/27 与第 8 节里 T4 对同一开发集的检索数字一致。
这些数字是开发用结果，不能写进报告当正式实验。组员随后重跑，见第 9.1 节；那次覆盖了这份 JSON。

### 9.1 组员重跑（2026-11-17 20:50 GMT+8）

组员在已激活 `.venv` 的仓库根目录重跑了上面的验收命令。终端文件只保留了最后一条命令和退出码：

```
$ python -m eval.chunking_experiment
exit=0
```

这次写出的 `eval/results/raw/chunking_comparison/comparison.json` 的 `generated_at` 是
`2026-11-17T12:50:10+00:00`。汇总与 20:43 的 agent 运行相同：`fixed` 28 chunks，
hit@1 16/27 (0.5926)，hit@3 23/27 (0.8519)；`paragraph` 33 chunks，hit@1 17/27 (0.6296)，
hit@3 23/27 (0.8519)。`pytest`、`ruff` 和 `--help` 的屏幕输出没有留在终端记录里，这里不补写它们的通过行数。

## 10. T2 在冻结语料上重跑（2026-11-21，Cursor 编码 agent 执行，组员尚未重跑）

分支 `t2-chunking-frozen-corpus`，从已合并 PR #14 的 `origin/main` 拉开。解释器是仓库 `.venv` 里的 Python 3.12.10。命令都在仓库根目录执行。没有调用 LLM。

`--formal` 不再抱怨缺少 `frozen_manifest.json`。剩下的拒绝是 8 道 unanswerable 题没有 `REVIEWED_BY`。`eval/results/summary/chunking_comparison/` 这次之后仍然不存在。

```
$ python -m ruff check .
All checks passed!

$ python -m pytest -q
154 passed, 2 skipped

$ python -m eval.chunking_experiment --formal
exit=2
ERROR: --formal refused, this run is not on frozen inputs yet:
  - unanswerable item(s) without a REVIEWED_BY attestation: N01, N02, N03, N04, N05, N06, N07, N08
Development numbers belong in eval/results/raw/ via --out, not in summary/.

$ python -m eval.chunking_experiment
exit=0
==============================================================================
[DEVELOPMENT] chunking comparison — 开发用，非正式实验结果
开发用 / development. Not a formal experiment result. Corpus cs5481-k8s-v135-16docs-36fd3eedf33f@bddfe3601885 is frozen. QA status: development set on CORPUS_V0, not the frozen formal QA set.
==============================================================================
corpus       : cs5481-k8s-v135-16docs-36fd3eedf33f@bddfe3601885 (frozen=True)
qa set       : eval/qa_set.csv@c97051d8789c
qa status    : development set on CORPUS_V0, not the frozen formal QA set
held constant: size=600 overlap=80 top_k=3 min_coverage=0.5 embedding=local:all-MiniLM-L6-v2

strategy      chunks    min    max     mean  hit@1          hit@3
fixed            668    147    600 587.5793  16/27 (0.5926) 23/27 (0.8519)
paragraph        775     81    683 515.7768  17/27 (0.6296) 23/27 (0.8519)

disagreements: 5
  A06 hit@3 gold=[1312, 1413] fixed=hit(rank=2), paragraph=miss(rank=None)
  A08 hit@1 gold=[2260, 2388] fixed=miss(rank=3), paragraph=hit(rank=1)
  A16 hit@1 gold=[1760, 1845] fixed=hit(rank=1), paragraph=miss(rank=2)
  A17 hit@1 gold=[2905, 3040] fixed=miss(rank=None), paragraph=hit(rank=1)
  A17 hit@3 gold=[2905, 3040] fixed=miss(rank=None), paragraph=hit(rank=1)

not applicable: retrieval-only comparison. hit@k is retrieval_hit_rate(); it is not answer correctness
wrote eval/results/raw/chunking_comparison/comparison.json
```

当前 JSON 的 `generated_at` 是 `2026-11-21T01:24:36+00:00`。同一天 `2026-11-21T01:22:54+00:00` 先跑过一轮，汇总表相同，说明文字还把语料写成未冻结的 `CORPUS_V0`。改过开发说明后重跑，后一次覆盖了 JSON。逐题文件在 gitignore 的 `eval/results/raw/chunking_comparison/comparison.json`，不入库。


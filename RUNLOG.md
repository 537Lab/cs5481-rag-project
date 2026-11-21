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

---

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

---

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


## 11. 正式 Kubernetes 评测集的创建，与 PR #14 两处调整的复核（2026-11-20，T4 第二轮）

> 编号说明：本节原为第 9 节，与 main 上 T2 的第 9 节（分块对比）撞号；合并 `origin/main`
> （`848d7c6`）后编号改为第 10 节，内部各小节号与交叉引用一并从 9.x 改为 10.x。

PR #14（分支 `t1-corpus-kubernetes-v135`，head `50e9985`）留了两条给 T4 的话：
「#14 对 `eval/qa_set.csv` 和 `tests/test_eval_metrics.py` 有少量调整，请 T4 负责人确认」，
以及「目前 35 道 QA 仍是 Wikipedia 开发集，正式 Kubernetes QA 还需要 T4 创建并人工审核」。
本轮完成前者的 review、以及后者的**创建**；**人工审核一步没有做，也做不了** ——
`REVIEWED_BY` 是一个组员的名字，不能由 agent 代填（见 §11.7）。

分支 `t4-k8s-qa-set`，基点是**尚未合并**的 `pr/14`：正式题只能引用 I1 冻结快照里的那 12 篇
Kubernetes 文档，而这些文档此刻只在 #14 里。环境与前两轮相同（Windows + `.venv`，
Python 3.13.5，本地 ONNX embedding + 本地 Chroma，**零付费调用**）；下文命令一律写成仓库内
可移植形式，实际由 `.venv\Scripts\*.exe` 在同一台机器上执行。

### 11.1 PR #14 两处调整的复核结论

| #14 的调整 | 本轮查到的真实原因 | 结论 |
| --- | --- | --- |
| `N07` 的 `ABSENT_TOKENS` 由 `charge; fee` 改成 `charge for reusing; licensing fee` | 旧检验是裸子串匹配：`fee` 命中的是语料里的 **`feedback`**，并不能证明「收费」这件事在语料中出现过 | **接受**。但根因在检验器不在题目，§11.2 已改成词边界匹配；以后组员不必再为了躲开偶然去改写措辞 |
| 测试新增 `CORPUS_V0_DOC_IDS` 常量，并把「覆盖所有文档」改成「覆盖开发语料」 | 语料从 4 篇扩到 16 篇后，35 道 Wikipedia 开发题本来就不该覆盖 12 篇新文档 | **接受**。本轮进一步把「覆盖」变成两份文件各自的硬要求，并新增一条「两份合起来必须覆盖整个快照」的检查 |

#14 在本机 worktree（`pr/14` 全量检出，验证完即删除）的真实结果：

```
$ ruff check .
exit=0
All checks passed!

$ python -m eval.metrics validate            # 此时 qa_set.csv 仍是 35 题开发集
exit=0
[REAL] validated qa_set.csv: 35 items (27 answerable, 8 unanswerable)
documents consulted: 16; all 27 gold quotes resolve to a source character span

$ python -m pytest -o addopts="" -q
exit=1
FAILED tests/test_loaders.py::test_frozen_manifest_hashes_match_committed_documents
1 failed, 132 passed, 2 skipped in 10.60s
```

### 11.2 失败项定位：冻结语料的字节在 Windows 上被换行符改写（阻塞 #14，与 T4 代码无关）

`tests/test_loaders.py` 用 `read_bytes()` 比较磁盘字节与 `frozen_manifest.json` 记录的 SHA-256，
而 `scripts/fetch_corpus.py` 也是按字节记的哈希。逐篇比对（临时脚本，输出留在 gitignored 的
`.tmp/frozen_check.txt`）：

```
k8s_v135_stateless_deployment   disk=DIFF blob=OK disk_eol=CRLF blob_eol=LF bytes=6305/6081
16 docs: disk mismatch=16, git-blob mismatch=0
```

本机 `git config core.autocrlf` = `true`，仓库里**没有 `.gitattributes`**：git 对象是 LF（所以哈希对得上），
Windows 工作副本被检出成 CRLF（所以逐篇字节都对不上）。结论：#14 的这个测试在 Linux runner 上恒绿、
在 Windows 组员机器上恒红 —— CI 掩盖了它，不是它自己会修好。`ragkit/loaders.py` 用的是
`read_text()`（通用换行 → LF），所以 gold 引文匹配跨平台仍然稳定，**受影响的是字节哈希**：
除该测试外，`metrics.py` 里 `corpus_ref` / `qa_set_ref` 的 `_sha256()` 同样按字节算，跨平台取值不同。

本轮修法：新增 `.gitattributes`，规则只有 `* text=auto eol=lf` 加注释。先确认过
`git grep --cached` 在**任何已提交文本里都找不到 CR**，因此这条规则不会改动任何 blob，
`git add --renormalize data/raw` 之后 `git diff --cached HEAD` 对语料为空 —— 对组员看到的
仓库内容零副作用，只把「检出时不要改写换行」写进版本库。改完后本机：

```
disk-vs-manifest mismatches now: 0
$ python -m pytest -o addopts="" -q tests/test_loaders.py
exit=0
17 passed in 0.48s
```

同一个根因还会打到新正式集上，这里补一句：`load_qa()` 以 `newline=""` 开文件，所以 `QUOTE_ALL` 写入的
跨行 gold 引文会**原样保留文件里的换行字节**，而语料走 `read_text()` 永远是 `\n`。把本轮的
CSV 拷一份改成 CRLF（其余一字不动）实跑：

```
$ python -m eval.metrics validate --qa .tmp/qa_set_crlf.csv
ERROR: K02: evidence quote is not verbatim source text of doc_id='k8s_v135_components': '[etcd](/docs/concepts/architecture/#etcd)\r\n: Consistent and '
K03: evidence quote is not verbatim source text of doc_id='k8s_v135_components': '[kube-proxy](/docs/concepts/architecture/#kube-proxy) (optio'
exit=2
```

只有 K02/K03 报错，因为它们是全集唯二跨行的引文。这就是「平台相关的检出伪装成 gold 标准有错」，
所以除了 `.gitattributes`，本轮还钉了两个测试：`test_committed_qa_files_stay_lf_so_multi_line_gold_survives_checkout`（检查两份已提交 CSV 的字节）与
`test_a_crlf_copy_of_the_formal_set_stops_matching_the_corpus`（反向控制，证明上一条检查对应的失败真实存在）。

### 11.3 `eval/metrics.py` 的三处改造

1. **删掉 `QA_SET_STATUS` 常量**，改为 `qa_set_status(path, items)` **按内容推导**：文件名
   决定它是正式集还是开发集；`qa_corpus_binding()` 再决定这些 gold 是否只引用 I1 快照列出的
   `doc_id`；未签名的拒答题数量决定要不要追加一句「N refusal label(s) awaiting a human
   REVIEWED_BY」。`_config_snapshot`、`_qa_ref` 与 `validate` 都用它，因此报告里的状态由
   读到的文件说，不由命令行上的自述说。
2. **`token_occurs()` 取代裸子串检验**：词首要求词边界（`fee` 不再等于 `feedback`），词尾允许
   英语词形（`gpu` 命中 `gpus`、`hallucination` 命中 `hallucinations`），词组内的空格按 `\s+`
   匹配（换行不能藏住一次出现）。两个方向都有测试钉住，只往一边松的规则活不下去。
3. **两道门变严**：`assert_formal_inputs()` 新增「读的不是 I2 路径的正式集」与「gold 引用了快照
   之外的文档」两类拒绝，拒绝信息里给出待签名清单的路径；`cmd_validate` 多打三行：语料绑定、
   快照中尚无 answerable 题的文档、复核表位置。

### 11.4 两份 QA 文件

35 题保留为开发集，**内容未改一行**，只换了文件名（`git mv` 保留历史）；I2 唯一的
`eval/qa_set.csv` 路径现在放的是正式 Kubernetes 集，所以默认参数下 T2/T3/T5 拿到的就是正式集。
「内容未改一行」不是口径而是可验的：改名后的 blob 与改名前同一个对象（工作副本已按
`.gitattributes` 归一为 LF，归一不改动提交内容）：

```
$ git rev-parse HEAD:eval/qa_set.csv
6836eab750cab9aa2872340bb1d43a2e4497bb26
$ git rev-parse :eval/qa_set_dev_v0.csv
6836eab750cab9aa2872340bb1d43a2e4497bb26
```

```
$ git mv eval/qa_set.csv eval/qa_set_dev_v0.csv
$ python -m eval.metrics validate --qa eval/qa_set_dev_v0.csv
[REAL] validated qa_set_dev_v0.csv: 35 items (27 answerable, 8 unanswerable)
documents consulted: 16; all 27 gold quotes resolve to a source character span
QA set status: development QA set on the four CORPUS_V0 Wikipedia documents, not the
formal evaluation set; 8 refusal label(s) awaiting a human REVIEWED_BY
```

正式集 `eval/qa_set.csv`：**36 条 = 26 answerable（K01–K26）+ 10 unanswerable（KN01–KN10）**，
覆盖冻结快照全部 12 篇 Kubernetes 文档（每篇 2–3 题）。gold 引文不是手打的：按
`(doc_id, 行号[, 结束行])` 从快照原文切片，断言该片段在整篇文档中**恰好出现一次**且非空，
并把行号写进 `notes`（`gold spans snapshot lines X-Y`）供复核人定位；CSV 用 `QUOTE_ALL` + `\n`
写出，因此一条引文可以跨多行（K02 取 `components` 第 17–18 行，因为 etcd 的名字与定义分在两行）。
10 条拒答题分 OUT-OF-DOMAIN（价格、默认口令、历史）与 NEAR-MISS（语料谈到同一对象但没问的性质），
`notes` 里如实写出复核人应当怀疑的线索，例如 KN03 说明 `services.md` 链接到 `.go` 源文件——
这暗示了语言却没有陈述它，算不算答案要人判。

本轮自查改掉的四处（都是先写错、机检发现、再改）：

- K02/K03 的引文以 `": "` 开头，不含主语（名字在上一行）→ 改成取跨行的 17–18、36–37；
- K26 的问题里「that tutorial」指代不明 → 直接点名 stateless application deployment tutorial；
- KN06 的理由写成了「Liveness/Liveness probe sections」→ 改为 Liveness/Readiness/Startup 三节；
- KN03 的理由没披露 `.go` 链接这一条存在线索 → 补进 `notes`，不把它当成「语料无法回答」藏起来。

一开始想用的 `design document`、`implemented in`、`mysql`、`cannot exceed`、`borg` 几个 token
全部被机检拦下（它们在快照里真的出现），已换词；最终 23 个 token 全部确认不存在。

### 11.5 验收命令（真实执行）

```
$ ruff check .
exit=0
All checks passed!

$ python -m eval.metrics validate
exit=0
[REAL] validated qa_set.csv: 36 items (26 answerable, 10 unanswerable)
documents consulted: 16; all 26 gold quotes resolve to a source character span
  k8s_v135_components          3 answerable items
  k8s_v135_configmaps          2 answerable items
  ...（共 12 篇，每篇 2–3 条）
  k8s_v135_stateless_deployment   2 answerable items
gold span sample (strategy-independent):
  K01 k8s_v135_components chars 175-253
  K02 k8s_v135_components chars 504-620
  K03 k8s_v135_components chars 1274-1396
unanswerable absence checks: 23 tokens confirmed absent from the corpus as whole words - a NECESSARY condition only, the absence
of a word does not prove the corpus cannot answer the question
human review of unanswerable labels: 0/10 carry REVIEWED_BY (pending: KN01, KN02, KN03, KN04, KN05, KN06, KN07, KN08, KN09, KN10)
  checklist for the reviewers: eval/review/formal_qa_review.md
corpus binding: 12 doc(s) cited, verified against the frozen snapshot: True
frozen documents with no answerable item (4/16): bm25_wikipedia, rag_wikipedia, vector_db_wikipedia, word_embedding_wikipedia
corpus checked against: data/raw/manifest.json@3e3e4e4217df; frozen snapshot (I1) present
QA set status: formal Kubernetes QA set (interface I2), gold quotes verbatim in the frozen corpus snapshot; 10 refusal label(s) awaiting a human REVIEWED_BY

$ python -m eval.metrics validate --require-reviewed
exit=2
ERROR: unanswerable item(s) without a human REVIEWED_BY attestation: KN01, KN02, KN03, KN04, KN05,
KN06, KN07, KN08, KN09, KN10 - absent tokens are a necessary condition, not proof that the corpus cannot answer

$ python -m pytest -o addopts="" -q
exit=0
148 passed, 2 skipped in 5.28s
```

测试数从 #14 基线的 132 passed / 1 failed / 2 skipped 到 **148 passed / 0 failed / 2 skipped**（+15）：
新增用例 10 个（两份集合计覆盖、词边界双向、换行字节与 CRLF 反向控制、复核表一致性、绑定入快照与越界、
开发集/临时文件的 formal 拒绝），GOLD 区 5 个用例改成 `committed_qa` 参数化后各跑两份；`tests/test_eval_metrics.py`
从 67 例到 82 例。本轮未删除任何首轮或 #14 的用例。`-o addopts=""` 与前两轮同因：
`pyproject.toml` 的 `addopts` 已含 `-q`，重复传无副作用，保留是为了跟 RUNLOG 历史记录可对比。
2 个 skipped 仍是 `tests/test_e2e_real.py`（需 `RUN_REAL_E2E=1`，其中一个还需 `OPENAI_API_KEY`），本轮未开启。

### 11.6 REAL 检索命中率（正式集与开发集，同一个索引）

真实入库 16 篇 → 668 chunks（`fixed` size=600 overlap=80，本地 ONNX MiniLM dim=384，`top_k=3`，
`min_coverage=0.5`），未动 `config.toml`，零付费调用：

```
$ python -m ragkit.cli ingest
OK: 16 documents -> 668 chunks stored in collection 'chunks_fixed'

$ python -m eval.metrics retrieval --hits 1,3 --min-coverage 0.5 --label REAL --out eval/results/raw/retrieval_k8s_formal.json
[REAL] retrieval metrics
  min_coverage               0.5
  n_items                    36
  n_answerable               26
  n_unanswerable             10
  hit@1                        8/26  0.3077
  hit@3                       18/26  0.6923

$ python -m eval.metrics retrieval --qa eval/qa_set_dev_v0.csv --hits 1,3 --min-coverage 0.5 --label REAL --out eval/results/raw/retrieval_wikipedia_dev.json
[REAL] retrieval metrics
  n_items                    35
  n_answerable               27
  hit@1                       16/27  0.5926
  hit@3                       23/27  0.8519
```

两组数字来处同一个索引，可直接对比：**正式集上的 hit@1 只有开发集的一半多一点（0.3077 vs 0.5926），
hit@3 从 0.8519 降到 0.6923**。这不是「代码坏了」的巧合，而是领域真的变了：Kubernetes 参考页里的命令、
表格与字段名和 Wikipedia 散文的表达方式不同，同一个 fixed+MiniLM 组合在新领域上明显更差。报告里
**不要把这两个率平均成「我们的命中率」**（`judge_protocol.md` §5 已新增一条领域差异的说明）。

一个值得记下来的观察：开发集的 16/27 与 23/27 与第 7.2 / 8.1 节在**只有那 4 篇 Wikipedia 文档**时
跑出的两个数字完全一致。分母相同（27 道 answerable），索引里的 chunk 从 28 块涨到 668 块，
命中题集却一题未变。本轮**没能在机检里解释这个现象**（它可能只是那 27 道题足够显著），
只把它当作“开发集行为未被本轮修改破坏”的旁证据，不当做结论写。

另：这两个文件只落在 gitignored 的 `eval/results/raw/`，没进 `summary/`：拒答标注未复核，
`--formal` 会被拒，这是当前应有的状态。

### 11.7 hit@3 未命中的 8 题归因（切片问题还是排序问题）

因为命中率明显偏低，本轮逐条检查了未命中题的 gold 区间是否**可能被任何 chunk 命中**：用与入库相同的
`fixed 600/80` 本地重切，取该文档内覆盖该区间比例最高的 chunk：

```
K03 span 1274-1396 best_coverage=1.00 chunks_touching=1 hit@3=False
K06 span 1249-1342 best_coverage=1.00 chunks_touching=1 hit@3=False
K12 span 8626-8727 best_coverage=1.00 chunks_touching=2 hit@3=False
K13 span 12462-12543 best_coverage=1.00 chunks_touching=1 hit@3=False
K18 span 15308-15401 best_coverage=1.00 chunks_touching=1 hit@3=False
K19 span 23886-23971 best_coverage=1.00 chunks_touching=1 hit@3=False
K21 span 13534-13614 best_coverage=1.00 chunks_touching=1 hit@3=False
K25 span 0-79       best_coverage=1.00 chunks_touching=1 hit@3=False
items whose gold span no single 600-char chunk covers by 0.5: []
```

结论：26 道正式题的 gold 区间**全部被某个 chunk 完整覆盖**（best_coverage=1.00），未命中不是跨边界
或 `min_coverage=0.5` 阈值造成的，而是**相关 chunk 没进 top-3**。这应该归入 T3（检索层）的失败样本，
T2 的 chunking 对比可以拿「不存在因切片而不可命中的题」作为前提检查。未命中题中有一个模式值得注意：
K25 的 gold 是教程首句（`stateless_deployment` 第 1 行），top-3 全是 `pods`/`probes` 的首块 —— 问题里
的“tutorial”在索引中没有任何可区分的信号，这是领域文档本身的特点，不是引文写错了。

### 11.8 本轮明确未执行 / 未做

- **人工审核（#14 里要的第二件事）没做，也不是本轮能做的**：`eval/qa_set.csv` 的 10 条拒答标注全部
  没有 `REVIEWED_BY`。已备好待签名的工作单 `eval/review/formal_qa_review.md`（逐题列出要重读的页面、
  要搜的词、需要时改动哪一行）与第 3 节签名区。组员签完后才能重跑 `--require-reviewed` / `--formal`。
- `--summary-dir` + `--formal` 的**成功路径**仍未执行：两个门现在多了一个「必须是正式集文件」，但
  拒答标注未复核这一条就足以拦住它；代码路径由测试用临时目录覆盖。
- `score` 对 REAL 答案产物的打分：仍未执行（需要 T5 的真 `eval/answers/<run_id>.jsonl`）；
  `answer_correctness` 依旧无数字（`pending human grading`）。
- `paragraph` 策略的命中率：本轮未测（本机 collection 只有 `chunks_fixed`）；第 11.6 节两个率都是
  `fixed 600/80`，不能代表全项目。
- 36 道题的人工逐题阅读：本轮只做了机检（逐字、唯一性、跨行覆盖、领域内部、token 不存在）与写作
  自查（§11.4）。机检只能证明引文存在，不能证明题目清楚。

### 11.9 本 PR 的云端 CI：未执行（账号级 Actions 计费），不是代码失败

PR 建好后 `ci / check (pull_request)` 在 2 秒内红。run 页 Annotation 原文：

```
The job was not started because recent account payments have failed or your spending limit
needs to be increased. Please check the 'Billing & plans' section in your settings
```

即 job 从未被调度，与 diff 内容无关。同一个错误出现在 **T1 的 PR #14 的 run**（页面标题
`T1: freeze Kubernetes v1.35 formal corpus`）上，所以这是账号/组织级、影响全组所有 PR，
不是本分支特有。`RUNLOG.md` 第 3 节记录的 `43423374183`（2026-11-13）当时是 `success`，
说明问题发生在 11 月中旬之后。

红之前先把内容层的可能排掉。用干净检出复现 CI 的两条命令：

```
$ git worktree add --detach .tmp/wt-ci HEAD     # 独立检出：按 .gitattributes 全 LF，无本地未跟踪文件
$ cd .tmp/wt-ci
$ ruff check .
All checks passed!
$ python -m pytest -q
exit=0
```

该 worktree 里 `test_committed_qa_files_stay_lf_so_multi_line_gold_survives_checkout` 通过，
反证检出确实是 LF（同一个用例在我归一化之前的主工作副本上因 CRLF 红过，见 §11.2）。
其余三条排除依据：`git ls-files --others --exclude-standard` 为空（没有测试依赖「只在本机存在」的文件）；
`git diff origin/main HEAD -- .github/workflows/ requirements-dev.txt pyproject.toml` 为空（CI 定义与依赖未变）；
main 是本分支祖先（`4f865c1`）且 `git merge-tree --write-tree origin/main HEAD` 无冲突（CI 检出的树 = HEAD）。

处置：额度/付款恢复前**不要点 Re-run jobs**（会再次 not started）。`docs/DEV_LOG.md` 与
`docs/AI_USAGE.md` 里「待本 PR 的 `ci / check`」那一格已改成如实描述，本地证据以上面这段代替。
「CI 绿才能合并」这条规则现在对全组都不可执行，需要组员另行确认临时判据 —— 我没有替大家改
`CONTRIBUTING.md`。

**后续（2026-11-21）**：本节记录的那个状态已过去 —— 本 PR 页面现在显示 **1 successful check**，
账号级计费故障已恢复。上一段保留作为当时的事实记录，不回头修改；当前 CI 口径见 §11.10。

### 11.10 合并 `origin/main`（`848d7c6`）：两个「第 9 节」撞号，以及合并后的实跑（2026-11-21）

main 在这期间合并了 T1 的 #13（`0ea607d`，loader 加固）与 T2 的 #10（`848d7c6`，分块对比）。
`git merge origin/main` 后：**代码层全部自动合并**（`ragkit/loaders.py`、`ragkit/chunking.py`、
`eval/chunking_experiment.py`、`tests/test_chunking.py`、`tests/test_loaders.py`），冲突只在三个
追加式文档：

| 文件 | 冲突原因 | 处理 |
| --- | --- | --- |
| `RUNLOG.md` | 本分支的 T4 第二轮写了「第 9 节」，与 main 上 T2 的第 9 节**编号碰撞** | 保留 T2 的第 9 节原文不动；T4 一节整体改编号为**第 10 节**，内部小节号与交叉引用一并从 9.x 改为 10.x |
| `docs/DEV_LOG.md` | 两边都在记录表尾部追加行 | 保留 T2 三行；T4 的 11-15 行用本分支的更新版（main 上那行还写着「待跑 CI / 待 review」，而它实际已以 `4f865c1` 合入）；新增本轮合并说明行 |
| `docs/AI_USAGE.md` | 两边都重写了尾部「不要照抄示例句」那段 | 合为一段，并按当前事实更新（T2 的行已在 main；T4 已四轮） |

指向修正：`docs/DEV_LOG.md` 与 `docs/AI_USAGE.md` 里属于 T4 的引用改为第 10 节；**T2 自己的引用
（`docs/CHUNKING_EXPERIMENT.md`、两行 T2 记录里的「第 9 节 / 9.1 节」）一律不改**，它们指的仍是
T2 自己在 main 上的第 9 节。没有改动 T1/T2 的实现代码，也没有为迁就他们而改指标行为。

合并后实跑（仓库根目录、`.venv`）：

```
$ ruff check .
All checks passed!

$ python -m pytest -o addopts="" -q
168 passed, 2 skipped in 5.43s        # 合并前 148 passed / 2 skipped

$ python -m eval.metrics validate
exit=0                                # 正式集：36 条，绑定 12 篇，frozen snapshot: True
$ python -m eval.metrics validate --qa eval/qa_set_dev_v0.csv
exit=0                                # 开发集：35 条，4 篇 CORPUS_V0
$ python -m eval.metrics validate --require-reviewed
exit=2                                # 10 条 REVIEWED_BY 未签，与 §11.8 一致
```

用例数增加来自 main：`tests/test_chunking.py` 10 → 23 个 `def test_`、`tests/test_loaders.py`
15 → 21（parametrize 展开后采集总数 150 → 170）；`tests/test_eval_metrics.py` 未变（82 例）。
没人为调整过计数或跳过条件。

跨任务接口的一手证据 —— T2 的正式门在本分支上少了一条拒绝理由：

```
$ python -m eval.chunking_experiment --formal
ERROR: --formal refused, this run is not on frozen inputs yet:
  - unanswerable item(s) without a REVIEWED_BY attestation: KN01, KN02, KN03, KN04, KN05, KN06, KN07, KN08, KN09, KN10
exit=2
```

第 9 节里那条 `data/raw/frozen_manifest.json is missing` 已消失，`eval/qa_set.csv` 路径检查也通过：
说明 I1 快照与 I2 正式集两个前提在 #14 + 本分支合入后就绪，剩下的唯一阻塞是人工签名。
给 T2 的一句话：`--formal` 不需要改代码，等 `REVIEWED_BY` 签完就能跑；T2 的 `DEVELOPMENT_NOTE`
里「the current qa_set.csv … not frozen formal inputs」这句已与本仓库现状不符（只报告，本轮没改 T2 的文件）。

### 11.11 PR 编号与组员账号：一条被浏览器现场证伪的推断（2026-11-21）

本轮试图用浏览器把新的 PR 描述贴上去，会话未登录，按预设的停止条件退出（没有输入任何凭据）。
但这次探测从 PR 列表页拿到了三条仓库内无法得到的事实，其中**推翻了我昨天写进 `docs/DEV_LOG.md` 的一句话**：

| 项 | 之前的说法（仅基于 git 取证） | 现在的实际情况 |
| --- | --- | --- |
| 本 PR 编号 | 不敢写，正文里用「`t4-k8s-qa-set` 那个 PR」占位 | **#15**（`wangsaorui wants to merge 8 commits into main from t4-k8s-qa-set`） |
| T5 | 「远端已有分支 `t5-generation-validation`，但仓库内看不到对应 PR」 | **已开 PR #16**（作者 `ziqilin669`，标题含 citation coverage / I4 batch export / offline demo） |
| 组员账号 | T1 `yafeili39-arch`、T2 `null1024-ws`、T3 `usagi`（按 commit author） | PR 页还出现了 `ldk13856478627-cell`（#14 作者）与 `ziqilin669`；**账号 ↔ 任务 ↔ 真人姓名仍未核实** |

`docs/DEV_LOG.md` 的三处对应描述已改。这里把错与改都记下来，而不只记结论：**仅凭 `git for-each-ref`
看到分支就推断「没人认领」是不成立的**，分支可以存在而 PR 后开。以后遇到同类推断，本仓库没有
`gh` CLI 就没有权威数据源，只能写「待核实」而不能写「没有」。

顺带一条对 reviewer 有用的：#15 页面上显示的是 **8 commits / +9,748 −250 / 29 files**，其中包含
尚未合并的 #14 全部内容（base = `main` 的必然结果，不是本 PR 多写了代码）。

### 11.12 第二次合并 `origin/main`（`0ee7d5e`）+ 把拒答题核对转交组员（2026-11-21）

这一轮做了三件不同的事，逐件登记，因为它们的可信度来源不一样。

**（1）解冲突：只做追加，不碰别人的行。** `main` 在 `6bc7600` 之后又合入了 T5 的 #16（`0ee7d5e`），
本分支与 base 再次只剩一个冲突文件 `docs/AI_USAGE.md`。这次 git 报的冲突标记在**第 1 / 102 / 201 行**，
即整份文件互相对不齐，尾部拼接的解法不适用，所以先把三个 stage 导出再逐行对齐：

| stage | 行数 | 相对共同祖先的变化 |
| --- | --- | --- |
| base（`:1:`） | 93 | — |
| ours（`:2:`，本分支） | 100 | 改一处小节标题、追加两行 T4 记录、把末尾段落由 2 行改写为 6 行 |
| theirs（`:3:`，main） | 98 | **只在文件末尾追加 `## T5 additional records` 一节（2 行记录）** |

两侧唯一的重叠就在文件末尾，因此正确解是「本分支全文 + main 追加的那一节原样附后」。
解完用脚本断言三件事，而不是目测：追加块与 `origin/main` 的版本**逐字节相同**（4 行，`sha256` 前缀 `5609f13c`）、
本分支的行**零丢失**、`git diff --cached HEAD -- docs/AI_USAGE.md` 只有 5 行 `+`、无 `-`。
合并后 `git diff --cached --name-only HEAD` 只列出 T5 的 9 个文件（`demo/`、`docs/ANSWER_QUALITY.md`、
`ragkit/cli.py`、`ragkit/generation.py`、`tests/test_generation.py` 等），`eval/`、`tests/test_eval_metrics.py`、
`tests/test_loaders.py`、`data/raw/`、`.gitattributes`、`RUNLOG.md` 均未被这次合并改动。

**（2）合并后实跑（本机，全部真实退出码）：**

| 命令 | 结果 |
| --- | --- |
| `ruff check .` | All checks passed（`exit=0`） |
| `python -m pytest -o addopts="" -q` | **186 passed / 2 skipped in 6.47s**（上轮 168；+18 例来自 #16 的 `tests/test_generation.py`） |
| `python -m eval.metrics validate` | `exit=0`；23 个 `ABSENT_TOKENS` 均以词边界确认不存在；`0/10 carry REVIEWED_BY`；corpus binding verified `True`；4/16 篇冻结文档无 answerable 题 |
| `python -m eval.metrics validate --qa eval/qa_set_dev_v0.csv` | `exit=0`（开发集 0/8 签名） |
| `python -m eval.metrics validate --require-reviewed` | **`exit=2`**（KN01–KN10 全部列名为未签名） |
| `python -m eval.chunking_experiment --formal` | **`exit=2`**，拒绝理由只剩未签名一条 |

推送 `f4cc5fa` 后的**云端**结果（从 PR / Checks 页读到，本机无 `gh` CLI）：`ci / check` **succeeded in 28s**，
run `44877582328` / job `136765583598`，页面上可见的步骤均为 `success`（含 Static check (ruff)、Tests (offline)、
Verify no secret was committed），唯一 annotation 仍只是 "Node.js 20 is deprecated"；Merge box 已从
`This branch has conflicts that must be resolved` 变为 `All checks have passed` + `No conflicts with base branch` +
`Merging can be performed automatically.`，PR 现为 7 commits。另外两条当时读到但**不能当成好消息**的事实：
`537Lab` 与 `ziqilin669` 的两条 review 链接仍都指向 `93bfb03`（即页面上的「1 approving review」不覆盖当前代码），
且截至本轮结束 `ziqilin669` **尚未回复**那条判定表。本轮登记自身会产生新 head，它的 CI 结论只记在 PR 页面上，
不在此自指追记，否则这个循环不会结束。

**（3）把人工核对转交组员，并核对 `537Lab` 那条 non-approving review。**
`537Lab` 在 `93bfb03` 上留的是 **COMMENTED**（不是 approve），正文明确写「not a human attestation」、
「I cannot fill `REVIEWED_BY`」。它可执行的请求有四项：逐题记录拒答评审、专门让人裁决 KN03、消歧义、
在 #13/#14 并入后刷新分支。逐条对仓库核验的结果：

| review 的断言 | 我这轮的独立复核结果 |
| --- | --- |
| 「26 条 gold quote 在其声明文档内逐字命中**恰好一次**」 | **成立且可复现**：26/26 篇内唯一，且**全库范围也只命中一次**（0 条重复、0 条找不到）——这条比 `validate` 本身检查的更强，已单独跑脚本验证 |
| 「10 条拒答全无 `REVIEWED_BY`，token 缺失只是必要条件」 | 成立，0/10 |
| 「KN03 需人裁决：`services` 页链到 `.go` 源码，可能间接暗示实现语言」 | 该疑问针对 `93bfb03`；`b2263d9` 已查明那个链接指向 `pkg/kubelet/envvars/envvars.go`（kubelet 环境变量），与 kube-proxy 无关。我这轮的同义词扫描独立复现：`.go` 在快照内共 4 处命中（`services:859`、`probes:205`、`kubectl_quick_reference:436/437`），无一处说明 kube-proxy 用什么写。**裁决权仍在组员** |
| 「刷新分支以便不含 #13/#14 的重复改动」 | 已通过 `ac173a2` 与本节这次合并两次完成；#14 已入 main，重复部分随之消失 |
| 「CI 通过不等于人工评审门禁关闭」 | 成立：本机 `--require-reviewed` 与 `--formal` 均 `exit=2` |

转交动作：以组员已登录的浏览器会话，在 PR #15 发出 `issuecomment-7058643165`（14 201 字符），内含
KN01–KN10 的空白判定表（只允许填「同意 / 不同意 / 该改」）与每题的同义词扫描摘录，并要求结论由
`ziqilin669` 本人以其账号给出。**本轮没有任何一条 `REVIEWED_BY` 被写入**——门禁仍关闭，这一点不能因为
「已发出请求」而改口径。另外那条 approve 针对的 commit 是 `93bfb03`，落后当前 head 五个提交。

**留给 T5 的一处排版（我没改，因为不是我写的行）**：main 上 `## T5 additional records` 的两行表格缺少
`| --- |` 表头分隔行，GitHub 不会把它渲染成表格，只会显示成竖线原文。属于 #16 的内容，按所有权应由 T5 自己修。

### 11.13 人工复核由 `ziqilin669` 本人落笔，正式门禁第一次打开（2026-11-21）

本节写于 §11.12 之后。期间**有三个不是我推的提交落进本分支**，远端 head 从 `11470fb` 变成 `d39d658`；
本地在它们存在期间一直停在 `11470fb`，所以 §11.12 那句「`REVIEWED_BY` 仍 0/10」在写完后就已过期（见 §11.14）。

| 提交 | 账号 / 时间（GMT+8） | 内容 | 我的核验 |
| --- | --- | --- | --- |
| `da3c82d` | `ziqilin669` 18:52:01，GitHub 网页 "Add files via upload" | `eval/qa_set.csv` 的 10 行 `notes` 末尾追加 `REVIEWED_BY: ziqilin669 (2026-11-21)` | 逐行 csv 比对：36 行不变、`qid` 顺序不变、**除 `notes` 外没有任何一列被改**；去掉该 token 后与 `b2263d9` 的措辞一致，即 KN03 那处事实纠正没有被回退 |
| `5eaf1e2` | `ziqilin669` 18:53:34，同上 | `eval/review/formal_qa_review.md` 签名区 4 行 | 行数 86 → 87，签名原文见下 |
| `d39d658` | `ldk13856478627-cell` 20:25:32 | 把门禁测试从「关闭」翻成「打开」：`tests/test_eval_metrics.py` −21/+14、`tests/test_chunking.py`（**T2 拥有**）−11/+12、`formal_qa_review.md` −4/+5 | 实跑 + 逐条 diff，见下 |

**这一步的性质要说清楚**：签名是 `ziqilin669` **本人用自己的账号把改好的文件传上 GitHub**，姓名是他自己的，
不是任何人代填 —— 即我在 `issuecomment-7058643165` 里给出的两条合法路径中的 A 条（由本人直接改 csv）。
`eval/review/formal_qa_review.md` 的 sign-off 现在写的是
`Reviewer name(s) and date: ziqilin669, 2026-11-21`、`Items changed after review: none; KN07 kept as written`、
`Remaining disagreements (adjudicated by a third member): none`，并把结尾那句「questions have not been read by a
second human yet, so every row above is pending」改成「no row remains pending」。

在 `d39d658` 的 detached worktree 上实跑（`.venv`，Python 3.13.5，用完 `worktree remove --force`，主工作树未动）：

| 命令 | 结果 |
| --- | --- |
| `ruff check .` | All checks passed（`exit=0`） |
| `python -m pytest -o addopts="" -q` | **186 passed / 2 skipped**（与 `11470fb` 完全同数：翻转是 1:1 替换用例，没有净减少覆盖） |
| `python -m eval.metrics validate` | `exit=0`；`human review of unanswerable labels: 10/10 carry REVIEWED_BY`；23 个 `ABSENT_TOKENS` 仍按词边界判定不存在 |
| `python -m eval.metrics validate --require-reviewed` | **`exit=0`** —— 本任务从头到尾 `exit=2` 的那道门，第一次真实打开 |

两处我怀疑过、**但实测不成立**的问题，记为已排除而不是缺陷：

1. `REVIEWED_BY` 被追加在 `ABSENT_TOKENS: helm; chart;` 这条分号列表的尾部，我怕它被当成第三个「缺失 token」。
   实际解析结果 `absent_tokens=('helm','chart')`、`reviewed_by='ziqilin669 (2026-11-21)'`，未被污染；
   起作用的是 `test_review_markers_parse_in_whatever_order_they_are_written` 覆盖的那个性质。
2. 怕翻转顺手删掉负向对照。`test_require_reviewed_fails_until_a_human_signs_off` 仍在，仍用合成行证明
   缺 token 时会 `raise QASetError`。

一处**真实的覆盖面缩减，但文件不归我，交由 T2 判断**：`tests/test_chunking.py` 的
`test_formal_refuses_before_creating_summary` 被改写成 `test_formal_creates_summary_after_review_gate_opens`，
该文件内 `raises(QASetError)` 由 6 → 5，断言字面量 `"not on frozen inputs"` 由 1 → 0，也就是「未签名时
`--formal` 必须拒绝」这条**经由分块实验入口**的断言消失了。逻辑上它是门禁打开的必然结果（已签名的提交集
不再会拒绝，硬留这条测试反而要造假数据），机制层覆盖仍留在 `test_eval_metrics.py`。但这次改动是
**T1 的账号、在 T4 的分支上、改 T2 拥有的测试文件**，三方里没有一个文件所有者，是否认可这种翻转应由 T2 自己说。

### 11.14 我上一轮的登记有一条已经过期，以及本轮确认下来的合并口径

**自我更正（不改动 §11.12 原文，只在此追加）**：§11.12 结尾的「本轮没有任何一条 `REVIEWED_BY` 被写入」，
以及我在 PR #15 描述与 `issuecomment-7062218447` 里写的「`REVIEWED_BY` 出现 0 次」「`--require-reviewed`
必然 `exit=2`」，**在发出的那一刻就已经不成立**：`da3c82d` 的签名上传是 18:52 GMT+8（10:52 UTC），
我的评论发在 11:56 UTC、描述更新在 12:24 UTC。当时那些话对本分支 `11470fb` 是对的，对 PR 的真实 head 是错的。

根因不是判断失误，是取证口径漏了一项：这轮所有命令都比的是 `origin/main` 与**本地** `HEAD`，
唯独没有比 `origin/t4-k8s-qa-set`。别人可以往我的分支推提交（此前 `b2263d9`、`ac173a2` 已发生过两次），
本地 head 因此会静默落后，而我引用的数字全是「本地 head 上的数字」。修法是把「fetch 之后先比对远端分支 head，
再引用任何计数」固定成前置步骤；本轮已按此执行（`git merge --ff-only origin/t4-k8s-qa-set` 从 `11470fb` 进到 `d39d658`，
没有为了追赶而制造我自己的提交）。

**合并口径（经负责人确认，写在这里供解冲突时照做）**：下一次解 `docs/AI_USAGE.md` 时
**只追加本分支自己的行，不动 main 那份重复块**。当前 main（`30e6e98`）上该缺陷依旧未修 ——
一级标题在第 1 与第 96 行、共 195 行、`0ee7d5e → main` 的 numstat 仍是 `+195 / −98`（纯追加应为 `−0`）。
也就是说本分支会暂时继承一份已知坏文档，但我不在自己的 PR 里删别人写的 98 行。

**新的撞号事实**：main 的 `## 10` 现在是「T2 在冻结语料上重跑」，本分支的 `## 10` 是「T4 正式 Kubernetes 评测集」，
同号两份内容。合并时按 §11.10 的同一做法：**T4 这一节整体改号为 `## 11`**（含 `### 11.x` 小节号与全部 `§11.x`
自引用同步），T2 的第 10 节原文一字不动。`RUNLOG.md` 与 `docs/DEV_LOG.md` 的 main 侧仍是纯追加
（`0ee7d5e → main` 各 `+47 / −0`、`+1 / −0`），可以安全解；与我的行零重叠这个判据本轮重新测过，仍成立。

### 11.15 第三次合并 `origin/main`（`30e6e98`）：6 处文档冲突、本节改号为第 11 节（2026-11-21）

上面 §11.14 写的合并口径在这一轮落地。前置事实（`git fetch` 后实测，不是回忆）：merge-base 仍是
`0ee7d5e`，main 已到 `30e6e98`（合入 #18、#20），main 侧 14 个提交不在本分支，本分支 12 个提交不在 main；
`git merge-tree --write-tree HEAD origin/main` **`exit=1`**，冲突**只在三份追加式审计文档**：
`RUNLOG.md` 1 处、`docs/DEV_LOG.md` 1 处、`docs/AI_USAGE.md` 4 处，共 6 处；代码与测试 0 处冲突，
`ragkit/cli.py`、`ragkit/generation.py`、`tests/test_generation.py`、`demo/README.md`、
`docs/ANSWER_QUALITY.md`、`docs/CHUNKING_EXPERIMENT.md`、`eval/chunking_experiment.py`、
`tests/test_chunking.py` 全部由 git 自动合并。

**（1）`RUNLOG.md`：main 的那一节在前，本分支的那一节整体改号。**
main 上 `## 10. T2 在冻结语料上重跑` 共 46 行，**逐字放在本节之前，一个字未改**；本分支原来那份
`## 10. 正式 Kubernetes 评测集…`（497 行）整体改号为 `## 11`，`### 10.1`–`### 10.14` 改为
`### 11.1`–`### 11.14`，节内指向本节自己的指针（`§10.x`、`第 10.x 节`、`` `RUNLOG.md` 第 10 节``）
同步改为 11.x。**三句叙述上一次（9→10）改号的原句故意保留**：「后编号改为第 10 节」、
「T4 一节整体改编号为**第 10 节**」、「属于 T4 的引用改为第 10 节」——它们记录的是当时发生的事件，
改掉就是篡改历史；读者现在的定位信息由本节承担。

**（2）`docs/DEV_LOG.md`：只插入别人的一行，不重排别人的行。**
main 侧新增的是 `| 2026-11-21 09:24 GMT+8 | T2 在 PR #14 冻结语料上重跑 |` 这一行（`0ee7d5e → main`
为 `+1 / −0`，纯追加），逐字插在本分支四行 T4 记录之前。改号脚本只作用于本分支的行 ——
**T2 写的指针若指向 T2 自己的第 10 节，我没有权限替它改成第 11 节**。

**（3）`docs/AI_USAGE.md`：按 §11.14 的口径，继承坏文档，只追加自己的行。**
main 那 195 行**逐字作为文件前缀保留**，包括那份已知缺陷：一级标题同时出现在第 1 与第 96 行
（`0ee7d5e → main` 仍是 `+195 / −98`，纯追加应为 `−0`）。本分支自己的 4 行 T4 登记与更正后的现状段落
追加到新开的 `## T4 additional records` 一节，带 `| --- |` 分隔行，GitHub 能正常渲染。
上一轮那种「本分支全文保留 + 把 main 的新块附到末尾」的解法这一轮不再适用：main 侧那 98 行改动
与本分支的 98 行改动**交集就是 98 行**（双方都把带 CR 的 base 整份归一并各自重写），没有任何一段能
干净地插在对方中间。main 的标题句「除 T4 外组员尚未开始」与本分支的标题句互相矛盾，本轮**取 main 的
原文不改**，由 T4 一节里的一段说明取代其口径 —— 别人的行留在原地，错的判断由追加的行来更正。

**（4）解完之后的机器校验**（脚本 `.tmp/verify_pass1.py`，**37 项断言全通过**；与仓库一样是一次性取证，不入库）：
main 的 T2 段逐字连续存在；main 的 195 行是 `docs/AI_USAGE.md` 的逐字前缀；本分支 4 行 T4 记录与现状
段落都在；`### 10.x` 残留 0 处、`§10.` 指针残留 0 处；剩下的「第 10 节」全部命中上面列出的三句叙述与
「T2 的第 10 节原文一字不动」；无冲突标记；三份文件全 LF 且以换行结尾。

**（5）合并后实跑**（`.venv`，Python 3.13.5，全部真实退出码）：

| 命令 | 结果 |
| --- | --- |
| `ruff check .` | All checks passed（`exit=0`） |
| `python -m pytest -o addopts="" -q` | **195 passed / 2 skipped**（合并前 186；+9 例来自 main 的 #18 / #20） |
| `python -m eval.metrics validate` | `exit=0`；`10/10 carry REVIEWED_BY`；corpus binding verified `True` |
| `python -m eval.metrics validate --require-reviewed` | `exit=0`（门禁打开的状态跨过这次合并仍然成立） |

**（6）一条不能替别人判定的一致性风险**：`tests/test_chunking.py` 现在同时含有 main 上 T2 自己的改动和
`d39d658` 里 **T1 账号在 T4 分支上**做的门禁翻转。git 文本层面自动合并成功、195 例全绿，但这两套改动叠加后
的语义是否仍是 T2 想要的，**只有 T2 能认**（§11.13 已把这件事挂在他名下）。测试通过不等于认可。

**（7）推送前的干净检出复现，以及第一次复现给出的假红灯**：`git worktree add --detach` 检出一份当前 HEAD，
里面没有任何未跟踪文件。第一次复现给出 `ruff check .` **`exit=1` 且 stdout 为空**、`pytest` **190 passed /
3 skipped**，与主工作树不一致，当时我把它当成待解释的阻塞项。取 stderr 之后确认这是**解释器选错**，与内容无关：
那条命令走的是 PATH 上的 conda 解释器（pytest **9.1.1**，且 `No module named ruff` —— 这句话在 stderr，
只读 stdout 就像一次无声失败）。换回仓库 `.venv`（pytest **8.4.2**，符合 `requirements-dev.txt` 的
`pytest>=8,<9`，也正是 CI `pip install -r requirements-dev.txt` 会装出来的那一档）在同一份检出里重跑，
结果与主工作树完全一致：`ruff check .` `exit=0`、**195 passed / 2 skipped**、两条 `validate` 均 `exit=0`。
教训两条：本机测量必须先固定解释器路径；`exit=1` 而 stdout 为空时第一步是读 stderr，不是改代码。

本轮登记自身会产生新的 head，它的云端结论只应在新 head 的 Checks 页面上读，不在此自指追记。


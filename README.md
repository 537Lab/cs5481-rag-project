# CS5481 Topic 5 — Knowledge Base Q&A with Verifiable Citations（基础工程 v1）

这是给 **5 人小组** 用的**起步工程**，不是最终作业。

> **组员请从 [`START_HERE.md`](START_HERE.md) 开始**：仓库地址、认领任务、发 PR、判断完成标准都在那里。
> 五个开发任务包见 [`docs/TASKS.md`](docs/TASKS.md)；实际开发记录在 [`docs/DEV_LOG.md`](docs/DEV_LOG.md)，
> AI 辅助使用记录在 [`docs/AI_USAGE.md`](docs/AI_USAGE.md)。
> 当前版本 v1.1：已按外部审阅修复评测共同证据标准、引用三层区分、ParagraphChunker overlap 与薄弱断言。

它能跑通一条最小 RAG 流水线（读文档 → 分块 → Embedding → 向量库 → 检索 → LLM 回答 → 可回查引用 → 无答案拒答），并把五个模块的代码边界、数据格式和测试固定下来，让五个人可以同时改代码而不互相打架。

**这一版明确不做**：20 组正式问答、两种 chunking 的对比实验、任何命中率/正确率数字、prompt 调优、UI、最终报告。这些是后续 PR。

---

## 1. 五分钟跑通（零配置、不需要任何密钥）

```bash
cd cs5481-rag
python3 -m venv .venv
source .venv/bin/activate                  # Windows: .venv\Scripts\activate
python -m pip install -r requirements-dev.txt

python -m ragkit.cli offline-demo         # MOCK 演示，不联网
python -m pytest -q                       # 离线自动化测试
ruff check .                              # 代码检查
```

`offline-demo` 会打印一条带 `[doc_id#chunk_id]` 引用的答案、一条"编造引用被拦截"的拒答、一条"无答案"的拒答。它顶部有 **`[MOCK / OFFLINE DEMO]`** 横幅 —— 这是模拟运行，**不能**把它的输出写进报告。

> 所有命令都要在**仓库根目录**执行。`ragkit` 是普通包，没有 `pip install -e .`，从别的目录运行会找不到模块。

---

## 2. 真实运行（不需要 API key 也能跑完前两步）

```bash
# 第 1 步：把 4 篇真实文档切块、向量化、写入 Chroma
python -m ragkit.cli ingest

# 第 2 步：用真实向量检索，打印 chunk id 与原文片段（引用就是靠这些 id 回查的）
python -m ragkit.cli retrieve "What is retrieval-augmented generation?"
python -m ragkit.cli retrieve "What does a vector database store?" --top-k 3

# 第 3 步：真实 LLM 生成答案（需要 OPENAI_API_KEY）
cp .env.example .env        # 然后编辑 .env，填入 OPENAI_API_KEY
python -m ragkit.cli ask "When was retrieval-augmented generation first proposed?"
```

前两步用的是 **Chroma 内置的本地 ONNX `all-MiniLM-L6-v2`**（384 维、开源模型、本机推理、无需密钥）。首次 `ingest` 会下载约 80 MB 模型到 `~/.cache/chroma`，**之后完全离线**。

### 命令与真实性对照表

| 命令 | 语料 | Embedding | 向量库 | LLM | 标注 |
| --- | --- | --- | --- | --- | --- |
| `offline-demo` | MOCK fixture | MOCK | MOCK 内存 | MOCK | **MOCK** |
| `pytest -q`（默认） | 真实 + MOCK | MOCK | 真实 Chroma | MOCK | 单元测试 |
| `pytest -m real -q` | 真实 | 真实本地模型 | 真实 Chroma | 真实（需 key） | **REAL**，默认跳过 |
| `cli ingest` | 真实 | 真实本地模型 | 真实 Chroma | — | **REAL** |
| `cli retrieve` | 真实 | 真实本地模型 | 真实 Chroma | — | **REAL** |
| `cli ask` | 真实 | 真实本地模型 | 真实 Chroma | 真实 API | **REAL** |

本次实际跑了哪些命令、原始输出是什么，见 [`RUNLOG.md`](RUNLOG.md)。没有跑过的命令在那里会明确写"未执行"。

---

## 3. 目录结构

```
ragkit/            五个模块 + 共享契约（一人一个文件）
  contracts.py     ★ 所有跨模块数据类型与接口，改它要 2 人 review
  config.py        config.toml + .env 读取
  loaders.py       M1 文档接入
  chunking.py      M2 分块（fixed / paragraph 两种最小实现）
  embeddings.py    M3 向量化（本地 ONNX 或 OpenAI 兼容 API）
  store.py         M4 Chroma 持久化与检索
  generation.py    M5 回答生成、引用校验、拒答
  pipeline.py      薄编排（不含任何业务逻辑）
  cli.py           命令行入口
data/raw/          真实文档 + manifest.json + SOURCES.md（出处/许可）
data/index/        Chroma 持久化目录（gitignore，每人本地重建）
tests/             离线测试 + tests/fixtures（明确标注 MOCK）
eval/              评测格式与指标定义（本期只定义，不实验）
docs/ARCHITECTURE.md   数据契约、模块边界表、技术取舍、验收标准
CONTRIBUTING.md    分支 / PR / review / 合并规则
RUNLOG.md          真实运行记录
```

真实文档是 Wikipedia 的 **CC BY-SA 4.0 摘录**，署名与链接见 `data/raw/SOURCES.md`。模拟数据只出现在 `tests/fixtures/`，两者**绝不混放**。

---

## 4. 五个人怎么分工

| 成员 | 模块 | 主要文件 | 输入 → 输出 |
| --- | --- | --- | --- |
| A | M1 文档接入 | `loaders.py` | manifest + 原文 → `list[Document]` |
| B | M2 分块 | `chunking.py` | `Document` → `list[Chunk]` |
| C | M3 向量化 | `embeddings.py` | `list[str]` → `list[list[float]]` |
| D | M4 存储检索 | `store.py` | `(Chunk, vector)` / 查询向量 → `list[RetrievedChunk]` |
| E | M5 生成引用 | `generation.py` | 问题 + 检索结果 → `Answer` |

每个模块的**依赖、测试命令、禁止做什么**写在 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)。
协作规则（分支名、PR、CI、合并）写在 [`CONTRIBUTING.md`](CONTRIBUTING.md)。**开工前请先读这两份**。

---

## 5. 常见问题（新手优先看这里）

**Q：`ModuleNotFoundError: No module named 'ragkit'`**
→ 没在仓库根目录运行，或没激活虚拟环境。执行 `cd cs5481-rag && source .venv/bin/activate`，再用 `python -m ragkit.cli ...`。

**Q：第一次 `ingest` 卡在下载模型 / 超时**
→ 模型 CDN 需要能出网。本机若用代理，先显式指定再运行（**Clash 优先，失败再试肥猫云**）：

```bash
export HTTPS_PROXY=http://127.0.0.1:7897     # Clash 默认 mixed-port
python -m ragkit.cli ingest
# 若 Clash 线路不通，改试肥猫云（默认 7892，可用 QUOTA_FEIMAO_PROXY 覆盖）
# export HTTPS_PROXY=http://127.0.0.1:7892
```

判断"线路可用"要**针对目标域名实测**，不要只看端口能否连上。也可以手工把
`https://chroma-onnx-models.s3.amazonaws.com/all-MiniLM-L6-v2/onnx.tar.gz`
下载到 `~/.cache/chroma/onnx_models/all-MiniLM-L6-v2/` 后重试。模型缓存好后无需网络。

**Q：`ask` 报 `OPENAI_API_KEY is not set`**
→ 只有第 3 步需要密钥。`cp .env.example .env` 后填入；不要在代码、`config.toml`、PR 里粘贴密钥。`.env` 已被 gitignore。若用校内/自建 OpenAI 兼容网关，在 `.env` 里设 `OPENAI_BASE_URL`。

**Q：`Index is empty`**
→ 先跑 `ingest`。`data/index/` 不进 git，每位组员都要在自己机器上重建一次。

**Q：改了 `config.toml` 没生效**
→ 确认在仓库根目录运行；`config.toml` 是唯一被读取的配置（`RAGKIT_CONFIG` 可指定另一份）。改 `chunking.strategy` 后要重新 `ingest`，因为不同策略使用不同的 Chroma collection。

**Q：Python 报 `No usable temporary directory found`**
→ 某些托管环境注入了不可写的 `TMPDIR`。执行 `export TMPDIR=/tmp` 再运行。

**Q：我想换 chunking 策略看看效果**
→ 改 `config.toml` 的 `strategy = "paragraph"` 再 `ingest`。但**本期只是脚手架**：正式对比实验、20 组 QA 和指标脚本还没写，见 `eval/README.md`。

---

## 6. 安全红线（全组必须遵守）

1. **API 密钥只放 `.env` 或 shell 环境变量**，绝不写进代码、`config.toml`、测试、注释、CI 或提交信息。
2. 不提交 `data/index/`、`eval/results/`、`__pycache__/`、`.env`。
3. 不把 MOCK 输出当成真实实验结果；不硬编码命中率/正确率；不伪造"已运行成功"。
4. 报告里需要的"每人贡献比例 + 全体签名"单独一页 —— PR 历史就是证据，别拖到最后补。

## 7. 第一版验收标准

见 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) 的「验收标准」一节（10 条可逐条实测）。本次实测结果记录在 [`RUNLOG.md`](RUNLOG.md)。

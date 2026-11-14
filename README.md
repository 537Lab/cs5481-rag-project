# CS5481 Topic 5 — Knowledge Base Q&A with Verifiable Citations

一个最小可运行的检索增强问答（RAG）基线：读取公开授权文档，切块并向量化后写入本地向量库；
检索返回带出处、许可与字符区间的片段；LLM 只用给定上下文作答，每条引用都能回查原文，
证据不足时明确拒答。

本仓库是五人小组的开发起点，不是最终作业。代码边界、数据契约和测试已固定，便于并行开发。

## 功能

- **文档接入**：从 `manifest.json` 读取原文，一路携带 `source_uri` / `license` 出处信息。
- **分块**：`fixed` 与 `paragraph` 两种基线策略，保持 `doc.text[char_start:char_end] == chunk.text` 不变式。
- **向量化**：Chroma 内置的本地 ONNX `all-MiniLM-L6-v2`（384 维，无需密钥），或 OpenAI 兼容 API。
- **存储与检索**：Chroma 嵌入式持久化，返回 `chunk_id`、相似度、出处与原文片段。
- **生成与校验**：引用 ID 有效性 + 引文逐字性的**结构校验**（不等同于事实正确性）；编造引用、无引用或检索为空时拒答。
- **评测约定**：`eval/` 定义与 chunking 策略无关的共同证据标准和指标口径。
- **零配置演示**：`offline-demo` 用合成 fixture 与测试替身跑通全链路，输出带 MOCK 横幅。

## 技术栈

| 层 | 选择 |
| --- | --- |
| 语言 / 配置 | Python 3.11+，标准库 `tomllib`，`config.toml` 存非敏感参数，`.env` 存密钥 |
| 向量库 / Embedding | ChromaDB（嵌入式持久化），本地 ONNX MiniLM，或 OpenAI 兼容 embedding |
| LLM | OpenAI 兼容接口（`OPENAI_API_KEY`，可用 `OPENAI_BASE_URL` 指向其他网关） |
| 测试 / 检查 | `pytest`（离线单测 + 显式标记的 real 用例）、`ruff` |
| CI | GitHub Actions：`ruff` + 离线 `pytest` + 提交内容密钥扫描 |

不使用 LangChain / LlamaIndex；五个模块各自独立，便于分别开发和讲解。

## 安装与运行

所有命令都在**仓库根目录**执行（`ragkit` 是普通包，未做 `pip install -e .`）。

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

真实链路的前两步不需要任何密钥：

```bash
python -m ragkit.cli ingest
python -m ragkit.cli retrieve "What is retrieval-augmented generation?" --top-k 3
```

首次 `ingest` 需联网下载约 80 MB 的本地模型到 `~/.cache/chroma`，之后完全离线。
`cli ask` 需要 `OPENAI_API_KEY`：`cp .env.example .env` 后填入即可；`.env` 已被 gitignore。

> 新组员请按 [`START_HERE.md`](START_HERE.md) 逐步操作；本机网络或环境差异请自行处理，
> 不要把个人配置写进仓库。

## 当前状态

- **已具备**：4 篇真实公开授权语料、基础流水线、离线测试、静态检查与云端 CI；真实入库与语义检索已跑通。
- **尚未开展**：正式语料扩充、≥20 组正式 QA、chunking 对比实验、检索命中率 / 回答正确率、真实 LLM 回答、报告与演示。
- 未产生任何正式实验结果，也没有产生付费 API 调用。

逐条真实命令与输出见 [`RUNLOG.md`](RUNLOG.md)。

## 协作入口

| 文档 | 负责内容 |
| --- | --- |
| [`START_HERE.md`](START_HERE.md) | 新组员上手：权限、clone、跑通、认领任务、发第一个 PR |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | 协作规则：分支、PR、review、合并、禁止提交项 |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | 技术设计：数据契约、模块边界、技术取舍、验收清单 |
| [`docs/TASKS.md`](docs/TASKS.md) | T1–T5 任务包、语料/评测集冻结规则与依赖顺序 |
| [`eval/README.md`](eval/README.md) | 评测格式、指标口径、实验结果的保存与提交规范 |
| [`docs/DEV_LOG.md`](docs/DEV_LOG.md) / [`docs/AI_USAGE.md`](docs/AI_USAGE.md) | 开发记录与 AI 辅助披露（贡献声明依据） |
| [`RUNLOG.md`](RUNLOG.md) | 实际执行过的命令与原始输出 |

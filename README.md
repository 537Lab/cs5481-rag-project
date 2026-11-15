# CS5481 Topic 5 — Knowledge Base Q&A with Verifiable Citations

五人小组的课程项目。目标是把一组**公开、许可明确、版本固定**的官方文档建成知识库：
用户提问后，系统检索原文片段，让 LLM 只用这些片段作答，每条论断附上可回查的
「来源文档 + chunk + 逐字引文」；知识库里没有答案时明确拒答。重点在后端数据管线与
答案保真机制，不是聊天界面。

> **项目方案（唯一定义）**：[`docs/PROJECT_PLAN.md`](docs/PROJECT_PLAN.md)
> 包含背景与实际问题、目标与预期系统、老师原始要求逐项映射、技术架构与设计理由、
> 五个并行任务、依赖与集成排期、测试 / 实验 / 展示 / 交付标准。
> 应用领域、LLM 方案与任务认领仍需五人共同确认；五个任务目前均未认领。

## 这个仓库现在有什么

- **M1 文档接入**：`manifest.json` 读取原文，`source_uri` / `license` 随文档传递。
- **M2 分块**：`fixed` 与 `paragraph` 两种最小策略，保持
  `doc.text[char_start:char_end] == chunk.text` 不变式。
- **M3 向量化**：Chroma 内置本地 ONNX `all-MiniLM-L6-v2`（384 维、开源、无需密钥），
  或 OpenAI 兼容 embedding API。
- **M4 存储检索**：Chroma 嵌入式持久化，返回 `chunk_id`、相似度、出处与原文片段。
- **M5 生成校验**：引用 ID 有效性 + 引文逐字性的**结构校验**（不等于事实正确性）；
  编造引用、无引用或检索为空时拒答。
- **评测约定**：`eval/` 定义与分块策略无关的共同证据标准与指标口径。
- **零配置演示**：`offline-demo` 用合成 fixture 跑通全链路，输出带 MOCK 横幅。

不使用 LangChain / LlamaIndex；五个模块各自独立，便于分别开发、测试和讲解。

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

首次 `ingest` 需联网下载约 80 MB 本地模型到 `~/.cache/chroma`，之后完全离线。
`cli ask` 需要 LLM API 配置：`cp .env.example .env` 后填入；`.env` 已被 gitignore。
**任何付费 API 调用必须先由全组确认方案**，本仓库目前零付费调用。

## 当前状态

- **已具备**：4 篇开发语料、基础流水线、离线测试（57 passed / 2 skipped）、静态检查与云端 CI；
  真实入库与语义检索已跑通。
- **尚未开展**：正式语料、≥20 组 QA、chunking 对比实验、命中率 / 正确率、真实 LLM 回答、
  报告与 15 分钟展示。
- **单元测试通过不等于满足课程要求**：逐项覆盖情况见
  [`docs/PROJECT_PLAN.md` §3](docs/PROJECT_PLAN.md#3-老师原始要求及符合情况)。
- 未产生任何正式实验结果；逐条真实命令与输出见 [`RUNLOG.md`](RUNLOG.md)。

## 协作入口

| 文档 | 一句话职责 |
| --- | --- |
| [`docs/PROJECT_PLAN.md`](docs/PROJECT_PLAN.md) | **统一方案**：背景、目标、要求映射、架构、任务、排期、交付标准 |
| [`docs/TASKS.md`](docs/TASKS.md) | T1–T5 详细任务卡（输入 / 输出 / 可改文件 / 测试 / 验收 / 演示） |
| [`START_HERE.md`](START_HERE.md) | 新组员上手：clone、跑通、认领、发第一个 PR |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | 分支、PR、review、合并与禁止提交项 |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | 数据契约、模块边界、引用三层与技术取舍 |
| [`eval/README.md`](eval/README.md) | QA 格式、指标口径、结果提交规范 |
| [`docs/DEV_LOG.md`](docs/DEV_LOG.md) / [`docs/AI_USAGE.md`](docs/AI_USAGE.md) | 开发记录与 AI 辅助披露 |
| [`RUNLOG.md`](RUNLOG.md) | 实际执行过的命令与原始输出 |

任务以 GitHub Issues #1–#5 为准；在对应 Issue 评论认领并把 Assignee 设成自己，一人一个。

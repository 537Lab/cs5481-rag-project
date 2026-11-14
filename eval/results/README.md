# 实验结果：保存与提交规范

## 原则

**不伪造数据**，但也不一概禁止结果进仓库。真实、可复现的**汇总指标、图表和实验配置**
应当提交，供全组复核、写进报告并留作贡献与学术诚信的证据；**原始逐条输出**留在本地。

| 类别 | 位置 | 是否提交 |
| --- | --- | --- |
| 汇总指标（每个策略一行、可复核的数字） | `eval/results/summary/<experiment>/` | **提交** |
| 图表（PNG / SVG，能由命令重生成） | 同上 | **提交** |
| 实验配置快照、运行清单 | 同上 | **提交** |
| 逐题原始输出、大日志、模型/索引缓存 | `eval/results/raw/` | **不提交**（已 gitignore） |
| MOCK 输出、AI 编造或未真实运行的数字 | — | **一律禁止** |

目录形态：

```
eval/results/
├── README.md              # 本规范（入库）
├── summary/               # 入库
│   └── <experiment>/      # 例如 chunking_comparison/
│       ├── run.md         # 运行清单：命令、日期、执行者、退出码、复现步骤
│       ├── config.json    # 实验配置快照
│       ├── metrics.json   # 汇总指标
│       ├── metrics.md     # 人类可读表格（供报告引用）
│       └── *.png / *.svg  # 图表（可选）
└── raw/                   # 本地生成，gitignore，不入库
```

## 提交汇总结果的必要条件（每条都要满足）

1. **真实运行**：`run.md` 写完整命令、执行日期、执行者、退出码；本地命令与云端 CI 分开写，
   不把 Agent 的执行写成某人亲自运行。
2. **配置可复现**：`config.json` 记录 `strategy` / `size` / `overlap` / `top_k` /
   `min_coverage` / embedding 模型 / LLM 与 temperature 等，并注明所依据的
   **T1 冻结语料快照标识**与 **T4 冻结 `qa_set.csv` 标识**（冻结规则见
   [`docs/TASKS.md`](../../docs/TASKS.md)）。
3. **数字可追溯**：`metrics.json` 的每个指标都能由 `raw/` 输出或 `run.md` 中的命令重算。
   禁止硬编码、禁止手写「已运行成功」、禁止把结构校验率称作回答正确率。
4. **同一基准**：同一组对比必须使用同一评测集、同一 `top_k`、`min_coverage`、embedding 与 LLM。
5. **开发期输出不得混入 `summary/`**：用 `CORPUS_V0`、`qa_template.csv` 格式示例或 MOCK fixture
   自测得到的数字只能留在本地或 `raw/`，并明确标注「开发用，非正式实验结果」，不得写进报告。
6. **PR 里可复核**：PR 描述写明 reviewer 用哪条命令复现、预期输出是什么。

## 建议的报告字段（`metrics.json`，只列字段，不含数值）

| 字段 | 含义 |
| --- | --- |
| `experiment_id` | 与 `summary/<experiment>/` 目录名一致 |
| `generated_at` | 真实运行时间 |
| `command` | 完整可复制的运行命令 |
| `config_ref` | 同目录 `config.json` |
| `corpus_ref` / `qa_set_ref` | T1 / T4 冻结快照标识 |
| `strategies` | 每个策略一行：`chunk_count`、长度分布、`hit@1`、`hit@3`、拒答相关指标 |
| `judge` | `human` 或明确披露的 LLM judge；结构校验与事实正确性分开列 |

图表须附生成命令；若图表与 `metrics.json` 不一致，以可重算的原始输出为准并在 PR 中说明。

## 与 CI 的关系

- CI 完全离线（无密钥、不下载模型），**不重跑实验**；`ci / check` 绿灯只说明代码与测试没坏，
  不证明某个实验数字正确。
- CI 的密钥扫描会检查提交内容；汇总结果中不得出现 API key、token 或个人环境信息。

本轮仓库规范化**没有生成任何正式实验结果**，`summary/` 目前只有 `.gitkeep` 占位。

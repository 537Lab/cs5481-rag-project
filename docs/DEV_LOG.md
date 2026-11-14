# 实际开发记录

用途：课程要求报告写明**每人贡献比例 + 全体签名**，并遵守学术诚信要求。
本文件按时间记录谁（或哪个 AI 辅助）做了什么、跑过什么命令、结果如何。
**不要把"代码已生成"或"测试通过"记成"作业已完成"。**

截至本记录，**五名组员尚未开始正式开发**；以下内容全部是组长委托 AI 辅助完成的
基础工程准备，最终由组长审阅。组员开始后，请各自在本文件追加自己的记录。

| 日期 (GMT+8) | 阶段 | 执行者 | 做了什么 | 真实验证 |
| --- | --- | --- | --- | --- |
| 2026-11-13 18:12–19:00 | v1.0 基础工程 | AI 辅助（WorkBuddy），组长审阅 | 读课程 PDF；设计五模块契约；实现 loaders/chunking/embeddings/store/generation/pipeline/cli；抓 4 篇 CC BY-SA 语料；写 README/ARCHITECTURE/CONTRIBUTING/RUNLOG/CI/PR 模板；45 个测试 | `ruff` 通过；`pytest` 43 passed / 2 skipped；`cli ingest` 4→28 chunks；`cli retrieve` top-3；`cli offline-demo` 3 案例；密钥扫描无命中。原始输出见 `RUNLOG.md` 第 1–8 节 |
| 2026-11-13 19:19 | 审阅包 | AI 辅助 | 生成 `cs5481-rag-v1-review.zip` / `.txt` 供外部审阅（包在工作区外，未入库） | zip 完整性 `testzip()=None`；46 条目；无凭据 |
| 2026-11-13 19:52–20:10 | v1.1 修复 | AI 辅助（WorkBuddy），依据组长转述的外部审阅意见 | ① eval gold 改共同证据标准（`eval/evidence.py` + `qa_template.csv`）② 引用三层概念拆分（`generation.py` / `cli.py`）③ ParagraphChunker overlap + 元数据修正（`chunking.py` / `store.py`）④ 加固薄弱断言（3 个测试文件 + 新增 `test_eval_evidence.py`）⑤ 正常环境安装/运行/测试确认 | `ruff check .` 通过；`pytest -o addopts="" -ra` → **57 passed / 2 skipped**；`cli offline-demo` / `ingest` / `retrieve` 真实运行。原始输出见 `RUNLOG.md` 第 9 节 |
| 2026-11-13 20:10–20:20 | GitHub 启动 | AI 辅助（WorkBuddy） | `git init -b main`；创建私有仓库 `537Lab/cs5481-rag-project`；首次提交 `a12bb14` 推送 main；CI 首次运行成功；关闭自动合并；确认分支保护/Rulesets 受套餐限制；写 `docs/TASKS.md`、`START_HERE.md`、本文件与 `docs/AI_USAGE.md` | `gh run view` → conclusion `success`（ruff / pytest / 密钥扫描三步全绿）；`allow_auto_merge=false`；保护规则 API 403，改文档化替代流程 |
| 2026-11-14 | T4（任务包 #4） | 组员（PR 作者）+ AI 辅助（Qoder agent），组员本人审阅 | 新增 `eval/qa_set.csv`（35 条：27 answerable + 8 unanswerable）、`eval/metrics.py`（validate/retrieval/score/mock-demo）、`eval/judge_protocol.md`、`tests/test_eval_metrics.py`（39 例）；改写 `eval/README.md`；`RUNLOG.md` 新增第 11 节。未改契约、`config.toml`、`requirements*.txt` 与别人负责的文件 | 本机真实执行：`eval.metrics validate` → 27 条 gold quote 全部逐字定位，10 个 absent token 确认不存在；`retrieval --hits 1,3 --min-coverage 0.5` → **hit@1 16/27=0.5926、hit@3 23/27=0.8519**（两轮一致）；`ruff check .` 通过；`pytest tests/test_eval_metrics.py tests/test_eval_evidence.py` → 45 passed；全量 `pytest` → 96 passed / 2 skipped。零付费调用。**人工 judge 尚未开始，因此无 `answer_correctness` 数字**。原始输出见 `RUNLOG.md` 第 11 节 |

## 已知限制与需人工处理的事项

- GitHub Free + 私有仓库不支持强制分支保护（403），PR review 规则靠人工执行。
- 组长需要在 GitHub 邀请另外 4 名组员为 Collaborator（私有仓库）。
- 真实 LLM API 调用需要密钥与费用方案，**尚未执行，也未产生任何付费调用**。
- 本地工具会话曾出现临时目录限制（`/private/tmp/pytest-of-unknown` EEXIST），
  已用 `--basetemp` 绕过；云端 CI 不受影响。详情见 `RUNLOG.md`。

## 组员追加记录模板

```
| 日期 | 阶段 | 执行者 | 做了什么（含 PR 号） | 真实验证（命令 + 输出摘要） |
```

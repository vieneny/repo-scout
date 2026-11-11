# LangChain：从入门到应用

真实研究案例：**学习 LangChain，用 Python 做个人 RAG 与工具调用助手，优先可读示例和可复用完整流程。**

[在线交互报告](https://vieneny.github.io/repo-scout/) · [离线 HTML](report.html) · [评分依据](assessments.json)

## 检索范围

2026-11-11 采集 GitHub 公开元数据。检索在约 04:57 UTC 完成，仓库核查在其后完成；每个候选保留独立采集时间、默认分支提交 SHA 与最近发布记录。Stars 为该次快照。

三组真实检索，每组最多 10 条，共得到 **26 个去重候选**：

```text
langchain tutorial in:name,description language:Python
langchain rag in:name,description language:Python stars:>100
langchain agent in:name,description language:Python stars:>1000
```

从中挑选 8 个，覆盖教程、官方框架与完整应用，并控制深入阅读的范围。**全部 8 个都来自保存的检索命中**；没有将手工指定仓库伪装成搜索结果。剩余候选名单和选择理由保留在 [selected.json](selected.json)。这不是全平台穷举，也不是只根据 Stars 做榜单。

## 结果怎么理解

| 排名 | 项目 | 保守分 / 上界 | Stars | 主要学习用途 |
|---:|---|---:|---:|---|
| 1 | langchain-ai/langchain | 90.00 / 90.00 | 149,338 | 核对现代模型、工具与 Agent API |
| 2 | RMA-MUN/RAGNotebook | 84.69 / 84.69 | 486 | 真实应用分层与可注入 RAG 测试 |
| 3 | Annyfee/agent-craft | 84.23 / 84.23 | 537 | 中文章节式工具调用与 RAG 路线 |
| 4 | leonyangdev/lc-studylab | 82.61 / 82.61 | 406 | 分阶段中文 LangChain v1 学习 |
| 5 | langchain-ai/langgraph | 80.15 / 80.15 | 44,774 | 状态、图编排与持久化进阶 |
| 6 | chatchat-space/Langchain-Chatchat | 74.09 / 74.09 | 38,713 | 知识库、向量适配器与服务边界 |
| 7 | langchain-ai/streamlit-agent | 67.72 / 67.72 | 1,645 | 聊天 UI、流式展示与检索回调 |
| 8 | pixegami/rag-tutorial-v2 | 49.99 / 64.99 | 969 | 小型 RAG 数据流阅读 |

综合排名服务于上述目标。学习顺序不必照搬排名：可以用 **agent-craft/lc-studylab 的中文章节**建立概念，随时查官方 LangChain 的当前 API，再用 RAGNotebook 学工程化，最后进入 LangGraph。旧示例可读，但需核对依赖代际。

pixegami 的许可证元数据为空，完整文件树中也未见许可证，所以复用价值保留未知，形成 15 分区间；不能理解为已经证实不能复用。另有项目虽然 Stars 高，但默认分支提交停留在 2024/2025 年，平台最近更新时间不代表代码仍活跃。

## 证据与验证边界

- 读取公开 README、依赖声明、结构、默认分支提交和发布信息；额外阅读了关键 RAG/Agent 实现、测试与 CI 配置。
- 定性依据使用固定提交链接。每项非空源码判断都保留理由与证据；维护和热度仍为公开元数据启发式。
- `agent-craft` 初次自动树请求中断，错误保留在快照；后续人工研究读取了同一固定提交的完整树和源码，不将原始失败改成成功。
- 没有安装或执行任何候选项目，没有调用其模型、启动数据库或进行企业生产验收。测试文件存在、代码路径可读和实际运行通过是不同结论。

## 文件与离线复现

| 文件 | 内容 |
|---|---|
| profile.json | 目标、技术栈和能力画像 |
| search.json | 26 个检索候选与来源记录 |
| selected.json | 8 个深入阅读对象、选择理由和未审阅名单 |
| inspected.json | 8 个候选的元数据、源码结构与失败记录 |
| assessments.json | AI 根据静态源码补充的定性评估 |
| report.json / report.html | 最终评分和可交互成果 |

在仓库根目录执行以下命令即可离线核验已提交数据和页面的一致性：

```bash
python -X utf8 tools/verify_example.py
```

自行重新评分和渲染：

```bash
python -X utf8 skills/repo-scout/scripts/repo_scout.py score --input examples/langchain/inspected.json --assessments examples/langchain/assessments.json --out results/langchain/report.json
python -X utf8 skills/repo-scout/scripts/repo_scout.py render --input results/langchain/report.json --out results/langchain/report.html
```

重新评分会使用当前日期计算维护适合度，分数可能变化；采集时间仍保留原值。若要更新 Stars 或源码证据，需要重新检索、核查并审阅。

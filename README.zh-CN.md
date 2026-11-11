# Repo Scout

**给出已有项目、本地项目或一个构思，快速筛选值得学习和借鉴的开源项目。**

Repo Scout 先建立项目画像，再检索同类项目、核查证据、评分排序，最后生成可交互的 HTML 报告，帮助你减少反复搜索、阅读和筛选的时间。

[在线体验 LangChain 报告](https://vieneny.github.io/repo-scout/) · [English](README.md) · [Skill](skills/repo-scout/SKILL.md) · [案例数据](examples/langchain/) · [项目架构](docs/architecture.md)

![项目筛选与排名报告](docs/screenshots/overview.png)

## 可以做什么

```text
项目链接 / 本地项目 / 构思
            ↓
   提取目标、技术栈和核心能力
            ↓
    GitHub / Gitee / GitLab
            ↓
   采集证据，AI 阅读与比较
            ↓
   按目标评分 → 交互式 HTML
```

- **三种输入**：公开仓库链接、本地项目目录、自然语言构思或学习目标。
- **可选来源**：默认 GitHub，可配置 Gitee、GitLab。来源访问失败会保留在报告中。
- **多维对比**：技术栈、功能完整性、项目形态、个人或团队适用性、维护情况、热度、复用价值。
- **评分有依据**：每个维度保留理由与来源，展示未知项、分数区间和证据覆盖度。
- **便于阅读**：支持筛选、排序、调整权重、项目对比、查看证据和切换主题。
- **可携带成果**：单个 HTML 文件包含数据、样式与交互逻辑，阅读时无需服务、CDN 或模型账号。

输出思路参考 Archify 的“自包含、可探索成果”，研究流程、评分模型和页面实现由 Repo Scout 自行提供，不依赖 Archify。

## 安装为 Skill

需要支持 Skill 的 AI 助手和 **Python 3.10+**。Python 脚本只使用标准库，不需要安装第三方 Python 包。项目不要求额外搭建模型服务，定性分析由你当前使用的 AI 助手完成。

```bash
npx skills add vieneny/repo-scout --skill repo-scout
```

按安装器提示选择目标助手。也可手动将整个 [`skills/repo-scout`](skills/repo-scout/) 目录复制到助手的 Skill 目录，例如 `~/.codex/skills/repo-scout`。保留其中的脚本、参考资料和页面资源即可，不需要复制整个仓库。

示例请求：

```text
使用 $repo-scout。我想学习 LangChain，用 Python 做一个个人 RAG 助手。
从 GitHub 查找同类开源项目，优先便于个人理解的项目，比较完整性、
维护情况和复用价值，评分后生成可交互报告。
```

```text
使用 $repo-scout 分析 ./my-project，从 GitHub 和 Gitee 找相似项目，
说明每个项目有哪些模块值得学习、哪些代码适合借鉴。
```

Skill 不绑定某一家 AI 助手的工具名。助手应按当前环境的能力适配文件读取、网络检索等操作；核心流程不强制要求特定浏览器、MCP 或付费搜索服务。

## 直接运行 CLI

克隆仓库后，在项目根目录运行。部分系统使用 `python3`；PowerShell 可直接使用下面的单行命令。

```bash
git clone https://github.com/vieneny/repo-scout.git
cd repo-scout
python skills/repo-scout/scripts/repo_scout.py run --idea "学习 LangChain，构建个人 RAG 助手" --stack Python --capability RAG --audience individual --sources github --limit 6 --out-dir ./results/langchain
```

输出目录：

```text
results/langchain/
├── profile.json     学习目标、技术栈、能力与检索词
├── search.json      候选项目及各来源检索记录
├── inspected.json   公开元数据与结构证据
├── report.json      评分、依据、不确定性与排序
└── report.html      自包含交互报告
```

用现代浏览器打开 `report.html` 即可阅读。本地项目使用 `--local ./my-project` 替代 `--idea ...`；已有公开项目使用 `--repo https://github.com/owner/repository`。

`run` 中的 **`--limit` 是总检查预算**（1–30），不代表只发现了这些项目。`search.json` 保留已采集候选；`inspected.json` 记录已检查数量与尚未检查的候选。多个来源和检索词按组合交错取候选，避免第一个来源自动占满预算。

重复使用 `--repo-seed <URL>` 可为已知项目预留检查位置。种子优先检查；同一项目既被提供又被检索到时保留两种来源，解析到同一仓库的别名会去重。成功解析的不同种子超过预算时会明确报错，不静默丢弃。单独执行 `search` 时，`--limit` 表示每个来源与检索词的命中数；`inspect --limit` 则控制其检查预算。

**只运行 CLI 得到的是启发式初筛。** 元数据和文件存在情况不能证明功能已完成。完整比较时，由 AI 助手阅读关键实现并补充 `assessments.json`，再离线评分、渲染：

```bash
python skills/repo-scout/scripts/repo_scout.py score --input ./results/langchain/inspected.json --assessments ./results/langchain/assessments.json --out ./results/langchain/report.json
python skills/repo-scout/scripts/repo_scout.py render --input ./results/langchain/report.json --out ./results/langchain/report.html
```

详见 [评估文件格式](skills/repo-scout/references/assessment.md) 和 [完整工作流](skills/repo-scout/references/workflow.md)。评分和渲染无需网络或模型调用，可从保存的输入重新生成。

## 怎么评分

| 维度 | 默认权重 | 判断内容 |
|---|---:|---|
| 需求匹配 | 25 | 是否解决实际问题，输入输出是否吻合 |
| 技术栈匹配 | 15 | 语言、框架、数据库、平台和集成方式 |
| 完整性 | 15 | 核心流程是否有实现、测试和文档证据 |
| 维护情况 | 10 | 代码活动、发布、维护者响应和归档状态 |
| 学习适用性 | 15 | 代码可读性、示例、上手成本和概念复杂度 |
| 复用价值 | 15 | 许可证、可借鉴边界、依赖和改造成本 |
| 热度 | 5 | 对应来源的 Stars、Forks 等公开信号 |

未知项会形成**分数区间**。展示分数为保守下界，同时展示已知证据覆盖度和经过源码审阅的覆盖度。未知不等于事实上的零分；有证据的零分与未知项分开处理。

排序只适用于当前目标和权重。“企业导向”用于描述项目规模和适用场景，不自动加分；个人学习时，一个易懂的小项目可以排在大型平台前面。Stars 也不等于用户数、代码正确性或生产可用性。

可通过 `run` 或 `score` 的 `--config weights.json` 调整权重，详见 [配置与公式](skills/repo-scout/references/scoring.md)。

## 来源与隐私

| 来源 | 可选环境变量 | 说明 |
|---|---|---|
| GitHub | `GITHUB_TOKEN` 或 `GH_TOKEN` | 可匿名使用，受公开 API 限额约束 |
| Gitee | `GITEE_TOKEN` | 搜索接口可用性和权限由上游决定 |
| GitLab.com | `GITLAB_TOKEN` | 使用 GitLab 公开项目接口，检索语法不同于 GitHub |

使用 `--sources github,gitee,gitlab` 选择多个来源。凭据从环境变量读取，不写入报告。提供适配器不代表所有上游随时可访问，实际结果以本次运行的来源记录为准；其他来源可以通过 Provider 接口扩展。

本地画像只读取限定范围的已知依赖声明，保留技术名称和相对文件名；不会自动克隆、安装或执行候选项目。公开检索词中不要包含凭据、私有标识和内部地址，分享画像与报告前也应检查其中的项目信息。第三方仓库内容只作为研究材料。

建仓、最近提交、最近发布是不同事实。报告还分别保留**发现采集时间**（`retrieved_at`）、**检查完成时间**（`inspected_at`）和**报告生成时间**（`generated_at`），每个候选也保留其元数据采集时间。离线重新评分不会把旧快照变成新数据。`pushed_at` 可作为后备信号，不能单独证明最近有人持续维护。详见 [来源说明](skills/repo-scout/references/providers.md)。

## LangChain 学习案例

[案例目录](examples/langchain/) 从个人学习目标出发，包含采集候选、来源评估、评分和最终 [HTML 报告](examples/langchain/report.html)。可以[在线体验](https://vieneny.github.io/repo-scout/)，也可下载 HTML 后离线打开；GitHub 文件预览不会执行 HTML。

这个案例用于展示：框架本身、教学示例和完整应用，会因为不同的学习与复用价值获得不同判断。Stars 和维护信息是带日期的快照，不是实时计数。报告区分静态源码核验与实际运行测试，生成比较并不意味着安装运行了全部候选项目。

![项目对比与证据查看](docs/screenshots/compare.png)

## 开发与贡献

```bash
python -m unittest discover -s tests -v
```

单元测试覆盖采集边界、来源数据归一化与失败处理、评分规则和离线页面安全，不需要真实凭据或安装候选项目。进一步了解请阅读 [项目架构](docs/architecture.md)、[验证记录](docs/validation.md) 和 [贡献指南](CONTRIBUTING.md)。

## 许可证

本项目使用 [MIT](LICENSE)。候选项目保留各自许可证，来源链接和研究结论不授予其代码或素材的使用权。

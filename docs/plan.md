# 自动化深度研究智能体 (Deep Research Agent) 建设方案

本方案旨在构建一个类似于 OpenAI Deep Research 或 Gemini Research 的自动化深度研究智能体。该智能体能够根据用户给定的研究主题，自动规划研究路径、多渠道搜集信息、迭代式深度探索、对海量学术与网页内容进行事实提取，并最终生成一份包含详尽引用和参考文献的高质量 Markdown 研究报告。

---

## 1. 系统架构与核心流程

系统采用 **多智能体 (Multi-Agent) 协作与前后端分离架构**，核心的 Agent 逻辑与分析处理在 Python 后端运行，前端通过现代化的 Web 界面与用户交互，并通过 Server-Sent Events (SSE) 或 WebSocket 实现研究过程的实时动态可视化。

为了便于后续测试与调优，**所有 Agent 的 Prompt 将进行集中化配置与管理**。

### 1.1 多 Agent 架构设计

系统由以下几个协作的 Agent 组成：
1. **规划智能体 (Planner Agent)**：负责解析用户的研究主题，生成初始研究大纲，拆解为多个子查询，并确定每个方向的研究深度与广度。
2. **检索智能体 (Searcher Agent)**：负责调用 Tavily/Google Search 或学术 API (arXiv, Semantic Scholar) 获取相关信息。
3. **抓取智能体 (Scraper Agent)**：负责读取高价值源链接，清洗 HTML 标签，返回精炼文本。
4. **事实提取智能体 (Extractor Agent)**：负责从检索和抓取的内容中，对照原始来源提取出事实要点与论据笔记。
5. **合成智能体 (Synthesizer Agent)**：负责将收集到的事实笔记进行去重、融合，并逐步分章节撰写最终的 Markdown 报告。

```
                     +-------------------------------------------------+
                     |                 用户 Web 界面                   |
                     |       (Vue 3 + Vite + Glassmorphism UI)         |
                     +------------------------+------------------------+
                                              | 1. 发起研究请求 / 实时状态订阅
                                              v
                     +-------------------------------------------------+
                     |               FastAPI 后端服务                  |
                     +------------------------+------------------------+
                                              | 2. 调度执行
                                              v
                     +-------------------------------------------------+
                     |       深度研究 Multi-Agent 核心引擎              |
                     |                                                 |
                     |   +------------------------------------------+  |
                     |   |          Prompt 集中管理配置模块         |  |
                     |   |          (prompts.yaml / prompts.py)     |  |
                     |   +--------------------+---------------------+  |
                     |                        |                        |
                     |   +--------------------v---------------------+  |
                     |   |    Planner Agent -> Searcher Agent       |  |
                     |   |                                          |  |
                     |   |    Scraper Agent -> Extractor Agent      |  |
                     |   |                                          |  |
                     |   |            Synthesizer Agent             |  |
                     |   +--------------------+---------------------+  |
                     |                        |                        |
                     |                        v                        |
                     |   +------------------------------------------+  |
                     |   |        自定义轻量级异步事件循环          |  |
                     |   |   (支持工具调用记录 & 详细输入输出日志)  |  |
                     |   +------------------------------------------+  |
                     +-------------------------------------------------+
```

### 1.2 核心工作流程
1. **输入与规划 (Plan)**: 用户输入研究主题、搜索深度 (Depth) 和搜索广度 (Breadth)。Planner Agent 使用集中管理的 Prompt 生成初始研究思路与子查询任务。
2. **搜索与检索 (Search & Retrieve)**: Searcher Agent 使用 Tavily API 获取实时网页数据，并利用 arXiv API / Semantic Scholar API 获取学术论文摘要与核心结论。
3. **抓取与清洗 (Scrape & Clean)**: Scraper Agent 抓取网页正文，清洗干扰元素，只提取纯文本。
4. **迭代深度研究 (Iterate & Dig)**: 核心事件循环驱动各个 Agent 协同运行。在每一步中，详细记录每个 Agent 的 LLM 输入输出日志、工具调用记录（Search、Scrape、Extract 等）。Agent 根据已有结果判断当前信息是否完备，若发现新线索，则由 Planner 自动生成第二代、第三代搜索查询（根据预设的 Depth 进行递归），进一步深挖。
5. **多源融合与草稿生成 (Synthesis & Draft)**: Synthesizer Agent 整合所有收集到的笔记与来源引用链接，生成大纲，并分章节逐步撰写详细报告。
6. **最终生成 (Deliver)**: 生成带有 inline 引用 (如 `[1]`, `[2]`) 及尾部参考文献列表的 Markdown 格式报告。


---

## 2. 技术栈选型

### 2.1 后端技术栈 (Python 3.11+)
- **Web 框架**: `FastAPI` (高效的异步 API 支持) + `Uvicorn` (ASGI 服务器)
- **Agent 框架**: 自定义轻量级异步事件循环，内建**工具调用链路追踪**与 **I/O 运行日志**记录机制。
- **大模型支持**: Zhipu AI GLM-5.2 API (通过官方 `zhipuai` SDK 或兼容 OpenAI 接口的 SDK)
- **搜索引擎集成**:
  - `tavily-python` (专为 LLM 优化的 Tavily 搜索引擎 API，由用户提供 API Key)
  - `arxiv` Python SDK / `Semantic Scholar` API (学术搜索)
- **抓取与提取**: `httpx` + `BeautifulSoup4` 或 `playwright` (用于动态渲染页面)，配合 `jina-reader` (将网页直接转化为 Markdown 供 LLM 阅读)
- **提示词管理**: `PyYAML` (用于读取集中配置的 YAML 提示词模板)

### 2.2 前端技术栈
- **核心框架**: `Vue 3` (Composition API) + `TypeScript`
- **构建工具**: `Vite`
- **样式设计**: Vanilla CSS (自定义实现高颜值的 Glassmorphism 磨砂玻璃特效与暗黑模式)
- **状态及实时展示**: Server-Sent Events (SSE)，用于将 Agent 后端执行的每一步状态（例如："正在搜索..."、"正在阅读网页..."）以及工具调用日志、大模型 I/O 记录实时推送给前端展示
- **Markdown 渲染**: `markdown-it` / `marked` 并集成代码高亮和数学公式渲染 (`KaTeX`)
- **图标库**: `lucide-vue-next`

---

## 3. 功能模块详细设计

### 3.1 后端 Agent 引擎设计

#### 集中式 Prompt 管理
系统建立独立的提示词管理模块 `backend/prompts/`，将各个 Agent (Planner, Searcher, Extractor, Synthesizer) 的 System Prompt 和 User Prompt 集中于 YAML 文件或统一的 Python 模块中。这使得测试人员和开发者可以无需修改核心代码，即可一键调优或替换提示词。

#### State 数据结构与日志记录 (Research State & Logging)
为了记录工具调用记录和大模型输入输出日志，定义如下数据结构：

```python
class ToolCallRecord(BaseModel):
    tool_name: str
    arguments: dict
    output: str
    timestamp: float

class LLMIOLog(BaseModel):
    agent_name: str
    prompt_name: str
    llm_input: str
    llm_output: str
    timestamp: float

class ResearchState(BaseModel):
    topic: str
    max_depth: int
    max_breadth: int
    current_depth: int = 0
    sources: List[dict] = []         # 已搜集的源链接及其摘要
    extracted_facts: List[dict] = []  # 提取的事实节点与来源对照
    search_history: Set[str] = set() # 避免重复搜索的查询记录
    tool_calls: List[ToolCallRecord] = []  # 详细工具调用记录 (Tool Calling Logs)
    llm_logs: List[LLMIOLog] = []          # 详细大模型 I/O 日志 (LLM Inputs/Outputs)
    logs: List[str] = []                   # 运行实时状态日志
```

#### 搜索路由与学术过滤 (Search Router)
根据用户的偏好和关键词，判断是调用 Web 搜索还是学术搜索：
- 如果关键词包含学术性强词汇（如 "algorithm", "clinical study", "framework", "performance benchmark"）或用户开启了学术优先，则优先调用 ArXiv 或 Semantic Scholar API 检索最新学术论文。
- 否则，调用 Tavily 获取最新网页数据。

#### 异步提取器 (Content Extractor)
为了防反爬并提高效率，采用：
1. Jina Reader API：将 URL 作为参数传入 `https://r.jina.ai/{url}`，可直接得到排版良好的 Markdown。
2. 本地备用方案：通过 `httpx` 获取网页，再使用 `BeautifulSoup` 提取核心段落。

### 3.2 前端 Glassmorphism（磨砂玻璃）UI 设计

为了提供顶级的视觉体验，前端将采用纯 Vanilla CSS 编写现代暗黑玻璃拟态样式。

- **配色方案**:
  - 背景色: 深靛蓝至极深灰渐变 (`linear-gradient(135deg, #0f172a, #020617)`)
  - 玻璃卡片: `background: rgba(30, 41, 59, 0.45); backdrop-filter: blur(16px); border: 1px solid rgba(255, 255, 255, 0.08);`
  - 主题色 / 渐变色: 极光绿与科技蓝渐变 (`linear-gradient(to right, #38bdf8, #34d399)`)
- **主界面分区**:
  1. **配置面板 (Left Sidebar)**:
     - 搜索主题输入框
     - 深度/广度滑动条 (Slider)
     - 数据源选择器 (Web / Academic / All)
     - 开始/停止 按钮
  2. **实时研究脑图/日志区 (Center Main)**:
     - 实时流式输出日志 (Stream Logs)
     - 当前正在探索的 "Query Tree" 树状节点动态展开动效，展示研究深度与广度的分叉过程
  3. **报告预览区 (Right Panel)**:
     - 在研究完成后，以精美的 Markdown 排版展示最终研究报告。
     - 提供一键导出为 Markdown、HTML 或 PDF 的功能。

---

## 4. 实施计划 (Roadmap)

### 第一阶段：后端 Agent 核心搭建 (预计 3-4 天)
- [ ] 初始化项目结构与虚拟环境。
- [ ] 编写搜索引擎连接模块（Web 搜索 API + 学术 API）。
- [ ] 编写 Planner 规划器和事实提取器逻辑。
- [ ] 构建迭代式搜索主循环，实现深度 (Depth) 和广度 (Breadth) 的递归控制。
- [ ] 编写 Synthesis 生成器，合成 Markdown 报告。

### 第二阶段：FastAPI 接口与实时流推送 (预计 2 天)
- [ ] 搭建 FastAPI 服务，定义 API 接口。
- [ ] 实现 SSE (Server-Sent Events) 服务端，支持将 Agent 执行日志实时推送。
- [ ] 添加历史报告保存与检索功能（基于本地 JSON 或轻量数据库 SQLite）。

### 第三阶段：前端高颜值 Web 客户端开发 (预计 3 天)
- [ ] 初始化 Vue 3 + TypeScript 项目。
- [ ] 编写全局 CSS 主题系统（Glassmorphism 磨砂玻璃、渐变、过渡动效）。
- [ ] 开发配置面板、实时状态监控组件（树状进度图/日志流）。
- [ ] 集成 Markdown 渲染引擎，开发美观的报告阅读与下载界面。

### 第四阶段：系统联调与优化 (预计 2 天)
- [ ] 前后端联调，验证长时间运行任务的稳定性。
- [ ] 优化 LLM 的 prompt，提高提取事实的准确度和报告质量。
- [ ] 限制单次研究的最大 API 消耗，加入费用预算预估与熔断机制。

---

## 5. 已确定的技术设计决策

根据沟通，以下设计决策已确定并写入方案：
1. **大语言模型**: 采用 Zhipu AI GLM-5.2 API 作为主控 LLM，所有 Agent 的推理与总结工作皆由其完成。
2. **搜索引擎**: 使用 Tavily API 作为主要网页搜索引擎，学术领域结合 arXiv / Semantic Scholar API，不再引入 SearxNG。
3. **前端框架**: 确立采用 **Vue 3 + Vite + TypeScript** 搭建 Web 客户端，使用 CSS 实现磨砂玻璃拟态视觉效果。
4. **Agent 架构**: 使用多智能体结构，通过自定义异步事件循环驱动，具备工具调用追踪及详细的 LLM I/O 日志记录功能。
5. **Prompt 管理**: 提示词进行集中化配置管理（存放于 `backend/prompts/` 目录），方便后续测试与调优。

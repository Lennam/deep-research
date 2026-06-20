# Deep Research Agent 🚀 | 自动化深度研究智能体

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100.0%2B-green.svg)](https://fastapi.tiangolo.com/)
[![Vue 3](https://img.shields.io/badge/Vue-3.5.0%2B-emerald.svg)](https://vuejs.org/)
[![Vite](https://img.shields.io/badge/Vite-8.0.0%2B-purple.svg)](https://vite.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Deep Research Agent** 是一个集成多智能体协同（Multi-Agent Collaboration）、异步递归探索、实时流式状态推送（SSE）以及高保真磨砂玻璃拟态（Glassmorphic）前端的自动化深度研究系统。系统能够针对用户给定的研究课题进行深度规划、多源信息检索、内容清洗提炼、交叉事实核查，并最终生成具有详尽引用文献的高质量 Markdown 格式研究报告。

---

## 🌟 核心特性

- **🤖 多智能体协同机制 (Multi-Agent)**：
  - **Planner Agent**：拆解研究主题，规划子研究方向，生成最优检索词。
  - **Scraper Agent**：并发抓取高质量网页与学术资源正文，自动降级与清洗 HTML 标签。
  - **Extractor Agent**：深度阅读清洗后的内容，提取强相关的客观事实片段并归档为 `FactNode`。
  - **Synthesizer Agent**：冲突消除、去重融合，分章节撰写终期 Markdown 报告。
- **🔄 异步递归深度探索 (Async Research Loop)**：
  - 支持深度 (`max_depth`) 和广度 (`max_breadth`) 限制的异步递归探索。
  - 使用 `asyncio.gather` 实现多路子方向并发深挖。
- **🌐 智能搜索路由 (Search Router)**：
  - 自动识别查询属性，智能路由至 **Tavily Web Search** 或 **Academic API** (arXiv & Semantic Scholar)。
- **🛡️ 运行时熔断与安全防线 (Guardrails)**：
  - **API 费用软/硬双阶段熔断**：提供预算预估算法，软熔断时停止派生子任务，硬熔断时立即中止爬取并基于已获事实合成“阶段性报告”，杜绝失控空转。
  - **本地双级缓存 (SQLite Cache)**：提供搜索结果 (1天有效期) 与网页内容 (7天有效期) 缓存，降低网络请求耗时与 API 消耗。
  - **孤立协程熔断 (Orphan Task Cleaning)**：服务端自动检测 SSE 客户端物理断开，注销消息队列，物理终止执行协程。
- **💎 极致视觉 Glassmorphism 前端 UI**：
  - 基于 Vue 3 + TypeScript 纯 Vanilla CSS 实现的暗黑科技风磨砂玻璃特效。
  - 实时绘制研究脑图 (QueryTree SVG 动态渲染) 展现递归深度与广度。
  - SSE 实时研究状态流式控制台日志与报告 Markdown (含 KaTeX 公式) 渲染。

---

## 🏗️ 系统架构设计

### 目录结构

```text
.
├── backend/                  # Python 异步后端应用
│   ├── app/
│   │   ├── api/               # API 路由控制层 (FastAPI - 任务控制、报告归档)
│   │   ├── agents/           # 多智能体定义层 (Planner, Scraper, Extractor, Synthesizer)
│   │   ├── core/             # 控制循环与状态层 (AsyncResearchLoop, ResearchState)
│   │   ├── search/            # 检索与抓取服务 (Tavily, Academic, BS4/Jina)
│   │   ├── prompts/           # 集中式提示词配置管理 (prompts.yaml)
│   │   └── utils/             # 数据库、通用工具与日志
│   ├── requirements.txt      # 依赖声明文件
│   └── test_cli.py           # 命令行沙盒运行器
├── frontend/                  # Vue 3 前端应用
│   ├── src/
│   │   ├── components/       # UI 组件 (ConfigPanel, QueryTree, LogConsole, ReportViewer)
│   │   ├── composables/      # 逻辑复用 (useSSE 长连接控制器)
│   │   └── assets/           # 全局样式与变量定义
│   └── package.json          # 前端依赖配置
├── docs/                     # 设计规约与执行计划文档
├── ARCHITECTURE.md           # 核心系统架构说明书
└── AGENTS.md                 # 智能体协同与开发指南
```

### 系统数据与调用流

```mermaid
graph TD
    subgraph Frontend [前端展示层 (Vue 3)]
        VC[ConfigPanel - 配置面板]
        QT[QueryTree - SVG 脑图]
        LC[LogConsole - 终端日志]
        RV[ReportViewer - 报告渲染]
        useSSE[useSSE - SSE 客户端]
    end

    subgraph FastAPI [API 控制层]
        API[FastAPI Routers]
        TM[TaskManager - 任务管理器]
        DB[(SQLite / aiosqlite)]
    end

    subgraph CoreLoop [控制循环与状态层]
        Loop[AsyncResearchLoop]
        State[ResearchState - 全局状态机]
    end

    subgraph Agents [多智能体业务层]
        Planner[Planner Agent]
        Scraper[Scraper Agent]
        Extractor[Extractor Agent]
        Synthesizer[Synthesizer Agent]
    end

    subgraph Infrastructure [基础服务层]
        PM[PromptManager - 提示词模块]
        SR[SearchRouter - 搜索路由器]
        TC[Tavily Client - 网页检索]
        AC[Academic Client - 学术检索]
        Jina[Scraper Service - 页面抓取]
    end

    VC -->|1. POST /api/research/start| API
    API -->|2. 管理后台任务| TM
    TM -->|3. 启动协程循环| Loop
    useSSE -->|4. GET /api/research/stream/{id}| API
    TM -.->|5. 实时推送事件帧| useSSE

    Loop -->|读写| State
    Loop -->|调度执行| Planner
    Loop -->|调度执行| Scraper
    Loop -->|调度执行| Extractor
    Loop -->|调度总结| Synthesizer

    Planner --> PM
    Extractor --> PM
    Synthesizer --> PM
    Scraper -->|正文提炼| Jina
    Loop --> SR
    SR -->|Web 搜索| TC
    SR -->|学术论文| AC
    TM -->|历史持久化| DB
```

---

## 🛠️ 技术栈选型

* **后端 (Python 3.11+)**：
  * **主框架**：FastAPI + Uvicorn (异步高并发处理)
  * **核心 LLM**：Zhipu AI GLM-5.2 (兼容 OpenAI API 规范)
  * **搜索引擎**：Tavily API (Web)、arXiv & Semantic Scholar API (学术)
  * **数据持久化**：aiosqlite (SQLite 异步驱动)
  * **网页转化**：Jina Reader API / BeautifulSoup4 备用降级
* **前端 (Vue 3 + TS + Vite)**：
  * **核心技术**：TypeScript, Composition API, SFC
  * **网络通信**：Server-Sent Events (SSE) 保持长连接状态下沉
  * **报告渲染**：marked + KaTeX (数学公式实时渲染)
  * **样式设计**：Vanilla CSS 极致毛玻璃效果，响应式无缝排版

---

## 🚀 部署与运行指南

### 1. 环境准备与配置

在运行项目之前，需要提供对应的 API Key。

在 `backend/` 目录下创建并配置 `.env` 配置文件：

```env
# 核心大模型配置 (支持 OpenAI 协议兼容端点)
OPENAI_API_KEY=your-glm-api-key-here
OPENAI_API_BASE=https://open.bigmodel.cn/api/paas/v4

# 搜索引擎配置
TAVILY_API_KEY=your-tavily-api-key-here
```

### 2. ⚡ 快捷一键启动 (推荐)

我们在项目根目录下提供了一个一键启动开发环境的脚本 `start.sh`，它会自动执行环境检查、虚拟环境激活、前端依赖安装，并同时在后台拉起前后端服务，支持通过 `Ctrl+C` 一键安全关闭：

```bash
# 在项目根目录下，直接运行一键启动脚本
./start.sh
```

---

### 3. 分步手动启动 (备选)

如果你希望手动分别控制前后端，也可以按照以下步骤分别运行：

#### 后端服务启动

```bash
# 进入后端目录
cd backend

# 创建并激活虚拟环境 (可选)
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 运行 FastAPI 接口服务 (默认启动在 127.0.0.1:8000)
python -m app.main
```

#### 前端服务启动

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器 (默认启动在 127.0.0.1:5173)
npm run dev
```

### 4. 命令行沙盒测试 (CLI)

如果你想绕过前端，直接在命令行控制台启动深度研究任务并查看输出，可以使用 `test_cli.py`：

```bash
cd backend
# 启动对特定主题的深度研究 (深度2，广度2，探索全部渠道)
python test_cli.py --topic "生成式人工智能在医疗诊断中的前沿应用" --depth 2 --breadth 2 --mode all
```
*执行完成后，Markdown 报告及运行状态 State logs 将自动保存至 `backend/output/` 文件夹。*

---

## 🧪 自动化测试

项目内嵌完整的自动化单元测试与集成测试，覆盖提示词、检索、爬虫、状态追踪以及核心异步循环逻辑。

```bash
# 进入后端根目录并运行所有测试
cd backend
PYTHONPATH=. pytest tests/

# 运行指定的单个测试文件
PYTHONPATH=. pytest tests/test_loop.py
```

---

## 📝 开发者指南与约束

在对本项目进行二次开发或维护时，请严格遵守以下开发规约（详细参见 [AGENTS.md](./AGENTS.md)）：

1. **集中提示词管理**：
   - 严禁在 Python 业务代码中硬编码 System/User Prompt。所有提示词必须定义在 [prompts.yaml](./backend/app/prompts/prompts.yaml) 中，并通过 `PromptManager` 加载。
   - YAML 中包含花括号 `{}` 的内容（如 JSON 模式定义）必须使用双花括号 `{{` 和 `}}` 进行转义。
2. **状态可观测性跟踪**：
   - 所有执行具体工具的网络 IO 函数（如搜索、抓取）必须标记 `@track_tool_call(tool_name)` 装饰器。
   - 所有调用 LLM 接口的地方必须传递 `state` 指针以捕获 input/output Token 损耗并实时审计。
3. **并发安全与去重**：
   - 抓取阶段必须控制全局并发信号量（Semaphore），防止因过高并发导致源端封禁或触发 429。
   - 严格在检索和爬取前比对 `search_history` 和 `scraped_urls`，防止环形引用导致的死循环。


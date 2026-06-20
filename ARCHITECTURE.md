# 自动化深度研究智能体 架构规约说明书 (ARCHITECTURE.md)

本系统是一个集成多智能体协同、异步递归探索、实时流式状态推送（SSE）与极致磨砂玻璃拟态前端的自动化深度研究系统。本架构设计严格遵循 **Harness Engineering（运行时脚手架工程）** 规范，贯彻“仓库即规约（Repository as Spec）”的设计哲学。

本说明书为 AI 智能体与开发者提供了明确的**系统职责边界、域映射、通信契约与安全熔断防线**，作为系统运行与演进的最高事实来源。

---

## 1. 系统概述与设计哲学

本系统的核心目标是使 AI 智能体在进行深层、广层互联网与学术课题研究时，能够**高度自治、实时反馈且行为受控**。

### 1.1 设计哲学：Repository as Spec
* **可达性上下文**：智能体无法通过外部工具访问 Wiki、Slack 或 Jira。所有关于系统模块结构、状态机、API 接口及拦截规则的定义，必须沉淀在代码库内部（如 `AGENTS.md`、`ARCHITECTURE.md` 及设计规范中）。
* **taste 规则化 (Taste Invariance)**：将对“代码质量、系统鲁棒性、费用熔断和安全性”的抽象品味，转化为具体的、代码强制执行的物理约束（如心跳检测、孤儿协程熔断、并发信号量限制）。

---

## 2. 域映射与系统分层 (Domain Map)

系统代码结构分为清晰的五层，每层具有单一职责和严格的依赖规则：

```
. (Repository Root)
├── frontend/                  # Presentation Layer: 前端展示层（Vue 3 + TS）
└── backend/                   # 后端应用根目录
    └── app/
        ├── api/               # Router Layer: API 路由与控制器层（FastAPI）
        ├── core/              # Loop & Manager Layer: 控制循环与状态管理层
        ├── agents/            # Business Layer: 智能体角色定义层
        ├── search/            # Infrastructure Layer: 检索与抓取服务层
        ├── prompts/           # Config Layer: 提示词管理层（yaml 配置）
        └── utils/             # Cross-cutting Layer: 数据库与日志通用工具层
```

### 2.1 系统架构图

```mermaid
graph TD
    subgraph Frontend [前端展示层 (Vue 3 + Vite)]
        VC[ConfigPanel - 配置面板]
        QT[QueryTree - SVG 脑图]
        LC[LogConsole - 终端日志]
        RV[ReportViewer - 报告渲染]
        useSSE[useSSE - SSE 客户端]
    end

    subgraph FastAPI [API 控制器与管理层]
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

    subgraph Infrastructure [基础设施与服务层]
        PM[PromptManager - 集中式模板]
        SR[SearchRouter - 搜索路由器]
        TC[Tavily Client - 网页检索]
        AC[Academic Client - 学术检索]
        Jina[Scraper Service - Jina/BS4 抓取]
    end

    %% 调用与通信流向
    VC -->|1. POST /start| API
    API -->|2. 创建/管理后台任务| TM
    TM -->|3. 启动后台协程| Loop
    useSSE -->|4. GET /stream 长连接| API
    TM -.->|5. 事件流式广播| useSSE

    Loop -->|读写| State
    Loop -->|调用| Planner
    Loop -->|调用| Scraper
    Loop -->|调用| Extractor
    Loop -->|调用合成| Synthesizer

    Planner --> PM
    Extractor --> PM
    Synthesizer --> PM

    Scraper -->|提取清洗正文| Jina
    Loop --> SR
    SR -->|路由 Web| TC
    SR -->|路由学术| AC
    
    TM -->|持久化归档| DB
```

---

## 3. 状态机与核心数据流 (State & Data Flow)

系统的所有运行时行为都是围绕全局单一事实源（Single Source of Truth） **`ResearchState`** 展开的。

### 3.1 状态流转时序与智能体分工

1. **大纲规划 (Planner Agent)**：分析用户输入的 `topic`，拆解出互不重复的 `sub_topics`（研究子方向）并生成各子方向的检索关键词 `search_queries`。
2. **异步控制循环 (AsyncResearchLoop)**：核心控制中枢。开始递归探索，维护当前探索深度 `current_depth`，并使用 `asyncio.gather` 并发处理各子课题分支。
3. **网页与论文检索 (SearchRouter & Scraper Agent)**：针对子查询，搜索路由判断是否路由到学术数据库，获取高价值 URL。Scraper 并发抓取并利用 Jina Reader（降级采用 BeautifulSoup）清洗正文。
4. **事实笔记抽取 (Extractor Agent)**：阅读清洗后的 Markdown 文本，提取与当前子方向强相关的客观事实，转化为 `FactNode` 归档到 `state.extracted_facts`。
5. **章节逐步合成 (Synthesizer Agent)**：在递归结束或硬熔断触发时，整合所有事实笔记与源链接（`state.sources`），进行冲突融合和去重，最终分章节撰写并合成完整的 Markdown 研究报告。

---

## 4. 关键协议契约 (Core Communication Protocols)

### 4.1 RESTful API 控制契约

| 接口端点 | 方法 | 请求体/参数说明 | 响应体 (JSON) | 职责 |
| :--- | :--- | :--- | :--- | :--- |
| `/api/research/start` | `POST` | `{"topic": str, "max_depth": int, "max_breadth": int, "search_mode": str}` | `{"task_id": str, "status": "running"}` | 异步启动研究协程任务 |
| `/api/research/stream/{task_id}` | `GET` | 路径参数: `task_id`，请求头: `Accept: text/event-stream` | `text/event-stream` 字节流 | 监听任务的实时流式推送通道 |
| `/api/research/stop/{task_id}` | `POST` | 路径参数: `task_id` | `{"task_id": str, "status": "stopped"}` | 物理中止并清理活跃的任务 |
| `/api/reports` | `GET` | 无 | `[{"id": str, "topic": str, "created_at": str, ...}]` | 查询历史研究报告列表（排除大字段） |
| `/api/reports/{id}` | `GET` | 路径参数: `id` | `{"id": str, "report_content": str, "state_json": dict}` | 获取某篇报告的 Markdown 详情及审计日志 |
| `/api/reports/{id}` | `DELETE` | 路径参数: `id` | `{"status": "success"}` | 从 SQLite 数据库中物理删除报告 |

### 4.2 SSE (Server-Sent Events) 流式推送事件规约

服务端在 `/api/research/stream/{task_id}` 连接上必须按以下 JSON 帧结构广播事件：

* **运行日志帧 (`event: log`)**：
  ```json
  { "message": "正在解析网页: https://...", "timestamp": 1782345620.1 }
  ```
* **核心状态指标更新帧 (`event: state_update`)**：
  ```json
  { "current_depth": 2, "sources_count": 8, "facts_count": 14 }
  ```
* **任务正常结束帧 (`event: complete`)**：
  ```json
  { "report_id": "c1f7a8b9-...", "report": "# 生成的 Markdown 报告正文..." }
  ```
* **异常中断帧 (`event: error`)**：
  ```json
  { "message": "任务执行出错: Tavily API 额度超限" }
  ```
* **心跳保持（保活）**：服务端必须每过 **15 秒** 写入 `: heartbeat\n\n` 的空注释。

### 4.3 数据库模型规约 (SQLite 表结构)

归档历史报告使用 SQLite 进行轻量化异步持久化（通过 `aiosqlite`）：

```sql
CREATE TABLE IF NOT EXISTS reports (
    id TEXT PRIMARY KEY,               -- UUID 字符串 (task_id)
    topic TEXT NOT NULL,               -- 研究课题
    max_depth INTEGER NOT NULL,        -- 设定的探索深度限制
    max_breadth INTEGER NOT NULL,      -- 设定的探索广度限制
    report_content TEXT NOT NULL,      -- Synthesizer 生成的最终 Markdown 报告
    state_json TEXT NOT NULL,          -- 完整序列化的 ResearchState (含 llm_logs, tool_calls)
    created_at TEXT NOT NULL           -- ISO 8601 格式创建时间戳
);
```

---

## 5. 核心控制机制与安全防线 (Guardrails)

脚手架（Harness）通过以下五道物理防线确保智能体在高并发和长时间长连接下的安全性与经济性。

### 5.1 异步递归深度与广度衰减控制
* **深度（Depth）控制**：递归每深入一层，`current_depth` 递增。当 `current_depth > max_depth` 时，强行退出递归。
* **搜索去重机制**：对子查询 query 维护全局 `state.search_history`，抓取前核对 URL 重复性，杜绝智能体在搜索网络中发散出死循环。

### 5.2 全链路可观测性审计追踪 (Observability)
* **工具拦截器**：应用 `@track_tool_call(tool_name)` 拦截装饰器，捕获所有外部搜索、抓取网络 IO 的出入参（Arguments/Output）、执行时间及时间戳，直接追加至 `state.tool_calls`。
* **LLM I/O 日志追踪**：所有对 `GLMClient` 的调用均要求显式传递全局 `state` 句柄，以捕获并持久化 LLM 的原始 Prompt 输入、输出文本及消耗的 token（`state.llm_logs`）。

### 5.3 API 费用审计与软硬双阶段熔断 (Circuit Breaker)
为防止智能体发生失控循环而耗尽 API 余额，系统内嵌双阶段费用熔断器：
1. **预算预判算法**：在进入下一层递归时，依据公式估算未来分支的最大开销：
   $$Cost_{est} = CurrentCost + (Depth_{remaining} \times Breadth \times (Cost_{search} + Cost_{LLM\_extract}))$$
2. **软熔断（已用预算达 75% 时）**：停止派生新的子查询（不继续深入递归），将当前已抓取网页的事实抓取消化完毕后直接进入合成阶段。
3. **硬熔断（已用预算达 100% 时）**：强行中止后续所有的 Scraper 和 Extractor 进程，主循环不发生报错崩溃，而是直接流式推送硬熔断日志，并调用 Synthesizer Agent 基于已有提取的事实笔记，合成并持久化一份**“阶段性报告”**归档，防止已支出的 API Token 彻底被浪费。

### 5.4 并发度隔离与本地双级缓存
* **协程并发度隔离**：Scraper 抓取网页时，必须采用 `asyncio.Semaphore` 限制全局最大并发数（默认为 5），并辅以微小的随机延迟（0.2s - 0.8s），规避目标网站的反爬锁 IP 机制或限额 429。
* **本地双级缓存 (SQLite Cache)**：
  * **搜索缓存表 (`search_cache`)**：以 `md5(query + mode)` 为键，存储 Tavily 返回的结果，有效期 1 天。
  * **网页内容缓存表 (`page_cache`)**：以 `md5(url)` 为键，存储 Jina 清洗过的正文，有效期 7 天。
  * 拦截流程：搜索与抓取调用前先经过拦截器，若命中未过期缓存，返回时间 $<5\text{ms}$ 且费用为 $\$0$。

### 5.5 长连接生命周期管理与孤立任务熔断 (Orphan Task Cleaning)
在前后端联调及真实运行中，由于用户刷新页面、关闭浏览器或网络抖动，长连接可能会断开。
* **前端重连机制**：当网络短暂中断重连时，前端检测到本地 `active_task_id`，自动向 `/api/reports/{id}` 拉取最新快照，重新挂载 SSE 管道，无缝恢复日志拼接。
* **孤立任务（Orphaned Task）回收**：后端 SSE 生成器利用 FastAPI 提供的 `request.is_disconnected()` 侦测客户端物理关闭。一旦网络连接物理断开，立刻注销对应的消息 Queue。
* **物理熔断**：当检查到某活跃任务绑定的**所有监听 Queue 数量归零**，且后台的 `asyncio.Task` 仍在执行时，系统判定该任务为“孤立任务”，立刻调用 `task.cancel()` 触发 `asyncio.CancelledError`，使协程优雅停止运行并释放 HTTP 资源，从而在物理层面彻底拦截因用户离线导致的无意义计费空转。

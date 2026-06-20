# 自动化深度研究智能体 规格说明书索引 (Specifications Index)

本目录包含了深度研究智能体 (Deep Research Agent) 系统的核心规格与设计规范说明书。这些规格说明书规定了系统的底层数据流、业务逻辑、多智能体交互规范以及前端高颜值客户端设计标准。

---

## 规格说明书分类索引

### 1. [后端规格与核心细节 (Backend Specs)](./backend/README.md)
* **[数据状态模型与序列化 (State & Data Models)](./backend/state_models.md)**: 规范 `ResearchState`、`FactNode` 以及日志数据的结构约束与 JSON 序列化规范。
* **[多智能体协作与 Prompt 设计 (Multi-Agent & Prompts)](./backend/multi_agents.md)**: 角色划分、各 Agent 的输入输出边界条件以及集中化提示词配置。
* **[异步递归事件循环机制 (Async Event Loop)](./backend/async_loop.md)**: 探索深度与广度递归衰减逻辑、并发控制与异常处理规约。
* **[审计链路与追踪拦截器 (Logging & Tracing)](./backend/logging_tracing.md)**: 捕获工具调用开销、LLM I/O 运行日志与 Token 审计机制。

---

### 2. [前端高颜值客户端设计规范 (Frontend Specs)](./frontend/specs.md)
* **[磨砂玻璃拟态视觉规范 (Glassmorphism & Theme)](./frontend/specs.md#1-磨砂玻璃拟态视觉规范)**: 定义 Vanilla CSS 核心设计变量、背景渐变、虚化滤镜、发光投影以及微过渡动画设计标准。
* **[探索决策脑图 SVG 渲染规约 (SVG MindMap Rendering)](./frontend/specs.md#2-探索决策脑图-svg-渲染规约)**: 确定树状层级图在 SVG 画布上的坐标映射规则、生长线条动画以及节点状态色彩标识。
* **[流式 SSE 状态管道机制 (SSE Stream Pipeline)](./frontend/specs.md#3-流式-sse-状态管道机制)**: 详细定义浏览器 EventSource 的生命周期、消息类型（log、state_update、complete、error）的路由调度策略，以及浏览器端断线重连、主动熔断与自动资源销毁规约。
* **[Markdown 与学术公式排版 (Markdown & LaTeX Typography)](./frontend/specs.md#4-markdown-与学术公式排版)**: 整合 Marked 引擎、KaTeX 行内与块级公式、引用文献悬浮卡片（Popover）的显示规范，以及打印 PDF A4 学术排版的样式重写。

# 后端核心实现细节与规格说明书 (Product Specs Index)

本目录包含了深度研究智能体 (Deep Research Agent) 后端核心模块的详细技术规格与实现设计。这些文档旨在辅助后续的系统维护、前端对接以及 AI 辅助开发。

---

## 技术规格文档索引

### 1. [数据状态模型与序列化 (State & Data Models)](./state_models.md)
* **核心内容**: 描述 `ResearchState`、`FactNode`、`ToolCallRecord` 以及 `LLMIOLog` 的 Pydantic 模型声明、字段约束和序列化规范。
* **主要目的**: 规范前端与后端状态传输的 JSON Schema，提供事实笔记（Knowledge Graph）和执行日志的数据结构依据。

### 2. [多智能体协作与 Prompt 设计 (Multi-Agent & Prompts)](./multi_agents.md)
* **核心内容**: 介绍多智能体系统（Planner, Searcher, Scraper, Extractor, Synthesizer）的角色划分、输入输出边界，以及位于 `prompts.yaml` 的集中式提示词。
* **主要目的**: 规范大模型对话规范与微调/Prompt 工程优化路径。

### 3. [异步递归事件循环机制 (Async Event Loop)](./async_loop.md)
* **核心内容**: 阐明 `AsyncResearchLoop` 的递归控制算法，包含如何通过 `asyncio.gather` 实现多方向检索与提取的并发控制，以及深度（Depth）和广度（Breadth）的递归衰减逻辑。
* **主要目的**: 规约核心业务流程的执行步骤，提供状态回滚与任务控制机制。

### 4. [审计链路与追踪拦截器 (Logging & Tracing)](./logging_tracing.md)
* **核心内容**: 讲解工具拦截器 `@track_tool_call` 与大模型 I/O 监控记录的设计，说明运行时开销（Token 和响应耗时）是如何自动持久化至全局 State 的。
* **主要目的**: 描述可观测性（Observability）的实现原理，辅助生成完整的 Debug 日志和研究轨迹。

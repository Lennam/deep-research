# 第三阶段：前端高颜值 Web 客户端设计文档

本设计文档针对“自动化深度研究智能体”的第三阶段——**前端高颜值 Web 客户端开发**，详细阐述其系统架构、目录结构、基于纯 Vanilla CSS 的 Glassmorphism（磨砂玻璃）设计系统、核心组件的交互细节、基于 Server-Sent Events (SSE) 的流式状态同步，以及报告预览与导出模块的设计。

---

## 1. 前端项目目录结构

前端项目采用 **Vue 3 (Composition API) + Vite + TypeScript** 架构构建。为了确保样式的极致可控，遵循 Repository 规范，**完全不使用 TailwindCSS 等第三方 CSS 框架**，全部采用原生 Vanilla CSS。

项目目录结构设计如下：

```
frontend/
├── index.html                # 入口 HTML 模板（引入 Google 字体与图标库）
├── package.json              # 项目依赖项配置
├── vite.config.ts            # Vite 构建配置（配置开发服务器反向代理至 FastAPI 后端）
├── tsconfig.json             # TypeScript 编译器配置
├── src/
│   ├── main.ts               # Vue 应用入口点
│   ├── App.vue               # 全局布局主组件
│   ├── assets/
│   │   ├── base.css          # 全局 CSS 重置与排版规范
│   │   └── theme.css         # CSS 变量定义与 Glassmorphism 设计系统
│   ├── components/
│   │   ├── ConfigPanel.vue   # 左侧：任务配置与控制面板
│   │   ├── QueryTree.vue     # 中间：探索查询树（SVG 动态脑图）
│   │   ├── LogConsole.vue    # 中间：实时运行步骤日志控制台
│   │   ├── ReportViewer.vue  # 右侧：Markdown 报告渲染与操作面板
│   │   └── HistoryDrawer.vue # 抽屉：历史研究报告列表与管理
│   ├── composables/
│   │   └── useSSE.ts         # 自定义 Composition Hook（处理 SSE 状态接收与自动重连）
│   ├── types/
│   │   └── index.ts          # 数据模型与状态类型定义（与 Python 后端对齐）
│   └── utils/
│       └── exporter.ts       # 报告文件多格式导出实用工具
```

---

## 2. 全局 CSS 主题系统 (Theme CSS)

为了给用户提供“震撼、奢华、极具科技感”的第一印象，界面样式采用 **暗黑磨砂玻璃拟态 (Dark Glassmorphism)** 风格。

在 `src/assets/theme.css` 中定义全局设计系统变量：

```css
/* src/assets/theme.css */
:root {
  /* 基础配色 */
  --bg-app: linear-gradient(135deg, #0f172a, #020617);
  --color-primary: #38bdf8;       /* 科技蓝 */
  --color-secondary: #34d399;     /* 极光绿 */
  --color-accent: #8b5cf6;        /* 霓虹紫 */
  
  /* 文本颜色 */
  --text-main: #f8fafc;
  --text-muted: #94a3b8;
  --text-dark: #64748b;

  /* 磨砂玻璃的核心变量 */
  --glass-bg: rgba(30, 41, 59, 0.45);
  --glass-bg-hover: rgba(30, 41, 59, 0.6);
  --glass-border: rgba(255, 255, 255, 0.08);
  --glass-border-focused: rgba(56, 189, 248, 0.4);
  --glass-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
  --glass-blur: blur(16px);

  /* 状态颜色 */
  --color-success: #10b981;
  --color-warning: #f59e0b;
  --color-error: #ef4444;
  --color-info: #3b82f6;

  /* 边距与过渡 */
  --radius-lg: 16px;
  --radius-md: 10px;
  --radius-sm: 6px;
  --transition-smooth: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* 玻璃材质基础类 */
.glass-panel {
  background: var(--glass-bg);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--glass-shadow);
  transition: var(--transition-smooth);
}

.glass-panel:hover {
  background: var(--glass-bg-hover);
  border-color: rgba(255, 255, 255, 0.12);
}

/* 交互焦点边框 */
.glass-input {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md);
  color: var(--text-main);
  padding: 10px 14px;
  outline: none;
  transition: var(--transition-smooth);
}

.glass-input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 12px rgba(56, 189, 248, 0.25);
}
```

---

## 3. 核心交互组件详细设计

### 3.1 任务配置与控制面板 ([ConfigPanel.vue](../../frontend/src/components/ConfigPanel.vue))

位于界面左侧，负责接收用户的研究指令并将其发送至后端。

*   **输入项**:
    *   **研究主题**: `textarea` 多行自适应输入框，支持占位提示词，设有最大长度 200 字符限制。
    *   **最大探索深度 (Depth)**: 滑动条 `input[type="range"]`（限制 1 - 5 级，默认 2），提供气泡提示当前级别的搜索意义。
    *   **最大探索广度 (Breadth)**: 滑动条 `input[type="range"]`（限制 1 - 10 级，默认 3），即每次展开子课题的分支数。
    *   **搜索模式选择**: 按钮组切换（`Web 网页搜索` / `Academic 学术数据库` / `All 全能路由模式`）。
*   **控制项**:
    *   **“开始深度探索”按钮**: 点击后调用后端 `POST /api/research/start` 接口，触发 SSE 监听，并将按钮置为 Loading 态（带有渐变光效扩散动画）。
    *   **“强制中止”按钮**: 只有在任务处于 `running` 状态时可见。点击触发 `/api/research/stop/{task_id}` 接口。
*   **状态展示**:
    *   **Token / 费用预估**: 实时显示当前研究所累积消耗的 LLM Tokens 数，并结合估算模型，显示单次研究的消费曲线，提醒费用熔断阈值。

### 3.2 动态探索查询树 ([QueryTree.vue](../../frontend/src/components/QueryTree.vue))

为了给用户提供卓越的“研究脑图”体验，该组件使用 SVG 渲染一个动态展开的树状分支图，显示 Planner Agent 发起的多级子查询如何逐层深入。

*   **实现原理**:
    *   使用 SVG 的 `<g>`, `<line>`, `<circle>` 绘制基于父子节点关系的层级树。
    *   根据 SSE 推送的 `state_update` 消息，在内存中动态维护一个由 `search_history` 和子课题派生组成的树状结构。
    *   使用 CSS `@keyframes` 动画实现新生成的节点由内向外膨胀展现、连线从父节点以动画过渡伸出的动效。
*   **节点状态可视化**:
    *   `Pending`: 灰蓝色小圆圈，代表已排期但未启动。
    *   `Searching`: 蓝绿色呼吸灯闪烁圈，代表 Searcher 正在抓取。
    *   `Scraping`: 橙色波纹圈，代表 Scraper 正在下载网页正文。
    *   `Completed`: 亮绿色，点击该节点可在浮窗中查看该分支已提取的 `FactNode`。

### 3.3 实时运行日志控制台 ([LogConsole.vue](../../frontend/src/components/LogConsole.vue))

以类似 Linux 终端终端的排版形式输出 Agent 的执行步骤和审计日志。

*   **交互特征**:
    *   **自动滚动锚定**: 日志流式传入时，自动滚动到最底端；若用户手动向上滚动浏览，则暂停自动滚动，并右下角浮动提示“↓ 自动追随最新日志”。
    *   **日志过滤分级**: 支持 `Verbose` (包含 LLM 原始 I/O)、`Metrics` (仅工具耗时与 Token)、`State Logs` (步骤描述) 三种日志等级过滤切换。
    *   **代码及 LLM I/O 折叠**: 审计日志中的大模型 Prompt 输入与输出使用 `<details>` 标签包裹，点击可展开高亮渲染，方便开发者调试。

### 3.4 Markdown 报告阅读器 ([ReportViewer.vue](../../frontend/src/components/ReportViewer.vue))

在界面右侧，以最精美舒适的学术论文排版展现 Synthesizer Agent 合成的最终 Markdown 报告。

*   **渲染引擎选择**:
    *   集成 `marked` 库将 Markdown 纯文本实时转译为 HTML DOM。
    *   集成 `KaTeX` 插件，将 Markdown 中包含的行内公式 `$E=mc^2$` 与块公式 `$$...$$` 进行超轻量级、无延迟的数学公式排版渲染。
*   **引用悬浮窗 (Reference Popover)**:
    *   针对文本中的学术或网页引用标志（例如 `[1]`, `[2]`），当鼠标悬浮或移动端点击时，读取对应 `sources` 的 URL、标题与段落摘要，并在该元素下方展示带圆角的磨砂悬浮卡片。
*   **导出操作栏**:
    *   **导出 Markdown**: 将内存中完整的报告原文以 `.md` 格式下载。
    *   **打印为 PDF**: 配置 CSS `@media print` 样式（剔除左侧控制面板与日志背景，保留标准 A4 纸张学术排版），调用浏览器的 `window.print()` 实现无水印 PDF 导出。
    *   **导出 HTML**: 生成包含内嵌样式、KaTeX 离线 CSS 文件的完整 HTML。

---

## 4. SSE (Server-Sent Events) 客户端流式通信设计

前端采用自定义 composable `useSSE.ts` 进行连接管道生命周期管理。

### 4.1 [useSSE.ts](../../frontend/src/composables/useSSE.ts) 实现构想

```typescript
import { ref } from 'vue';
import { ResearchState, LogEvent, StateUpdateEvent } from '../types';

export function useSSE() {
  const isConnecting = ref(false);
  const currentTaskId = ref<string | null>(null);
  const eventSource = ref<EventSource | null>(null);
  
  // 核心状态数据
  const stateLogs = ref<string[]>([]);
  const extractedFactsCount = ref(0);
  const sourcesCount = ref(0);
  const currentDepth = ref(0);
  const finalReport = ref<string>('');
  
  const connectSSE = (taskId: string, onComplete: (report: string) => void, onError: (err: string) => void) => {
    currentTaskId.value = taskId;
    isConnecting.value = true;
    stateLogs.value = [];
    finalReport.value = '';
    
    const sseUrl = `/api/research/stream/${taskId}`;
    eventSource.value = new EventSource(sseUrl);
    
    // 监听步骤运行日志
    eventSource.value.addEventListener('log', (event: any) => {
      const data: LogEvent = JSON.parse(event.data);
      stateLogs.value.push(`[${new Date(data.timestamp * 1000).toLocaleTimeString()}] ${data.message}`);
    });
    
    // 监听全局核心状态指标更新
    eventSource.value.addEventListener('state_update', (event: any) => {
      const data: StateUpdateEvent = JSON.parse(event.data);
      currentDepth.value = data.current_depth;
      sourcesCount.value = data.sources_count;
      extractedFactsCount.value = data.facts_count;
    });
    
    // 监听任务结束
    eventSource.value.addEventListener('complete', (event: any) => {
      const data = JSON.parse(event.data);
      finalReport.value = data.report;
      isConnecting.value = false;
      closeSSE();
      onComplete(data.report);
    });
    
    // 监听异常
    eventSource.value.addEventListener('error', (event: any) => {
      // 区分是服务器主动发出的 error 还是连接断开引发的
      if (event.data) {
        const data = JSON.parse(event.data);
        onError(data.message || '执行出错');
      } else {
        onError('网络流连接意外中断');
      }
      isConnecting.value = false;
      closeSSE();
    });
  };
  
  const closeSSE = () => {
    if (eventSource.value) {
      eventSource.value.close();
      eventSource.value = null;
    }
  };

  return {
    isConnecting,
    currentTaskId,
    stateLogs,
    currentDepth,
    sourcesCount,
    extractedFactsCount,
    finalReport,
    connectSSE,
    closeSSE
  };
}
```

---

## 5. 前端数据模型与类型声明 ([types/index.ts](../../frontend/src/types/index.ts))

为了确保与后端传递的 JSON Schema 严格兼容，前端在 `src/types/index.ts` 中定义相应的 TypeScript interfaces：

```typescript
export interface ToolCallRecord {
  tool_name: string;
  arguments: Record<string, any>;
  output: string;
  timestamp: number;
  duration: number;
}

export interface LLMIOLog {
  agent_name: string;
  prompt_name: string;
  llm_input: string;
  llm_output: string;
  prompt_tokens: number;
  completion_tokens: number;
  timestamp: number;
}

export interface FactNode {
  fact: string;
  evidence: string;
  source_url: string;
  source_title: string;
  sub_topic: string;
}

export interface ResearchState {
  topic: string;
  max_depth: number;
  max_breadth: number;
  current_depth: number;
  sources: Array<{ url: string; title: string; snippet?: string }>;
  extracted_facts: FactNode[];
  search_history: string[];
  tool_calls: ToolCallRecord[];
  llm_logs: LLMIOLog[];
  logs: string[];
}

export interface LogEvent {
  message: string;
  timestamp: number;
}

export interface StateUpdateEvent {
  current_depth: number;
  sources_count: number;
  facts_count: number;
}
```

---

## 6. 前端联调与验证方案

为了确保开发期间前端与后端的对接平滑且具备鲁棒性，第三阶段的验证包含两部分：

### 6.1 前端 Mock 数据脱机测试
为了在后端暂未稳定联调时并行开发前端 UI 特效，编写一个前端 Mock 数据源拦截脚本：
*   **模拟 SSE 连接生成器**: 使用前端定时器（`setInterval`）周期性模拟推送 `log` 事件帧、随机增长的 `sources_count` 和 `facts_count` 指标，以及动态构建 SVG 树的子节点。
*   **报告渲染压力测试**: 预置一份包含超长排版（3万字以上）、数十个三级标题、十余个数学公式块、数百个代码高亮、多级项目符号和大表的 Markdown 报告样例，测试 `ReportViewer.vue` 在 Vue 渲染下的首屏耗时与公式转译流畅度。

### 6.2 前后端整合及高并发联调
*   **反向代理验证**: 运行 Vite 时配置本地代理：
    ```typescript
    // vite.config.ts
    export default defineConfig({
      server: {
        proxy: {
          '/api': {
            target: 'http://127.0.0.1:8000',
            changeOrigin: true
          }
        }
      }
    });
    ```
    验证前端能跨域发起 POST 请求并维持单通道长连接 SSE。
*   **页面生命周期与连接回收检查**:
    *   打开任务递归途中，刷新或关闭浏览器窗口，检查后端后台日志，验证连接断开时，FastAPI 触发清理并使底层 asyncio 任务熔断，防资源泄漏。
    *   在任务进行中，点击“停止”按钮，验证前端主动关闭 `EventSource`，向后端发送 stop 指令，且 UI 重置为就绪态。

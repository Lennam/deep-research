# 第四阶段：系统联调与优化设计文档

本设计文档针对“自动化深度研究智能体”的第四阶段——**系统联调与优化**，详细阐述了前后端全链路联调、长任务生命周期管理、LLM Prompt 调优与事实提取过滤、API 费用追踪与熔断控制，以及并发抓取速率限制与缓存优化等核心设计，旨在打造一个高可用、鲁棒、低成本且产出高质量报告的成熟智能体系统。

---

## 1. 前后端全生命周期联调与稳定性优化

在系统从单模块迈向整体集成的过程中，长时间运行任务（Long-running Tasks，如深层研究通常会持续 1-3 分钟）的通信鲁棒性与资源安全至关重要。

### 1.1 跨域代理与长连接维持
前端 Vite 开发服务器通过代理（Vite Dev Proxy）将 `/api` 请求转发到后端的 FastAPI 服务。

* **心跳保活（Heartbeat）**：SSE（Server-Sent Events）连接由于部分代理网关（如 Nginx、Vite Proxy）的默认超时设置（如 60s），容易发生连接超时断开。后端 SSE 流生成器（Generator）必须每过 15 秒写入一次 `: heartbeat\n\n` 空注释数据以保持长连接。
* **浏览器主动重连与状态对齐**：当网络出现偶发抖动或 Wi-Fi 切换导致连接中断时，前端 `EventSource` 会尝试自动重连。如果重连时任务仍在运行，前端可以使用注册的 `task_id` 向后端轮询获取当前的最新的关键状态，拉取已有的日志并重新挂载 SSE 监听器。

### 1.2 客户端离线时后端的资源清理机制（连接生命周期管理）
若用户关闭浏览器标签页、刷新网页或遭遇物理断网，如果后端继续运行庞大的异步研究循环，将会产生高昂的 LLM 与搜索 API 费用，造成严重浪费。

#### 时序图：连接异常断开时的清理流程
```mermaid
sequenceDiagram
    autonumber
    actor User as 用户浏览器 (Frontend)
    participant Gateway as Vite Proxy / Nginx
    participant API as FastAPI 接口
    participant TM as TaskManager (任务管理器)
    participant Loop as AsyncResearchLoop (后台协程)

    User->>API: 1. POST /api/research/start (启动任务)
    API->>TM: 创建并注册任务 (task_id)
    API->>Loop: 启动后台异步任务 (asyncio.create_task)
    API-->>User: 返回 task_id
    User->>API: 2. GET /api/research/stream/{task_id} (开启 SSE)
    API->>TM: 注册消息队列 (Queue)
    Loop->>TM: 发送研究步骤日志与状态
    TM-->>API: 传输 SSE 消息流
    API-->>User: 持续推送 SSE 数据包

    Note over User, Gateway: 突发事件：用户关闭浏览器 / 刷新 / 网页断网
    User-xGateway: 物理连接关闭
    Gateway-xAPI: TCP Connection Closed 侦测
    API->>TM: 触发异常注销 Queue (unregister_queue)
    API->>TM: 检查该任务是否还有存活的 SSE 监听队列
    Note over TM: 如果监听队列数量归零 (0)
    TM->>Loop: 调用 asyncio.Task.cancel() 触发中止
    Loop->>Loop: 捕获 CancelledError，释放 Jina/Tavily HTTP 客户端
    Loop->>TM: 清理活跃任务列表
    TM->>API: 释放系统资源
```

#### 后端连接关闭处理代码实现（FastAPI Endpoint）
```python
# app/api/research.py
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
import asyncio
from app.core.manager import task_manager

router = APIRouter()

@router.get("/stream/{task_id}")
async def stream_research(task_id: str, request: Request):
    """
    流式传输任务的运行状态。
    通过监听连接状态 (request.is_disconnected())，实现长连接物理断开时的自动熔断与垃圾回收。
    """
    if task_id not in task_manager.active_tasks:
        raise HTTPException(status_code=404, detail="未找到该任务")

    queue = task_manager.register_queue(task_id)

    async def event_generator():
        try:
            while True:
                # 检查客户端是否已断开连接
                if await request.is_disconnected():
                    print(f"[SSE Connection] 客户端断开连接，准备清理 task_id: {task_id}")
                    break
                
                try:
                    # 非阻塞地从队列等待新消息，附带 15s 超时作为心跳保活
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"event: {event['event']}\ndata: {json.dumps(event['data'])}\n\n"
                except asyncio.TimeoutError:
                    # 发送 SSE 心跳注释包，保持连接活跃
                    yield ": heartbeat\n\n"
        finally:
            # 无论何种原因断开（任务结束、客户端离线、异常异常），注销队列
            task_manager.unregister_queue(task_id, queue)
            # 检查若无活跃的 Queue 且任务仍在后台运行，物理中止后台协程
            await task_manager.cancel_task_if_orphaned(task_id)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

---

## 2. LLM Prompts 评测与事实提取质量优化

提示词（Prompts）的优劣直接决定了智能体“规划的深度”以及“报告的学术严谨度”。在第四阶段，需对 `prompts.yaml` 中的各个角色模版做定向调优，并解决事实抽取中的重叠与冲突问题。

### 2.1 提示词优化与微调策略

| Agent 角色 | 原始痛点 | 优化手段与 Prompt 结构微调 |
| :--- | :--- | :--- |
| **Planner** (规划) | 1. 递归产生的子 Query 重复率高；<br>2. 容易偏离用户最初的研究主题。 | 1. 在 Prompt 中注入 **“Search History 列表”**，明令禁止产生相似的短语；<br>2. 限制 Planner 生成 Query 的主题域，使用 Few-Shot 示例约束生成格式。 |
| **Extractor** (事实提取) | 1. 抓取正文较长时，容易凭空虚构原文没有的数据（幻觉）；<br>2. 提取的信息过于碎片化。 | 1. 强力约束：要求每一个事实（Fact）必须严格与原文文本段落（Context Snippet）绑定；<br>2. 优化 Extractor 的 JSON 格式输出，强制返回 `evidence_snippet` 以便前端显示 Popover 时有证可查。 |
| **Synthesizer** (报告合成) | 1. 生成大段 Markdown 时，结构松散；<br>2. 正文中引用的序号 `[1]` 与末尾参考文献无法对应。 | 1. 优化多步骤合成算法：先合成各章节大纲草稿，再分章节逐步扩写；<br>2. 引入 **“引用索引映射机制”**：合成器不再自由命名引用，而是由后端提前建立 Source 字典映射表 `{1: URL1, 2: URL2}` 随 context 传给 LLM，强约束其在正文对应处使用且只使用 `{dict_keys}`。 |

### 2.2 事实提取去重与融合机制
当在不同网页中抓取到多条事实时，往往存在高频的语义重复，或者由于信源不同产生事实冲突。后端需引入去重融合逻辑：

1. **粗筛（Jaccard 相似度）**：对新提取的事实节点与已有提取节点做 N-Gram 文本相似度过滤。如果相似度超 0.75，则直接进入融合分支。
2. **精筛与融合（LLM-based Fact Merge）**：对相似事实节点，调用 Extractor 触发细粒度的合并 Prompt，整合为一条含有多数据源交叉引用的“复合事实节点”（例如合并为 `"大语言模型采用 PagedAttention 能够减少多达 40% 的内存碎片 [1][3]"`，整合两处 `sources` 引用）。

---

## 3. API 消耗控制与费用预算熔断机制

频繁的深度搜索和超长 Token 交互在带来高质量报告的同时，也极易瞬间耗尽用户的 API 余额。系统必须实现精确的计量审计与可设定的熔断机制。

### 3.1 Token 与 API 消耗审计结构
系统需在全局 `ResearchState` 记录每次 LLM 交互的输入/输出 Token 数，以及 Tavily 搜索引擎的请求次数，并转化为实时费用：

```python
# app/core/state.py 扩展字段
class LLMIOLog(BaseModel):
    agent_name: str
    prompt_name: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost: float = 0.0
    timestamp: float

class ResearchState(BaseModel):
    # ... 第一阶段基础状态字段 ...
    # 费用追踪审计
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_search_calls: int = 0
    current_estimated_cost: float = 0.0
    max_cost_budget: float = 1.0  # 硬性预算上限（单位：美元）
    circuit_breaker_triggered: bool = False
```

### 3.2 费用动态估算与预判算法
在递归循环的每一轮迭代开始前，系统依据下列公式估算**下一层深度递归可能产生的最大衍生费用**（$Cost_{est}$）：

$$Cost_{est} = CurrentCost + (Depth_{remaining} \times Breadth \times (Cost_{search} + Cost_{LLM\_extract}))$$

其中：
* $Cost_{search}$ 为单次搜索引擎 API 调用的固定单价。
* $Cost_{LLM\_extract}$ 为拉取网页正文并通过 Extractor 抽取单条事实所消耗的 LLM Token 预估均价。

### 3.3 预算硬熔断与优雅中止（Soft & Hard Circuit Breaker）
当在递归迭代中途检测到费用超支时，采取以下应对策略：

1. **软熔断（Soft Limit）**：当当前已消耗费用达到预设预算的 **75%** 时，向前端推送告警日志（显示为黄色高亮），且停止向更高深度递归，停止生成新的子 Query。只对当前已经抓取回来的网页进行事实抽取。
2. **硬熔断（Hard Limit）**：当费用达到预设预算的 **100%** 时，立刻触发硬熔断。
   * 强行熔断后续的所有 Web Scrape 与 Fact Extract 进程。
   * 后端主循环**不直接抛出异常崩溃**，而是将运行标记置为 `circuit_breaker_triggered=True`，并向 SSE 推送 `"当前任务因触发 API 费用硬熔断，正在整理已有事实，生成阶段性报告..."` 的通知。
   * 调用 Synthesizer Agent，基于目前已经收集到的局部事实与源引用，生成一份“阶段性深度研究报告”，并将其正常保存进 SQLite，确保用户之前付出的 Token 成本仍能换回可用的文字结论。

#### 熔断拦截检测流程伪代码
```python
# app/core/loop.py 中递归执行体内的熔断拦截逻辑
async def process_search_node(self, sub_query: str, current_depth: int):
    # 1. 拦截检查是否已触发硬熔断
    if self.state.current_estimated_cost >= self.state.max_cost_budget:
        self.state.circuit_breaker_triggered = True
        self.log_step(f"🚨 [硬熔断拦截] 当前费用已达上限 ${self.state.current_estimated_cost:.4f}，强行中止搜索进程。")
        return

    # 2. 检查是否触发软熔断：缩减探索范围
    if self.state.current_estimated_cost >= self.state.max_cost_budget * 0.75:
        self.log_step("⚠️ [软熔断提醒] 费用预算即将耗尽，当前递归将不再扩展新的子查询分支。")
        if current_depth > 1:
            return  # 提前返回，不再向下发散递归

    # 3. 扣费计量（模拟搜索调用计费）
    self.state.total_search_calls += 1
    self.state.current_estimated_cost += 0.015  # Tavily 单次查询约 0.015 美元
    
    # 4. 执行真正的搜索与抓取...
    # ...
```

---

## 4. 并发抓取控制与缓存架构优化

多路并行抓取是提升智能体时效性、避免长等待的关键，但如果并发过高，会导致目标站点 IP 封锁或触发 API 的高频限速（Rate Limit）。

### 4.1 速率限制（Rate Limiting & Concurrency Controls）
在 Scraper Agent 批量下载源链接文本时，引入 `asyncio.Semaphore` 进行精细的协程并发度隔离，防止系统因同时开辟上百个 HTTP 连接而被对方服务器判定为 DDoS 攻击：

```python
# app/agents/scraper.py
import asyncio
import httpx

class AsyncScraper:
    def __init__(self, max_concurrent_tasks: int = 5):
        # 限制全局并发抓取数为 5
        self.semaphore = asyncio.Semaphore(max_concurrent_tasks)
        self.client = httpx.AsyncClient(timeout=10.0, follow_redirects=True)

    async def scrape_url(self, url: str) -> str:
        async with self.semaphore:
            # 引入微弱的随机延迟，模拟真实人类浏览行为，规避反爬
            await asyncio.sleep(random.uniform(0.2, 0.8))
            try:
                # 优先尝试 Jina Reader，备用 BeautifulSoup
                response = await self.client.get(f"https://r.jina.ai/{url}")
                if response.status_code == 200:
                    return response.text
                return ""
            except Exception as e:
                print(f"抓取 URL 失败: {url}, 错误: {str(e)}")
                return ""
```

### 4.2 搜索与抓取缓存架构（Cache System）
由于在递归迭代以及相同主题的多轮次优化研究中，极易遇到完全相同的网页 URL 或者完全一致的子搜索 Query，我们设计了一个**轻量级本地 SQLite 缓存服务**（以极低耗能避免重复向第三方支付 API 费用）：

* **缓存表设计**：
  * `search_cache`：以 `md5(query + mode)` 为 Key，存储 Tavily 返回的原始结果 JSON 字符串，设定有效期为 1 天。
  * `page_cache`：以 `md5(url)` 为 Key，存储 Jina Reader 提取清洗后的 Markdown 纯文本，设定有效期为 7 天。

#### 缓存流程结构图
```
[Searcher / Scraper Agent]
          │
          ├── 1. 发起请求 (Query / URL)
          v
+─────────────────────────────────+
|      缓存路由拦截器 (Cache)       |
+────────────────+────────────────+
                 │
                 ├── 2. 命中 (MD5 Key 在 DB 中存在且未过期)
                 │    ├──> [从本地 SQLite 读取缓存结果] ──> 返回数据 (耗时 < 5ms, 费用 $0)
                 │
                 └── 3. 未命中
                      ├──> [请求第三方 API (Tavily/Jina)]
                      ├──> [存入本地 SQLite Cache DB] ───> 返回最新数据 (耗时 > 1s, 产生计费)
```

---

## 5. 联调测试与系统验证方案

为了确认联调阶段各个极端场景下的稳定度与质量，需通过自动化用例与模拟故障进行验证。

### 5.1 自动化集成测试用例

#### 1. 预算超限熔断测试（Circuit Breaker Test）
* **测试方法**：通过单元测试将 `max_cost_budget` 参数人为硬编码设为极低值（如 `0.01` 美元），发起一个对复杂课题的深度搜索请求。
* **预期断言**：
  * 任务没有因为中途停止而崩溃报错；
  * `state.circuit_breaker_triggered` 的值为 `True`；
  * SSE 管道成功发出了提示熔断的 `log` 帧；
  * `reports` 数据库中有一份依据这 0.01 美元预算提取到的少数事实生成的有效 Markdown 报告草稿。

#### 2. 前端重连与任务持久化校验
* **测试方法**：
  1. 开启一个深度为 4 的长任务研究。
  2. 当日志打印到一半时，手动在 Chrome 浏览器中按下 `Cmd + R` 刷新前端页面。
  3. 页面重新加载后，前端侦测到 localStorage 存储的 `active_task_id`，立即向 `/api/reports/{task_id}` 发起状态查询。
* **预期断言**：
  * 后端主循环未中断（在 background 稳定运行）；
  * 前端查询结果显示状态仍为 `running`，并重新拉取 SSE 接口；
  * 终端日志控制台在刷新后能无缝恢复流式日志的拼接，未发生日志丢失或空表情况。

### 5.2 弱网与异常场景黑盒注入测试
* **Tavily API 超时/限频（429 Too Many Requests）模拟**：利用 `pytest-mock` 或在本地代理中拦截 Tavily 网络包，模拟随机抛出 `HTTPStatusError`，检验 Searcher Agent 是否有 `exponential backoff` (指数退避重试，最大重试3次) 逻辑。
* **Jina Reader 反爬/拦截模拟**：模拟 `https://r.jina.ai/` 返回 `403 Forbidden`，检验 Scraper Agent 是否能平滑降级到备用的本地原生 `BeautifulSoup` 抓取解析器，避免因单信源故障导致整个子方向的研究断绝。

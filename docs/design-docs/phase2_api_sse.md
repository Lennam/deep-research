# 第二阶段：FastAPI 接口与实时流推送设计文档

本设计文档针对“自动化深度研究智能体”的第二阶段——**FastAPI 接口与实时流推送**，详细阐述其模块划分、RESTful API 接口定义、Server-Sent Events (SSE) 实时日志流推送方案、基于 SQLite 的历史报告持久化存储，以及多任务管理与熔断机制的设计。

---

## 1. 项目目录结构调整

在第二阶段，我们将基于第一阶段构建的后端 Agent 核心，引入 FastAPI Web 服务框架。整体后端项目目录将扩展如下：

```
backend/
├── app/
│   ├── __init__.py
│   ├── config.py             # 配置管理（新增 DB 路径等配置）
│   ├── main.py               # FastAPI 应用入口与全局异常处理
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py           # 依赖注入项（如数据库连接、密钥验证）
│   │   ├── research.py       # 深度研究控制接口（启动、流推送、停止）
│   │   └── reports.py        # 报告管理接口（列表、详情、删除、导出）
│   ├── prompts/ ...          # 集中化管理的 Prompts 配置（保持不变）
│   ├── search/ ...           # 搜索路由与客户端（保持不变）
│   ├── agents/ ...           # 智能体核心业务类（保持不变）
│   ├── core/
│   │   ├── __init__.py
│   │   ├── state.py          # 状态模型（保持不变）
│   │   ├── loop.py           # 异步循环（微调以支持日志事件通知）
│   │   └── manager.py        # [NEW] 任务管理器 (TaskManager) 与事件总线，控制 SSE 队列
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logger.py
│   │   └── db.py             # [NEW] SQLite 数据库连接及初始化辅助工具
│   └── models/
│       ├── __init__.py
│       └── db_models.py      # [NEW] 数据库 ORM 或数据交互模型
├── requirements.txt          # [MODIFY] 新增 fastapi, uvicorn, sse-starlette, aiosqlite 等依赖
└── tests/
    ├── __init__.py
    ├── test_api.py           # [NEW] REST API 接口测试
    └── test_sse.py           # [NEW] SSE 实时推送流测试
```

---

## 2. API 接口设计与规范

为了让 Vue 3 前端能够平滑地控制研究流程，我们设计了一套符合 REST 规范的 API。

### 2.1 任务控制接口 (Research Controller)

#### 1. 启动研究任务
* **请求路径**: `POST /api/research/start`
* **请求体 (JSON)**:
  ```json
  {
    "topic": "大语言模型智能体状态管理技术现状与发展趋势",
    "max_depth": 3,
    "max_breadth": 2,
    "search_mode": "all" // 可选: "web", "academic", "all"
  }
  ```
* **响应体 (JSON)**:
  ```json
  {
    "task_id": "c1f7a8b9-52e8-4694-ba3d-ffbe1ad4c321",
    "status": "running",
    "message": "研究任务已成功在后台启动"
  }
  ```

#### 2. 实时日志与状态流推送 (SSE)
* **请求路径**: `GET /api/research/stream/{task_id}`
* **请求头**: `Accept: text/event-stream`
* **推送机制**: Server-Sent Events (SSE)。服务端将按行推送 JSON 格式事件，事件类型包括：
  * `log`: 纯文本运行日志，对应控制台步骤。
  * `state_update`: 当前 `ResearchState` 状态的关键指标变化（如当前深度、抓取 URL 数量、事实数量等）。
  * `complete`: 任务正常结束，推送最终的 Markdown 报告与保存记录的 ID。
  * `error`: 任务异常中断，推送错误详情。
* **数据帧样例**:
  ```http
  event: log
  data: {"message": "正在检索: 'LLM agent state'...", "timestamp": 1782345620.1}

  event: state_update
  data: {"current_depth": 2, "sources_count": 8, "facts_count": 14}

  event: complete
  data: {"report_id": "c1f7a8b9-52e8-4694-ba3d-ffbe1ad4c321", "report": "# 深度研究报告..."}
  ```

#### 3. 强制中止研究任务
* **请求路径**: `POST /api/research/stop/{task_id}`
* **响应体 (JSON)**:
  ```json
  {
    "task_id": "c1f7a8b9-52e8-4694-ba3d-ffbe1ad4c321",
    "status": "stopped",
    "message": "研究任务已成功被中止"
  }
  ```

---

### 2.2 报告历史与检索接口 (Report Controller)

所有完成的研究报告和运行时的详细 `ResearchState` 都会归档在 SQLite 数据库中，以供用户随时检索、查阅和下载。

#### 1. 获取报告历史列表
* **请求路径**: `GET /api/reports`
* **响应体 (JSON)**:
  ```json
  [
    {
      "id": "c1f7a8b9-52e8-4694-ba3d-ffbe1ad4c321",
      "topic": "大语言模型智能体状态管理技术现状与发展趋势",
      "max_depth": 3,
      "max_breadth": 2,
      "created_at": "2026-06-20T15:20:00Z",
      "facts_count": 24,
      "sources_count": 12
    }
  ]
  ```

#### 2. 获取单篇报告详情
* **请求路径**: `GET /api/reports/{report_id}`
* **响应体 (JSON)**:
  ```json
  {
    "id": "c1f7a8b9-52e8-4694-ba3d-ffbe1ad4c321",
    "topic": "大语言模型智能体状态管理技术现状与发展趋势",
    "max_depth": 3,
    "max_breadth": 2,
    "created_at": "2026-06-20T15:20:00Z",
    "report_content": "# 深度研究报告\n\n## 1. 引言...",
    "state_json": {
      "topic": "大语言模型智能体状态管理...",
      "max_depth": 3,
      "max_breadth": 2,
      "sources": [...],
      "extracted_facts": [...],
      "tool_calls": [...],
      "llm_logs": [...],
      "logs": [...]
    }
  }
  ```

#### 3. 删除历史报告
* **请求路径**: `DELETE /api/reports/{report_id}`
* **响应体 (JSON)**:
  ```json
  {
    "status": "success",
    "message": "报告已从数据库中物理删除"
  }
  ```

---

## 3. SSE 实时流推送机制实现方案

因为研究循环包含大量网络 I/O，属于典型的 CPU & I/O 密集型异步任务，我们必须把 `AsyncResearchLoop` 放在后台的 `asyncio` Task 中运行。如何在任务后台运行的同时将日志和状态通知发布到处于长连接状态的 SSE 接口？

### 3.1 观察者模式与事件队列流转图

```
+------------------+                   +------------------+                   +------------------+
|   前端 UI 页面   |                   | FastAPI API 服务 |                   |  TaskManager /   |
| (Vue 3 SSE Client)|                  | (Stream Handler) |                   |  Active Tasks    |
+--------+---------+                   +--------+---------+                   +--------+---------+
         |                                      |                                      |
         | 1. POST /api/research/start          |                                      |
         +------------------------------------->+ 2. 创建 task_id                      |
         |                                      |    启动后台异步 Task                 |
         |                                      +------------------------------------->|
         |                                      |    创建消息 Queue 绑定任务           |
         |                                      |                                      |
         | 3. GET /api/research/stream/{id}     |                                      |
         +------------------------------------->+ 4. 监听 task_id 对应的 Queue        |
         |                                      +------------------------------------->|
         |                                      |                                      |
         |                                      |          +---------------------------------------------+
         |                                      |          |         AsyncResearchLoop (后台运行)        |
         |                                      |          +----------------------+----------------------+
         |                                      |                                 |
         |                                      |                                 | 每一次 log_step()
         |                                      |                                 v
         |                                      |                         [Callback Triggered]
         |                                      |                                 |
         |                                      |  5. 消息写入 Queue               |
         |                                      |<--------------------------------+
         |                                      |
         | 6. SSE 格式推送 (text/event-stream)    |
         |<-------------------------------------+
         |
```

### 3.2 TaskManager 实现草案 (`app/core/manager.py`)

`TaskManager` 是核心的状态调度者，维护所有运行中的研究任务、它们对应的 `asyncio.Task` 实例以及用于 SSE 推送的 `asyncio.Queue` 管道列表。

```python
import asyncio
import uuid
from typing import Dict, Tuple, Set, Optional, Callable, Any
from app.core.state import ResearchState

class TaskManager:
    def __init__(self):
        # 结构: { task_id: (asyncio.Task, ResearchState, Set[asyncio.Queue]) }
        self.active_tasks: Dict[str, Tuple[asyncio.Task, ResearchState, Set[asyncio.Queue]]] = {}

    def create_task(self, state: ResearchState) -> str:
        task_id = str(uuid.uuid4())
        # 为当前任务初始化空队列集合
        self.active_tasks[task_id] = (None, state, set())
        return task_id

    def register_queue(self, task_id: str) -> asyncio.Queue:
        """当客户端建立 SSE 连接时，注册一个队列"""
        if task_id not in self.active_tasks:
            raise KeyError("Task not found")
        queue = asyncio.Queue()
        self.active_tasks[task_id][2].add(queue)
        return queue

    def unregister_queue(self, task_id: str, queue: asyncio.Queue):
        """当客户端断开连接时，销毁队列，防止内存泄漏"""
        if task_id in self.active_tasks:
            self.active_tasks[task_id][2].discard(queue)

    def publish_event(self, task_id: str, event_type: str, data: dict):
        """向该任务绑定的所有 SSE 队列广播事件"""
        if task_id not in self.active_tasks:
            return
        _, _, queues = self.active_tasks[task_id]
        payload = {"event": event_type, "data": data}
        for queue in queues:
            queue.put_nowait(payload)

    def associate_async_task(self, task_id: str, task: asyncio.Task):
        """绑定后台运行的 asyncio.Task 对象"""
        if task_id in self.active_tasks:
            _, state, queues = self.active_tasks[task_id]
            self.active_tasks[task_id] = (task, state, queues)

    async def cancel_task(self, task_id: str) -> bool:
        """任务熔断：主动取消 asyncio.Task"""
        if task_id not in self.active_tasks:
            return False
        task, _, _ = self.active_tasks[task_id]
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            return True
        return False

    def remove_task(self, task_id: str):
        """物理清除任务"""
        self.active_tasks.pop(task_id, None)

# 单例模式
task_manager = TaskManager()
```

### 3.3 异步循环的微调改造 (`app/core/loop.py`)

为了将运行日志与状态流式化，我们需要对 `AsyncResearchLoop` 做微弱的功能增强，允许其接收一个回调机制：

```python
class AsyncResearchLoop:
    def __init__(
        self, 
        state: ResearchState, 
        glm_key: str = None, 
        tavily_key: str = None,
        search_mode: str = "auto",
        on_event: Optional[Callable[[str, dict], None]] = None # [NEW] 广播回调
    ):
        # ... 原初始化逻辑 ...
        self.on_event = on_event

    def log_step(self, message: str):
        self.state.logs.append(message)
        print(f"[Agent Loop] {message}")
        
        # 触发回调发送 SSE 数据
        if self.on_event:
            self.on_event("log", {"message": message, "timestamp": time.time()})
            # 同时也触发 state_update 广播当前指标
            self.on_event("state_update", {
                "current_depth": self.state.current_depth,
                "sources_count": len(self.state.sources),
                "facts_count": len(self.state.extracted_facts)
            })
```

---

## 4. 历史报告持久化存储设计 (SQLite & aiosqlite)

为了轻量部署且不依赖庞大的外置 DB，我们选用 Python 自带的 **SQLite** 数据库，并通过 **`aiosqlite`** 提供非阻塞的异步操作。

### 4.1 数据库结构 (Database Schema)

我们将只创建一个单表 `reports`：

| 字段名 | 数据类型 | 约束 | 说明 |
| :--- | :--- | :--- | :--- |
| **id** | VARCHAR(36) | PRIMARY KEY | UUID，代表此篇报告与任务的 ID |
| **topic** | TEXT | NOT NULL | 研究任务的总课题 |
| **max_depth** | INTEGER | NOT NULL | 设定的探索深度限制 |
| **max_breadth** | INTEGER | NOT NULL | 设定的探索广度限制 |
| **report_content** | TEXT | NOT NULL | 生成的完整 Markdown 格式研究报告内容 |
| **state_json** | TEXT | NOT NULL | 序列化后的 `ResearchState` JSON 字符串（包含完整的 `tool_calls` 与 `llm_logs` 审计数据） |
| **created_at** | VARCHAR(25) | NOT NULL | ISO 8601 格式的时间戳 (例如 `2026-06-20T15:20:00Z`) |

### 4.2 数据库连接与查询实现草案 (`app/utils/db.py`)

```python
import aiosqlite
import json
from app.config import settings

DB_PATH = settings.SQLITE_DB_PATH # 比如 "backend/app.db"

async def init_db():
    """初始化数据库表结构"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id TEXT PRIMARY KEY,
                topic TEXT NOT NULL,
                max_depth INTEGER NOT NULL,
                max_breadth INTEGER NOT NULL,
                report_content TEXT NOT NULL,
                state_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        await db.commit()

async def save_report(
    report_id: str, 
    topic: str, 
    max_depth: int, 
    max_breadth: int, 
    report_content: str, 
    state_dict: dict,
    created_at: str
):
    """保存研究报告与状态"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO reports (id, topic, max_depth, max_breadth, report_content, state_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (report_id, topic, max_depth, max_breadth, report_content, json.dumps(state_dict), created_at)
        )
        await db.commit()

async def get_all_reports_meta():
    """检索所有历史报告列表（排除大文本字段，仅供列表展示）"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, topic, max_depth, max_breadth, created_at, state_json FROM reports ORDER BY created_at DESC"
        ) as cursor:
            rows = await cursor.fetchall()
            results = []
            for r in rows:
                state_data = json.loads(r["state_json"])
                results.append({
                    "id": r["id"],
                    "topic": r["topic"],
                    "max_depth": r["max_depth"],
                    "max_breadth": r["max_breadth"],
                    "created_at": r["created_at"],
                    "facts_count": len(state_data.get("extracted_facts", [])),
                    "sources_count": len(state_data.get("sources", []))
                })
            return results

async def get_report_by_id(report_id: str):
    """按照 ID 查询单篇报告详细大字段"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM reports WHERE id = ?", (report_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "id": row["id"],
                    "topic": row["topic"],
                    "max_depth": row["max_depth"],
                    "max_breadth": row["max_breadth"],
                    "report_content": row["report_content"],
                    "state_json": json.loads(row["state_json"]),
                    "created_at": row["created_at"]
                }
            return None
```

---

## 5. 多任务管理与熔断控制机制

为了防止恶意请求、资源无限消耗（例如大模型 API Token 和 Tavily API 配额），以及保证当用户离开页面或点击“中止”时能及时关闭连接：

### 5.1 异步后台任务生命周期设计

当 `POST /api/research/start` 被调用时：
1. 构建 `ResearchState` 和 `AsyncResearchLoop` 对象。
2. 调用 `task_manager.create_task(state)` 生成 `task_id`。
3. 创建后台协程任务：
   ```python
   async def run_research_background(task_id: str, loop_instance: AsyncResearchLoop):
       try:
           # 运行智能体主循环
           report = await loop_instance.run()
           # 任务成功结束，持久化存储
           await save_report(
               report_id=task_id,
               topic=loop_instance.state.topic,
               max_depth=loop_instance.state.max_depth,
               max_breadth=loop_instance.state.max_breadth,
               report_content=report,
               state_dict=loop_instance.state.dict(),
               created_at=datetime.utcnow().isoformat()
           )
           # 广播完成事件
           task_manager.publish_event(task_id, "complete", {"report_id": task_id, "report": report})
       except asyncio.CancelledError:
           # 捕获用户主动取消异常
           task_manager.publish_event(task_id, "error", {"message": "研究任务已被用户中止。"})
       except Exception as e:
           # 捕获未知异常
           task_manager.publish_event(task_id, "error", {"message": f"任务执行出错: {str(e)}"})
       finally:
           # 从活跃任务管理器中移出该任务
           task_manager.remove_task(task_id)

   # 异步启动并绑定
   background_task = asyncio.create_task(run_research_background(task_id, agent_loop))
   task_manager.associate_async_task(task_id, background_task)
   ```

### 5.2 SSE 连接生命周期与资源清理
在 `GET /api/research/stream/{task_id}` 接口中，使用 FastAPI 的 `StreamingResponse` 驱动事件生成器：
* **超时重连 (Heartbeat)**: 每过 15 秒，如果队列中没有新事件，则由生成器向客户端发送一条空注释数据（例如 `: heartbeat\n\n`），保持连接不中断。
* **物理断开**: 当前端 SSE `EventSource.close()` 触发或网络断连引发生成器异常退出时，利用 `finally` 代码块执行 `task_manager.unregister_queue(task_id, queue)`，避免内存泄漏。

---

## 6. 第二阶段测试与验证方案

在第二阶段接口编写完成后，我们将通过以下方式进行自动化和黑盒测试。

### 6.1 单元接口测试 (`tests/test_api.py`)
使用 `FastAPI.testclient` 和 `pytest` 库：
* `test_create_task`: 测试通过 POST 接口成功创建任务，验证返回的 JSON 含有 UUID 格式的 `task_id`。
* `test_get_reports_list`: 测试获取历史记录列表，断言数据排除了体积巨大的 `state_json` 与 `report_content` 字段。
* `test_delete_report`: 测试删除特定 ID 的报告，断言再次获取该 ID 返回 404 错误。

### 6.2 SSE 交互功能校验测试 (`tests/test_sse.py`)
编写独立的异步 HTTP 客户端脚本：
```python
import httpx
import asyncio

async def test_sse():
    async with httpx.AsyncClient() as client:
        # 1. 启动任务
        response = await client.post("http://127.0.0.1:8000/api/research/start", json={
            "topic": "Python 异步测试", "max_depth": 2, "max_breadth": 1
        })
        task_id = response.json()["task_id"]
        
        # 2. 监听流式事件
        async with client.stream("GET", f"http://127.0.0.1:8000/api/research/stream/{task_id}") as stream:
            async for line in stream.iter_lines():
                if line.startswith("data:"):
                    print("收到 SSE 事件帧:", line)
                    if "complete" in line or "error" in line:
                        break
```

### 6.3 异常分支测试与熔断验证
* **网络突变**: 模拟在智能体递归中途关闭 Tavily API 网络通路，验证 `AsyncResearchLoop` 能捕获网络异常并将 `error` 消息推至 SSE 通道，确保系统不崩溃。
* **点击中断**: 调用 `/api/research/stop/{task_id}` 后，检验后台 Task 的 `cancelled()` 属性是否立刻变更为 `True`。

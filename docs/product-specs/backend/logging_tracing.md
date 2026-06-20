# 后端规格说明书: 审计链路与追踪拦截器 (Logging & Tracing)

本规格说明书定义了系统的可观测性 (Observability) 设计，详述了外部工具调用、运行耗时、大模型 I/O 内容以及 Token 消耗的全链路自动追踪技术实现。

---

## 1. 追踪拦截架构

可观测性机制采用 **装饰器拦截 (Decorator Interception)** 与 **显式状态传递 (Explicit Context Passing)** 结合的方式进行：

```
+--------------------------------------------------------------------------------+
|                                智能体执行流                                    |
+--------------------------------------------------------------------------------+
             |                                              |
             | 1. 调用工具 (例如：搜索、网页抓取)              | 2. 调用 LLM (GLM-5.2)
             v                                              v
+----------------------------+                 +----------------------------+
|   @track_tool_call 装饰器   |                 |    GLMClient.chat_completion |
|   - 计时开始                |                 |    - 计时与组装消息        |
|   - 捕获入参/出参           |                 |    - 执行 API 交互        |
|   - 自动追加入 state        |                 |    - 捕获 Token (usage)   |
+----------------------------+                 +----------------------------+
             |                                              |
             +----------------------+-----------------------+
                                    | 统一记录输出
                                    v
+--------------------------------------------------------------------------------+
|                              ResearchState                                     |
|  - state.tool_calls (List[ToolCallRecord])                                     |
|  - state.llm_logs (List[LLMIOLog])                                             |
+--------------------------------------------------------------------------------+
```

---

## 2. 拦截器实现原理与字段规范

### 2.1 工具拦截装饰器 (`track_tool_call`)
工具调用记录用于度量系统各网络 I/O 模块的耗时与健壮性。

* **实现细节**:
  通过定义 `@track_tool_call(tool_name)` 异步装饰器，当智能体方法被执行时，拦截器将：
  1. 获取当前 Unix 时间戳（开始时间）。
  2. 捕获方法的实参（包含位置参数 `args` 与关键字参数 `kwargs`，均转化为字符串以防引用泄露）。
  3. 执行被包装的方法，捕获返回值或异常。
  4. 计算总执行时间（结束时间 - 开始时间）。
  5. 检查调用实例是否具备 `self.state` 属性。若有，自动构建 `ToolCallRecord` 并追加至 `state.tool_calls`。

* **工具记录 JSON 样例**:
  ```json
  {
    "tool_name": "extractor_extract",
    "arguments": {
      "args": ["LLM Agent State", "state management"],
      "kwargs": {"raw_content": "This is raw text..."}
    },
    "output": "[{'fact': 'LLM agents are stateful', 'evidence': 'page 4'}]",
    "timestamp": 1782345610.12,
    "duration": 0.85
  }
  ```

### 2.2 LLM 交互追踪 (`GLMClient.chat_completion`)
为了监控大模型的输入输出，确保数据不被篡改且便于排查幻觉，GLMClient 类被设计为主动接受状态参数：

* **显式上下文传递**:
  所有的 Agent（如 Planner, Extractor）在发起 LLM 对话时，都会主动将自身的 `self.state` 作为关键字参数 `state` 传入 `chat_completion` 方法。
  ```python
  response = await self.client.chat_completion(
      system_prompt=system_prompt,
      user_prompt=user_prompt,
      response_format="json",
      state=self.state,        # 传入状态进行日志埋点
      agent_name="extractor",
      prompt_name="extract_facts"
  )
  ```
  如果传入了 `state`，客户端会在请求成功后：
  1. 解析响应报文中的 Token 使用状况（从 `response.usage` 读取 `prompt_tokens` 与 `completion_tokens`）。
  2. 组装输入源、系统提示词、用户提示词与完整输出内容。
  3. 实例化 `LLMIOLog` 记录，写入 `state.llm_logs`。

* **大模型记录 JSON 样例**:
  ```json
  {
    "agent_name": "extractor",
    "prompt_name": "extract_facts",
    "llm_input": "System:\n你是一个资深的事实提取专家...\n\nUser:\n研究子方向: LLM Agent State...",
    "llm_output": "{\"facts\": [{\"fact\": \"LLM agents are stateful\", \"evidence\": \"page 4\"}]}",
    "timestamp": 1782345610.15,
    "prompt_tokens": 420,
    "completion_tokens": 68
  }
  ```

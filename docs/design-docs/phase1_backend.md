# 第一阶段：后端 Agent 核心设计文档

本设计文档针对“自动化深度研究智能体”的第一阶段——**后端 Agent 核心搭建**，详细阐述其模块划分、接口定义、数据结构、多智能体协同机制以及提示词管理的设计。

---

## 1. 项目目录结构

第一阶段的代码开发将主要集中在 `backend` 文件夹中，其目录结构设计如下：

```
backend/
├── app/
│   ├── __init__.py
│   ├── config.py             # 配置管理（从环境变量加载 API Key 及参数）
│   ├── prompts/
│   │   ├── __init__.py
│   │   ├── prompts.yaml      # 集中化管理的 Prompts 配置
│   │   └── manager.py        # Prompts 读取器与渲染器
│   ├── search/
│   │   ├── __init__.py
│   │   ├── tavily_client.py  # Tavily Web 搜索客户端
│   │   ├── academic_client.py# ArXiv & Semantic Scholar 学术搜索客户端
│   │   └── router.py         # 搜索路由（决定调用 Web 还是学术搜索）
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py           # 智能体基类
│   │   ├── planner.py        # Planner Agent（研究规划、子查询生成与深化）
│   │   ├── scraper.py        # Scraper Agent（网页抓取与清洗）
│   │   ├── extractor.py      # Extractor Agent（事实与笔记提取）
│   │   └── synthesizer.py    # Synthesizer Agent（章节大纲生成与最终报告合成）
│   ├── core/
│   │   ├── __init__.py
│   │   ├── state.py          # 状态模型与日志记录 Pydantic 定义
│   │   └── loop.py           # 自定义轻量级异步事件循环
│   └── utils/
│       ├── __init__.py
│       └── logger.py         # 终端与流式日志辅助工具
├── requirements.txt          # 项目依赖包
└── tests/                    # 测试用例目录
    ├── __init__.py
    ├── test_search.py
    └── test_agents.py
```

---

## 2. 集中化 Prompt 管理 (`prompts.yaml`)

所有的 Prompt 模板存放于统一的 `backend/app/prompts/prompts.yaml` 文件中。基本设计示例如下：

```yaml
# 提示词配置文件

planner:
  system: |
    你是一个专业的研究规划专家。你的任务是分析用户的研究课题，将其拆解为多个互不重复且逻辑严密的研究子方向，并为每个子方向生成最有效的检索关键词。
    使用 JSON 格式输出，格式为：
    {
      "sub_topics": [
        {
          "title": "子方向标题",
          "reason": "拆解该方向的理由",
          "search_queries": ["查询词1", "查询词2"]
        }
      ]
    }
  user: |
    当前研究总课题: {topic}
    最大分支度 (Breadth): {breadth}
    请进行规划。

extractor:
  system: |
    你是一个资深的事实提取专家。你的任务是阅读一段参考文本，围绕给定的研究子方向和查询词，提取出真实、客观、无偏见的事实，并保留原始数据的论据。
    必须剔除所有广告、导航等无关信息。
    使用 JSON 格式输出，格式为：
    {
      "facts": [
        {
          "fact": "提取的事实陈述",
          "evidence": "支持该事实的原文段落/论据",
          "confidence": 0.95
        }
      ]
    }
  user: |
    当前研究子方向: {sub_topic}
    对应的查询词: {query}
    原始网页文本:
    ---
    {raw_content}
    ---
    请提取事实。

synthesizer:
  outline: |
    你是一个科学报告撰写专家。根据搜集到的所有事实笔记和来源，生成一份结构清晰、逻辑顺畅的 Markdown 报告大纲。
    必须包含研究背景、核心发现、各子方向详细对比及结论。
  write_chapter: |
    你是一个学术报告撰写人。请根据提供的“研究子方向”以及所有提取的事实笔记，撰写该章节的内容。
    要求：
    1. 必须使用 Inline 引用格式标注来源，例如 [1], [2]。
    2. 语言严谨，避免空话。
    3. 合并逻辑冲突，去粗取精。
```

`manager.py` 将提供 `PromptManager` 类，通过 `yaml.safe_load` 加载该文件，并提供如 `get_prompt("planner", "system", **kwargs)` 的接口进行参数渲染。

---

## 3. 数据模型设计 (`state.py`)

为了支持 **工具调用记录** 与 **大模型 I/O 日志** 监控，我们使用 Pydantic 规范数据类型：

```python
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Set

class ToolCallRecord(BaseModel):
    """工具（如搜索、网页抓取）调用记录"""
    tool_name: str
    arguments: Dict[str, Any]
    output: str
    timestamp: float
    duration: float

class LLMIOLog(BaseModel):
    """大模型输入与输出日志"""
    agent_name: str
    prompt_name: str
    llm_input: str  # 包含渲染后的 System Prompt 和 User Prompt
    llm_output: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    timestamp: float

class FactNode(BaseModel):
    """提取的事实节点"""
    fact: str
    evidence: str
    source_url: str
    source_title: str
    sub_topic: str

class ResearchState(BaseModel):
    """研究任务全局状态"""
    topic: str
    max_depth: int
    max_breadth: int
    current_depth: int = 0
    
    # 结果数据
    sources: List[Dict[str, Any]] = Field(default_factory=list) # 已搜集的 URL 及摘要元数据
    extracted_facts: List[FactNode] = Field(default_factory=list) # 提取事实库
    search_history: Set[str] = Field(default_factory=set)        # 已搜索过的 Query 集合
    
    # 监控与日志
    tool_calls: List[ToolCallRecord] = Field(default_factory=list)
    llm_logs: List[LLMIOLog] = Field(default_factory=list)
    logs: List[str] = Field(default_factory=list)                # 步骤描述（供前端实时滚动展示）
```

---

## 4. 搜索引擎与学术路由器 (`search/`)

由于只采用 **Tavily API** 与 **学术 API**，搜索模块的逻辑清晰明确。

### 4.1 Tavily 客户端
```python
class TavilySearchClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.endpoint = "https://api.tavily.com/search"

    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        异步调用 Tavily Web 搜索
        返回字段包括：title, url, content, score
        """
        # 实现异步 httpx 请求
```

### 4.2 学术客户端
- **ArXiv SDK**: 使用官方封装的 python 接口，调用异步封装，获取最新的物理/计算机/数学等领域论文。
- **Semantic Scholar API**: 通过 `https://api.semanticscholar.org/graph/v1/paper/search` 检索，获取论文的高价值摘要、引用数与作者列表。

### 4.3 搜索路由
```python
class SearchRouter:
    @staticmethod
    def should_use_academic(query: str) -> bool:
        """
        根据 query 中的关键字或主题属性判断是否应该路由到学术数据库
        """
        academic_keywords = {"algorithm", "neural", "arxiv", "paper", "dataset", "clinical", "mechanism"}
        return any(kw in query.lower() for kw in academic_keywords)
```

---

## 5. 多智能体协作与事件循环 (`core/loop.py`)

智能体系统由一个基于 `asyncio` 的自定义轻量级事件循环驱动。其执行架构如下：

```python
class AsyncResearchLoop:
    def __init__(self, state: ResearchState, api_keys: dict):
        self.state = state
        self.planner = PlannerAgent(api_keys["GLM_KEY"])
        self.searcher = SearcherAgent(api_keys["TAVILY_KEY"])
        self.scraper = ScraperAgent()
        self.extractor = ExtractorAgent(api_keys["GLM_KEY"])
        self.synthesizer = SynthesizerAgent(api_keys["GLM_KEY"])
        
    async def run(self) -> str:
        """运行深度研究主循环"""
        self.log_step("开始研究任务...")
        
        # 1. 第一步：规划器生成子课题大纲
        plan = await self.planner.generate_initial_plan(self.state.topic, self.state.max_breadth)
        self.log_step(f"规划器生成了 {len(plan['sub_topics'])} 个子方向")

        # 2. 深度递归迭代核心逻辑
        await self.recursive_explore(plan["sub_topics"], current_depth=1)
        
        # 3. 合成器合成最终报告
        self.log_step("正在汇总事实笔记并合成报告...")
        report = await self.synthesizer.generate_report(self.state)
        self.log_step("报告合成完成！")
        return report

    async def recursive_explore(self, topics_to_explore: list, current_depth: int):
        """递归深度搜索逻辑"""
        if current_depth > self.state.max_depth:
            return

        self.state.current_depth = current_depth
        tasks = []
        for topic in topics_to_explore:
            tasks.append(self.explore_single_topic(topic, current_depth))
            
        # 并行处理当前深度的各个课题方向
        await asyncio.gather(*tasks)

    async def explore_single_topic(self, topic: dict, depth: int):
        """对单个子课题进行 搜索 -> 抓取 -> 事实提取"""
        for query in topic["search_queries"]:
            if query in self.state.search_history:
                continue
            self.state.search_history.add(query)
            
            # (1) 搜索
            results = await self.searcher.execute(query)
            
            # (2) 并行抓取高价值网页正文并提取事实
            for result in results:
                # 记录工具调用
                url = result["url"]
                raw_content = await self.scraper.scrape(url)
                
                # (3) 提取事实并加入 state.extracted_facts
                facts = await self.extractor.extract(
                    sub_topic=topic["title"], query=query, raw_content=raw_content
                )
                for f in facts:
                    self.state.extracted_facts.append(
                        FactNode(
                            fact=f["fact"],
                            evidence=f["evidence"],
                            source_url=url,
                            source_title=result.get("title", "Unknown"),
                            sub_topic=topic["title"]
                        )
                    )
            
            # (4) 深度启发式拓展 (Depth > 1)
            # 如果深度还没达到上限，可以让 Planner Agent 分析现有的提取结果，
            # 判断是否需要生成更深一层的子查询 (e.g. 挖掘分支细节)
            if depth < self.state.max_depth:
                sub_queries = await self.planner.refine_and_expand(
                    topic=topic["title"], 
                    existing_facts=[f.fact for f in self.state.extracted_facts if f.sub_topic == topic["title"]]
                )
                if sub_queries:
                    new_sub_topics = [{"title": topic["title"], "search_queries": sub_queries}]
                    await self.recursive_explore(new_sub_topics, depth + 1)
```

### 5.1 日志与审计追踪装饰器设计
为了免除在每个智能体内部编写重复的日志记录代码，使用 Python 装饰器（Decorator）或事件发布/订阅模式对 Agent 调用进行拦截：

```python
import time

def track_tool_call(tool_name: str):
    """捕获并记录工具运行性能与输入输出的装饰器"""
    def decorator(func):
        async def wrapper(self, *args, **kwargs):
            start_time = time.time()
            # 记录入参
            arguments = {"args": args, "kwargs": kwargs}
            try:
                result = await func(self, *args, **kwargs)
                output = str(result)[:2000] # 截断避免日志过大
                return result
            except Exception as e:
                output = f"Error: {str(e)}"
                raise e
            finally:
                duration = time.time() - start_time
                # 将记录添加至全局 state.tool_calls
                if hasattr(self, 'state'):
                    self.state.tool_calls.append(ToolCallRecord(
                        tool_name=tool_name,
                        arguments=arguments,
                        output=output,
                        timestamp=start_time,
                        duration=duration
                    ))
        return wrapper
    return decorator
```

---

## 6. 第一阶段测试与验证方案

为了确保后端 Agent 核心在缺乏前端的情况下依旧完全可用，第一阶段将提供 **CLI 交互式沙盒** 和 **自动化测试用例**。

1. **CLI 研究测试脚本 (`test_cli.py`)**:
   - 允许开发者在终端直接输入 Topic、Depth、Breadth、GLM Key 和 Tavily Key。
   - 实时把 `state.logs` 的日志输出至终端。
   - 任务完成后，在控制台将 `state.tool_calls` 以及 `state.llm_logs` 格式化为表格输出，检查调用是否完整。
   - 在本地自动保存生成的 `report.md` 和包含日志的 `state.json`。
2. **PyTest 自动化断言**:
   - 测试 Prompt 模板的渲染正确性。
   - 模拟 Tavily/学术 API 请求，验证 Search Router 能成功路由到正确的搜索引擎。
   - 限制研究任务最大深度为 2，广度为 2，验证递归跳出条件和搜索历史防重机制。

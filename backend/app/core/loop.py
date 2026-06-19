import asyncio
from typing import List, Dict, Any
from app.core.state import ResearchState, FactNode
from app.agents.planner import PlannerAgent
from app.agents.scraper import ScraperAgent
from app.agents.extractor import ExtractorAgent
from app.agents.synthesizer import SynthesizerAgent
from app.search.router import SearchRouter

class AsyncResearchLoop:
    def __init__(
        self, 
        state: ResearchState, 
        glm_key: str = None, 
        tavily_key: str = None,
        search_mode: str = "auto"
    ):
        self.state = state
        self.search_mode = search_mode
        
        # Instantiate agents with shared state for tracking decorators
        from app.core.llm import GLMClient
        custom_client = GLMClient(api_key=glm_key) if glm_key else None
        
        self.planner = PlannerAgent(client=custom_client, state=self.state)
        self.scraper = ScraperAgent()
        self.extractor = ExtractorAgent(client=custom_client, state=self.state)
        self.synthesizer = SynthesizerAgent(client=custom_client, state=self.state)
        self.search_router = SearchRouter(tavily_key=tavily_key)
        
        # To avoid parallel scrapes of same URL
        self.scraped_urls = set()

    def log_step(self, message: str):
        """Logs a status message to the state logs list."""
        self.state.logs.append(message)
        print(f"[Agent Loop] {message}")

    async def run(self) -> str:
        """
        Runs the complete recursive research loop.
        """
        self.log_step(f"开始研究课题: '{self.state.topic}' (最大深度: {self.state.max_depth}, 最大广度: {self.state.max_breadth})")
        
        # 1. Generate initial plan
        self.log_step("正在规划研究大纲...")
        plan = await self.planner.generate_initial_plan(self.state.topic, self.state.max_breadth)
        sub_topics = plan.get("sub_topics", [])
        
        if not sub_topics:
            self.log_step("规划失败，未生成子方向。")
            return "# Research Plan Failed\n\nNo subtopics generated."
            
        self.log_step(f"已确定研究子方向: {[t.get('title') for t in sub_topics]}")
        
        # 2. Recursively explore topics
        await self.explore_topics_recursive(sub_topics, current_depth=1)
        
        # 3. Synthesize final report
        self.log_step("正在合成最终研究报告...")
        report = await self.synthesizer.generate_report(self.state)
        self.log_step("报告合成完成！")
        return report

    async def explore_topics_recursive(self, topics: List[Dict[str, Any]], current_depth: int):
        """
        Explores a list of topics concurrently at the current depth level.
        """
        if current_depth > self.state.max_depth:
            return
            
        self.state.current_depth = current_depth
        self.log_step(f"--- 正在开展深度为 {current_depth} 的研究探讨 ---")
        
        tasks = []
        for topic in topics:
            tasks.append(self.explore_single_topic(topic, current_depth))
            
        await asyncio.gather(*tasks)

    async def explore_single_topic(self, topic: Dict[str, Any], depth: int):
        """
        Explores a single topic: executes searches, scrapes pages, extracts facts, and recursively refines.
        """
        title = topic.get("title", "")
        queries = topic.get("search_queries", [])
        
        self.log_step(f"正在研究方向 [{title}]，拟执行查询: {queries}")
        
        for query in queries:
            if query in self.state.search_history:
                continue
            self.state.search_history.append(query)
            
            # Execute search
            self.log_step(f"正在检索: '{query}' ({self.search_mode} 模式)")
            search_results = await self.search_router.search(
                query, 
                max_results=self.state.max_breadth, 
                mode=self.search_mode
            )
            
            # Record sources (only new ones)
            for r in search_results:
                url = r["url"]
                if not any(s["url"] == url for s in self.state.sources):
                    self.state.sources.append({
                        "title": r.get("title", "Unknown"),
                        "url": url,
                        "content": r.get("content", "")
                    })
            
            # Scrape pages and extract facts in parallel
            scrape_tasks = []
            for r in search_results:
                url = r["url"]
                if url not in self.scraped_urls:
                    self.scraped_urls.add(url)
                    scrape_tasks.append(self.scrape_and_extract_facts(title, query, r))
                    
            if scrape_tasks:
                await asyncio.gather(*scrape_tasks)

        # Deeper recursion (depth-first progression within width limit)
        if depth < self.state.max_depth:
            # Gather facts extracted for this sub-topic
            topic_facts = [
                f.fact for f in self.state.extracted_facts 
                if f.sub_topic == title
            ]
            
            if topic_facts:
                self.log_step(f"正在评估对 [{title}] 方向的了解，决定是否深化...")
                deeper_queries = await self.planner.refine_and_expand(title, topic_facts)
                if deeper_queries:
                    self.log_step(f"决定针对 [{title}] 进一步挖掘: {deeper_queries}")
                    # Build a sub-topic for recursion
                    new_topic = {
                        "title": title,
                        "search_queries": deeper_queries
                    }
                    await self.explore_topics_recursive([new_topic], depth + 1)
                else:
                    self.log_step(f"方向 [{title}] 信息已足够，无需深化。")

    async def scrape_and_extract_facts(self, sub_topic: str, query: str, search_result: Dict[str, Any]):
        """Helper to scrape page and run facts extractor."""
        url = search_result["url"]
        title = search_result.get("title", "Unknown")
        
        self.log_step(f"正在阅读和清洗网页: {url}")
        raw_text = await self.scraper.scrape(url)
        
        if not raw_text.strip():
            self.log_step(f"网页内容为空或下载失败: {url}")
            return
            
        self.log_step(f"正在从网页中提取事实: {url}")
        facts = await self.extractor.extract(sub_topic, query, raw_text)
        
        self.log_step(f"从 {url} 提取到 {len(facts)} 条事实要点")
        for f in facts:
            self.state.extracted_facts.append(FactNode(
                fact=f.get("fact", ""),
                evidence=f.get("evidence", ""),
                source_url=url,
                source_title=title,
                sub_topic=sub_topic
            ))

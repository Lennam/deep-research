import asyncio
import time
from typing import List, Dict, Any, Optional, Callable
from app.config import settings
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
        search_mode: str = "auto",
        on_event: Optional[Callable[[str, dict], None]] = None
    ):
        self.state = state
        self.search_mode = search_mode
        self.on_event = on_event
        
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
        if getattr(self, "on_event", None):
            try:
                self.on_event("log", {"message": message, "timestamp": time.time()})
                self.on_event("state_update", {
                    "current_depth": self.state.current_depth,
                    "sources_count": len(self.state.sources),
                    "facts_count": len(self.state.extracted_facts),
                    "total_prompt_tokens": self.state.total_prompt_tokens,
                    "total_completion_tokens": self.state.total_completion_tokens,
                    "total_search_calls": self.state.total_search_calls,
                    "current_estimated_cost": self.state.current_estimated_cost,
                    "circuit_breaker_triggered": self.state.circuit_breaker_triggered
                })
            except Exception as e:
                print(f"[Agent Loop] Event publishing failed: {e}")

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
            
        # Hard limit check
        if self.state.circuit_breaker_triggered or self.state.current_estimated_cost >= self.state.max_cost_budget:
            self.state.circuit_breaker_triggered = True
            self.log_step(f"🚨 [费用硬熔断] 已达到或超出预算上限 ${self.state.max_cost_budget:.2f}，停止深层递归。")
            return

        # Soft limit check
        if self.state.current_estimated_cost >= self.state.max_cost_budget * 0.75:
            self.log_step(f"⚠️ [费用软熔断] 当前估计费用 ${self.state.current_estimated_cost:.4f} 已达预算的 75%，强行中止递归发散。")
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
            # Hard limit budget check
            if self.state.circuit_breaker_triggered or self.state.current_estimated_cost >= self.state.max_cost_budget:
                self.state.circuit_breaker_triggered = True
                self.log_step("🚨 [费用硬熔断] 达到或超出费用上限，中止当前子方向的搜索。")
                break

            if query in self.state.search_history:
                continue
            self.state.search_history.append(query)
            
            # Execute search
            self.log_step(f"正在检索: '{query}' ({self.search_mode} 模式)")
            
            # Phase 4 cost tracking
            self.state.total_search_calls += 1
            is_academic = (self.search_mode == "academic") or (self.search_mode == "auto" and self.search_router.should_use_academic(query))
            if not is_academic:
                self.state.current_estimated_cost += settings.SEARCH_COST_PER_CALL

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
            # Check circuit breaker before going deeper
            if self.state.circuit_breaker_triggered or self.state.current_estimated_cost >= self.state.max_cost_budget:
                self.state.circuit_breaker_triggered = True
                return

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
        
        # Skip if hard limits hit
        if self.state.circuit_breaker_triggered or self.state.current_estimated_cost >= self.state.max_cost_budget:
            self.state.circuit_breaker_triggered = True
            return

        self.log_step(f"正在阅读和清洗网页 [Query: {query}]: {url}")
        raw_text = await self.scraper.scrape(url)
        
        if not raw_text.strip():
            self.log_step(f"网页内容为空或下载失败 [Query: {query}]: {url}")
            return
            
        # Re-check budget limits before extractor
        if self.state.circuit_breaker_triggered or self.state.current_estimated_cost >= self.state.max_cost_budget:
            self.state.circuit_breaker_triggered = True
            return

        self.log_step(f"正在从网页中提取事实 [Query: {query}]: {url}")
        facts = await self.extractor.extract(sub_topic, query, raw_text)
        
        self.log_step(f"从 {url} 提取到 {len(facts)} 条事实要点 [Query: {query}]")
        
        # Fact de-duplication using Word-level Jaccard similarity
        def jaccard_similarity(s1: str, s2: str) -> float:
            w1 = set(s1.lower().split())
            w2 = set(s2.lower().split())
            if not w1 or not w2:
                return 0.0
            return len(w1 & w2) / len(w1 | w2)

        new_added = 0
        for f in facts:
            fact_text = f.get("fact", "").strip()
            evidence = f.get("evidence", "").strip()
            if not fact_text:
                continue

            # Compare Jaccard similarity with existing facts
            duplicate = False
            for existing in self.state.extracted_facts:
                if jaccard_similarity(fact_text, existing.fact) > 0.6:
                    duplicate = True
                    # Append new source references if not already there
                    if url not in existing.evidence and url != existing.source_url:
                        existing.evidence += f" [Cross-reference: {url}]"
                    break
            
            if not duplicate:
                self.state.extracted_facts.append(FactNode(
                    fact=fact_text,
                    evidence=evidence,
                    source_url=url,
                    source_title=title,
                    sub_topic=sub_topic
                ))
                new_added += 1
                
        self.log_step(f"去重融合后 [Query: {query}]，共新增 {new_added} 条事实，过滤/合并了 {len(facts) - new_added} 条重复事实。")

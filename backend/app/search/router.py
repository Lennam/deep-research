from typing import List, Dict, Any
import asyncio
from app.search.tavily_client import TavilySearchClient
from app.search.academic_client import AcademicSearchClient

class SearchRouter:
    def __init__(self, tavily_key: str = None):
        self.web_client = TavilySearchClient(tavily_key)
        self.academic_client = AcademicSearchClient()

    def should_use_academic(self, query: str) -> bool:
        """
        Determines if a query contains scientific or academic keywords.
        """
        academic_keywords = {
            "algorithm", "neural", "arxiv", "paper", "dataset", "clinical", 
            "mechanism", "benchmark", "quantum", "physics", "theorem", "proof", 
            "experimental", "evaluation", "methodology", "study", "analysis", 
            "performance", "model"
        }
        query_lower = query.lower()
        return any(kw in query_lower for kw in academic_keywords)

    async def search(self, query: str, max_results: int = 5, mode: str = "auto") -> List[Dict[str, Any]]:
        """
        Routes the query to the correct search engine(s) based on the query and search mode.
        Prioritizes checking the local SQLite cache first.
        """
        from app.utils.cache import get_search_cache, set_search_cache
        
        cached_res = await get_search_cache(query, mode)
        if cached_res is not None:
            print(f"[SearchRouter] Cache HIT for query: '{query}' (mode: {mode})")
            return cached_res[:max_results]

        print(f"[SearchRouter] Cache MISS for query: '{query}' (mode: {mode})")

        if mode == "academic":
            results = await self.academic_client.search(query, max_results)
        elif mode == "web":
            results = await self.web_client.search(query, max_results)
        elif mode == "all":
            web_task = self.web_client.search(query, max_results=max_results)
            acad_task = self.academic_client.search(query, max_results=max_results)
            web_res, acad_res = await asyncio.gather(web_task, acad_task)
            
            merged = []
            seen_urls = set()
            for r in acad_res + web_res:
                url = r["url"]
                if url not in seen_urls:
                    seen_urls.add(url)
                    merged.append(r)
            results = merged[:max_results]
        else: # auto
            if self.should_use_academic(query):
                results = await self.academic_client.search(query, max_results)
            else:
                results = await self.web_client.search(query, max_results)
                
        # Cache the results
        await set_search_cache(query, mode, results)
        return results
                
# Singleton instance with default configuration
search_router = SearchRouter()

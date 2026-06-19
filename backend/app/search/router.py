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
        Modes:
            - 'auto': automatically routes to Web or Academic search based on query keywords.
            - 'web': explicitly routes to Tavily Web Search.
            - 'academic': explicitly routes to Academic Search (arXiv + Semantic Scholar).
            - 'all': queries both and merges results.
        """
        if mode == "academic":
            return await self.academic_client.search(query, max_results)
        elif mode == "web":
            return await self.web_client.search(query, max_results)
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
            return merged[:max_results]
        else: # auto
            if self.should_use_academic(query):
                return await self.academic_client.search(query, max_results)
            else:
                return await self.web_client.search(query, max_results)
                
# Singleton instance with default configuration
search_router = SearchRouter()

import httpx
from typing import List, Dict, Any
from app.config import settings

class TavilySearchClient:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.TAVILY_API_KEY
        self.endpoint = "https://api.tavily.com/search"

    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Asynchronously search Tavily.
        
        Returns:
            List of dicts: [{'title': ..., 'url': ..., 'content': ..., 'score': ...}]
        """
        if not self.api_key or self.api_key == "your_tavily_api_key_here":
            # Fallback or error if missing key
            raise ValueError("Tavily API key is missing or not set. Please set TAVILY_API_KEY in .env.")

        payload = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": "basic",
            "max_results": max_results,
            "include_answer": False,
            "include_raw_content": False
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                response = await client.post(self.endpoint, json=payload)
                response.raise_for_status()
                data = response.json()
                
                # Tavily returns results in a 'results' key
                results = data.get("results", [])
                formatted_results = []
                for r in results:
                    formatted_results.append({
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "content": r.get("content", ""),
                        "score": r.get("score", 0.0)
                    })
                return formatted_results
            except Exception as e:
                # Log error or return empty list
                print(f"Error during Tavily search: {e}")
                return []

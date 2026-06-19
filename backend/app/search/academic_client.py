import httpx
import xml.etree.ElementTree as ET
from typing import List, Dict, Any
from urllib.parse import quote

class ArxivClient:
    def __init__(self):
        self.base_url = "http://export.arxiv.org/api/query"

    async def search(self, query: str, max_results: int = 3) -> List[Dict[str, Any]]:
        """Searches arXiv and returns metadata."""
        encoded_query = quote(query)
        url = f"{self.base_url}?search_query=all:{encoded_query}&max_results={max_results}"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                
                # Parse XML response
                root = ET.fromstring(response.text)
                
                # ArXiv XML uses the Atom namespace
                ns = {'atom': 'http://www.w3.org/2005/Atom'}
                
                results = []
                for entry in root.findall('atom:entry', ns):
                    title_elem = entry.find('atom:title', ns)
                    summary_elem = entry.find('atom:summary', ns)
                    id_elem = entry.find('atom:id', ns) # ArXiv URL
                    
                    title = title_elem.text.strip().replace("\n", " ") if title_elem is not None else ""
                    summary = summary_elem.text.strip().replace("\n", " ") if summary_elem is not None else ""
                    url_str = id_elem.text.strip() if id_elem is not None else ""
                    
                    if title:
                        results.append({
                            "title": title,
                            "url": url_str,
                            "content": f"[arXiv Abstract] {summary}",
                            "score": 0.85 # default confidence score for academic papers
                        })
                return results
            except Exception as e:
                print(f"Error searching arXiv: {e}")
                return []


class SemanticScholarClient:
    def __init__(self):
        self.endpoint = "https://api.semanticscholar.org/graph/v1/paper/search"

    async def search(self, query: str, max_results: int = 3) -> List[Dict[str, Any]]:
        """Searches Semantic Scholar and returns paper details."""
        params = {
            "query": query,
            "limit": max_results,
            "fields": "title,url,abstract,citationCount"
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(self.endpoint, params=params)
                if response.status_code == 429:
                    print("Semantic Scholar API rate limited (429).")
                    return []
                response.raise_for_status()
                data = response.json()
                
                papers = data.get("data", [])
                results = []
                for paper in papers:
                    title = paper.get("title", "")
                    url_str = paper.get("url") or f"https://www.semanticscholar.org/paper/{paper.get('paperId')}"
                    abstract = paper.get("abstract") or ""
                    citations = paper.get("citationCount", 0)
                    
                    results.append({
                        "title": title,
                        "url": url_str,
                        "content": f"[Semantic Scholar Abstract] Citation Count: {citations}. Abstract: {abstract}",
                        "score": 0.90
                    })
                return results
            except Exception as e:
                print(f"Error searching Semantic Scholar: {e}")
                return []


class AcademicSearchClient:
    def __init__(self):
        self.arxiv = ArxivClient()
        self.scholar = SemanticScholarClient()

    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Searches both arXiv and Semantic Scholar in parallel, merging results."""
        import asyncio
        
        # Split budget
        arxiv_limit = max_results // 2 + (max_results % 2)
        scholar_limit = max_results // 2
        
        # Parallel query
        arxiv_task = self.arxiv.search(query, max_results=arxiv_limit)
        scholar_task = self.scholar.search(query, max_results=scholar_limit)
        
        arxiv_results, scholar_results = await asyncio.gather(arxiv_task, scholar_task)
        
        # Merge results, scholar first (higher weight)
        merged = []
        seen_urls = set()
        
        for r in scholar_results + arxiv_results:
            url = r["url"]
            if url not in seen_urls:
                seen_urls.add(url)
                merged.append(r)
                
        return merged[:max_results]

import httpx
from bs4 import BeautifulSoup
import re
import asyncio
import random
from app.config import settings

class ScraperAgent:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        # Phase 4 Concurrency limit
        self.semaphore = asyncio.Semaphore(settings.SCRAPER_CONCURRENCY_LIMIT)

    async def scrape(self, url: str) -> str:
        """
        Scrapes a webpage.
        Checks page cache first, controls concurrency with semaphore, and uses micro-delays.
        """
        from app.utils.cache import get_page_cache, set_page_cache
        
        # Check cache
        cached_content = await get_page_cache(url)
        if cached_content is not None:
            print(f"[ScraperAgent] Cache HIT for URL: {url}")
            return cached_content
            
        print(f"[ScraperAgent] Cache MISS for URL: {url}")

        async with self.semaphore:
            # Random micro-delay to prevent rate limiting / bans
            await asyncio.sleep(random.uniform(0.2, 0.8))
            
            # Try Jina Reader
            jina_url = f"https://r.jina.ai/{url}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                try:
                    response = await client.get(jina_url, headers=self.headers)
                    if response.status_code == 200 and response.text.strip():
                        content = response.text.strip()
                        await set_page_cache(url, content)
                        return content
                except Exception as e:
                    print(f"Jina Reader failed for {url}: {e}. Falling back to standard BeautifulSoup scraping.")

                # Fallback BS4 Scraper
                try:
                    response = await client.get(url, headers=self.headers, follow_redirects=True)
                    response.raise_for_status()
                    content = self._clean_html(response.text)
                    if content.strip():
                        await set_page_cache(url, content)
                    return content
                except Exception as e:
                    print(f"Standard scrape failed for {url}: {e}")
                    return ""

    def _clean_html(self, html_content: str) -> str:
        """Cleans HTML content, removing scripts, styles, and returning clean text."""
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Remove script and style elements
        for script in soup(["script", "style", "header", "footer", "nav", "aside"]):
            script.decompose()
            
        # Get text
        text = soup.get_text()
        
        # Break into lines and remove leading/trailing space on each
        lines = (line.strip() for line in text.splitlines())
        # Break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # Drop blank lines
        text_clean = "\n".join(chunk for chunk in chunks if chunk)
        
        # Collapse multiple newlines
        text_clean = re.sub(r'\n+', '\n', text_clean)
        
        return text_clean[:12000] # Limit size to avoid overloading context

import httpx
from bs4 import BeautifulSoup
import re

class ScraperAgent:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    async def scrape(self, url: str) -> str:
        """
        Scrapes a webpage.
        Tries Jina Reader first for markdown conversion.
        Falls back to local httpx + BeautifulSoup parsing.
        """
        # Try Jina Reader
        jina_url = f"https://r.jina.ai/{url}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(jina_url, headers=self.headers)
                if response.status_code == 200 and response.text.strip():
                    return response.text.strip()
            except Exception as e:
                print(f"Jina Reader failed for {url}: {e}. Falling back to standard BeautifulSoup scraping.")

            # Fallback BS4 Scraper
            try:
                response = await client.get(url, headers=self.headers, follow_redirects=True)
                response.raise_for_status()
                return self._clean_html(response.text)
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

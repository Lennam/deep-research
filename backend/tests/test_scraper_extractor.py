import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.agents.scraper import ScraperAgent
from app.agents.extractor import ExtractorAgent

@pytest.mark.asyncio
async def test_scraper_jina_success():
    scraper = ScraperAgent()
    mock_markdown = "# Mocked Clean Jina Content\n\nThis is scraped clean markdown."
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_res = AsyncMock()
        mock_res.status_code = 200
        mock_res.text = mock_markdown
        mock_get.return_value = mock_res
        
        content = await scraper.scrape("https://example.com/testpage")
        assert content == mock_markdown
        # Assert Jina url was queried
        mock_get.assert_called_with("https://r.jina.ai/https://example.com/testpage", headers=scraper.headers)


@pytest.mark.asyncio
async def test_scraper_fallback_to_bs4():
    scraper = ScraperAgent()
    mock_html = """
    <html>
        <head><title>Test Page</title></head>
        <body>
            <nav>Menu Items</nav>
            <div id="content">
                <h1>Main Heading</h1>
                <p>This is the actual page content.</p>
            </div>
            <footer>Footer Links</footer>
        </body>
    </html>
    """
    
    with patch("httpx.AsyncClient.get") as mock_get:
        # First call to Jina fails (500)
        mock_jina_res = AsyncMock()
        mock_jina_res.status_code = 500
        
        # Second call to original page succeeds (200)
        mock_page_res = AsyncMock()
        mock_page_res.status_code = 200
        mock_page_res.text = mock_html
        mock_page_res.raise_for_status = lambda: None
        
        mock_get.side_effect = [mock_jina_res, mock_page_res]
        
        content = await scraper.scrape("https://example.com/testpage")
        
        # Verify nav/footer are cleaned out and only main text remains
        assert "Main Heading" in content
        assert "This is the actual page content." in content
        assert "Menu Items" not in content
        assert "Footer Links" not in content


@pytest.mark.asyncio
async def test_extractor_agent():
    mock_client = AsyncMock()
    mock_client.chat_completion.return_value = '```json\n{"facts": [{"fact": "LLM agents are stateful", "evidence": "page 4 paragraph 2"}]}\n```'
    
    extractor = ExtractorAgent(client=mock_client)
    
    facts = await extractor.extract(
        sub_topic="LLM Agent State",
        query="state management",
        raw_content="This is the raw content containing details about state management in LLM agents."
    )
    
    assert len(facts) == 1
    assert facts[0]["fact"] == "LLM agents are stateful"
    assert facts[0]["evidence"] == "page 4 paragraph 2"
    
    # Assert correct parameters were passed to model
    mock_client.chat_completion.assert_called_once()
    args, kwargs = mock_client.chat_completion.call_args
    assert kwargs["response_format"] == "json"

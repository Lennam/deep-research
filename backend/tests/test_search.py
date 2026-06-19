import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.search.tavily_client import TavilySearchClient
from app.search.academic_client import ArxivClient, SemanticScholarClient, AcademicSearchClient
from app.search.router import SearchRouter

@pytest.mark.asyncio
async def test_tavily_search_mock():
    client = TavilySearchClient(api_key="mock_key")
    
    mock_response = {
        "results": [
            {"title": "Test Web Result", "url": "https://example.com/web", "content": "Sample content", "score": 0.99}
        ]
    }
    
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_res = AsyncMock()
        mock_res.status_code = 200
        mock_res.json = lambda: mock_response  # json() is sync in httpx
        mock_res.raise_for_status = lambda: None # raise_for_status() is sync in httpx
        mock_post.return_value = mock_res
        
        results = await client.search("test query", max_results=1)
        
        assert len(results) == 1
        assert results[0]["title"] == "Test Web Result"
        assert results[0]["url"] == "https://example.com/web"
        assert results[0]["content"] == "Sample content"
        assert results[0]["score"] == 0.99


@pytest.mark.asyncio
async def test_arxiv_client_mock():
    client = ArxivClient()
    mock_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
        <entry>
            <title>Quantum Computing Error Correction</title>
            <summary>This paper discusses error correction in quantum computing.</summary>
            <id>http://arxiv.org/abs/2101.00001v1</id>
        </entry>
    </feed>
    """
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_res = AsyncMock()
        mock_res.status_code = 200
        mock_res.text = mock_xml
        mock_res.raise_for_status = lambda: None
        mock_get.return_value = mock_res
        
        results = await client.search("quantum", max_results=1)
        assert len(results) == 1
        assert results[0]["title"] == "Quantum Computing Error Correction"
        assert "error correction" in results[0]["content"]
        assert results[0]["url"] == "http://arxiv.org/abs/2101.00001v1"


@pytest.mark.asyncio
async def test_semantic_scholar_client_mock():
    client = SemanticScholarClient()
    mock_json = {
        "data": [
            {
                "title": "A Survey of LLM Agents",
                "url": "https://example.com/scholar",
                "abstract": "Survey abstract text.",
                "citationCount": 42,
                "paperId": "abcdef12345"
            }
        ]
    }
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_res = AsyncMock()
        mock_res.status_code = 200
        mock_res.json = lambda: mock_json  # json() is sync in httpx
        mock_res.raise_for_status = lambda: None
        mock_get.return_value = mock_res
        
        results = await client.search("LLM agents", max_results=1)
        assert len(results) == 1
        assert results[0]["title"] == "A Survey of LLM Agents"
        assert "42" in results[0]["content"]
        assert results[0]["url"] == "https://example.com/scholar"


def test_search_router_classification():
    router = SearchRouter(tavily_key="mock_key")
    
    # Academic keywords
    assert router.should_use_academic("quantum physics algorithm paper") is True
    assert router.should_use_academic("dataset performance evaluation benchmark") is True
    
    # Web keywords
    assert router.should_use_academic("latest tech news stock price apple") is False
    assert router.should_use_academic("weather forecast today") is False


@pytest.mark.asyncio
async def test_search_router_routing():
    router = SearchRouter(tavily_key="mock_key")
    
    # Mock calls
    router.web_client.search = AsyncMock(return_value=[{"title": "Web", "url": "web", "content": "W", "score": 0.5}])
    router.academic_client.search = AsyncMock(return_value=[{"title": "Acad", "url": "acad", "content": "A", "score": 0.9}])
    
    # Auto route to academic
    res_acad = await router.search("neural networks dataset study", mode="auto")
    router.academic_client.search.assert_called_once()
    assert res_acad[0]["title"] == "Acad"
    
    # Auto route to web
    res_web = await router.search("latest news", mode="auto")
    router.web_client.search.assert_called_once()
    assert res_web[0]["title"] == "Web"

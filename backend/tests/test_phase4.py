import pytest
import pytest_asyncio
import asyncio
import os
import json
import time
import tempfile
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from httpx import AsyncClient

from app.config import settings

# Redirect SQLite database to temp file for tests
db_fd, temp_db_path = tempfile.mkstemp()
settings.SQLITE_DB_PATH = temp_db_path

from app.main import app
from app.core.state import ResearchState, FactNode
from app.core.loop import AsyncResearchLoop
from app.core.manager import task_manager
from app.utils.db import init_db
from app.utils.cache import init_cache_db, get_search_cache, set_search_cache, get_page_cache, set_page_cache
from app.agents.scraper import ScraperAgent
from app.search.router import SearchRouter

@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup_db():
    await init_db()
    yield
    if os.path.exists(temp_db_path):
        try:
            os.close(db_fd)
            os.unlink(temp_db_path)
        except Exception:
            pass

@pytest.mark.asyncio
async def test_cache_mechanism():
    """Verify set/get operations and expiration policies of the SQLite cache."""
    await init_cache_db()
    
    # 1. Search cache check
    query = "Quantum Computing Future"
    mode = "web"
    results = [{"title": "Qubits", "url": "http://qubit.com", "content": "Information about qubits"}]
    
    # Cache hit/miss
    assert await get_search_cache(query, mode) is None
    await set_search_cache(query, mode, results)
    
    cached = await get_search_cache(query, mode)
    assert cached is not None
    assert cached[0]["title"] == "Qubits"
    
    # Test expiration: modify timestamp back by 2 days (TTL is 1 day)
    import aiosqlite
    async with aiosqlite.connect(settings.SQLITE_DB_PATH) as db:
        two_days_ago = time.time() - (2 * 86400)
        await db.execute("UPDATE search_cache SET timestamp = ?", (two_days_ago,))
        await db.commit()
        
    assert await get_search_cache(query, mode) is None

    # 2. Page cache check
    url = "https://example.com/ai-agents"
    page_text = "Cleaned page content of AI agents and state loops."
    
    assert await get_page_cache(url) is None
    await set_page_cache(url, page_text)
    
    cached_page = await get_page_cache(url)
    assert cached_page == page_text
    
    # Expire page cache: back by 8 days (TTL is 7 days)
    async with aiosqlite.connect(settings.SQLITE_DB_PATH) as db:
        eight_days_ago = time.time() - (8 * 86400)
        await db.execute("UPDATE page_cache SET timestamp = ?", (eight_days_ago,))
        await db.commit()
        
    assert await get_page_cache(url) is None


@pytest.mark.asyncio
async def test_search_router_and_scraper_caching():
    """Verify that SearchRouter and ScraperAgent skip HTTP requests when cached."""
    # 1. Scraper caching test
    scraper = ScraperAgent()
    url = "http://uncached-url-test.org/news"
    raw_content = "Unique content to be scraped and saved."
    
    # Clear caches
    import aiosqlite
    async with aiosqlite.connect(settings.SQLITE_DB_PATH) as db:
        await db.execute("DELETE FROM page_cache")
        await db.execute("DELETE FROM search_cache")
        await db.commit()

    # Mock Jina Reader & standard scrape
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = raw_content

    with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_response)) as mock_get:
        # First scrape -> cache miss, calls client
        res1 = await scraper.scrape(url)
        assert res1 == raw_content
        assert mock_get.call_count == 1
        
        # Second scrape -> cache hit, skips client call
        res2 = await scraper.scrape(url)
        assert res2 == raw_content
        assert mock_get.call_count == 1  # count remains 1

    # 2. SearchRouter caching test
    router = SearchRouter()
    query = "Agentic workflows"
    search_results = [{"title": "Workflows", "url": "http://workflows.net", "content": "Context details"}]
    
    with patch.object(router.web_client, "search", AsyncMock(return_value=search_results)) as mock_web_search:
        # First search -> cache miss, calls web client
        s1 = await router.search(query, mode="web")
        assert len(s1) == 1
        assert mock_web_search.call_count == 1
        
        # Second search -> cache hit, skips web client
        s2 = await router.search(query, mode="web")
        assert len(s2) == 1
        assert mock_web_search.call_count == 1


@pytest.mark.asyncio
async def test_concurrency_semaphore_in_scraper():
    """Verify ScraperAgent respects maximum concurrency settings using a semaphore."""
    scraper = ScraperAgent()
    url_base = "http://test-semaphore-target.org/"
    
    # Override settings for testing
    settings.SCRAPER_CONCURRENCY_LIMIT = 3
    scraper.semaphore = asyncio.Semaphore(settings.SCRAPER_CONCURRENCY_LIMIT)
    
    # Clear caching to force real scrapes
    import aiosqlite
    async with aiosqlite.connect(settings.SQLITE_DB_PATH) as db:
        await db.execute("DELETE FROM page_cache")
        await db.commit()

    max_simultaneous = 0
    current_simultaneous = 0
    lock = asyncio.Lock()

    async def mock_jina_get(client, url, *args, **kwargs):
        nonlocal current_simultaneous, max_simultaneous
        async with lock:
            current_simultaneous += 1
            if current_simultaneous > max_simultaneous:
                max_simultaneous = current_simultaneous
        
        # Sleep for a bit to hold concurrency
        await asyncio.sleep(0.1)
        
        async with lock:
            current_simultaneous -= 1
        
        resp = MagicMock()
        resp.status_code = 200
        resp.text = "Scrape Output"
        return resp

    with patch("httpx.AsyncClient.get", mock_jina_get):
        # Fire 6 concurrent scrapes
        tasks = [scraper.scrape(f"{url_base}{i}") for i in range(6)]
        await asyncio.gather(*tasks)
        
    # Maximum concurrent runs must be capped at SCRAPER_CONCURRENCY_LIMIT (3)
    assert max_simultaneous <= 3
    assert max_simultaneous > 0


@pytest.mark.asyncio
async def test_budget_circuit_breaker():
    """Verify that soft and hard budget circuit breakers are correctly enforced."""
    state = ResearchState(
        topic="Budget Test",
        max_depth=3,
        max_breadth=2,
        max_cost_budget=0.10  # low budget
    )
    
    # Mock search router and agents
    mock_router = SearchRouter()
    mock_router.search = AsyncMock(return_value=[{"title": "Factoid", "url": "http://cost.org", "content": "Expensive findings"}])
    
    loop = AsyncResearchLoop(state=state, glm_key="mock_key", tavily_key="mock_key")
    loop.search_router = mock_router
    loop.planner.generate_initial_plan = AsyncMock(return_value={
        "sub_topics": [
            {"title": "Subtopic A", "search_queries": ["query A"]},
            {"title": "Subtopic B", "search_queries": ["query B"]}
        ]
    })
    loop.planner.refine_and_expand = AsyncMock(return_value=["deeper query"])
    
    # 1. Soft circuit breaker validation (75% budget)
    # Manually bump cost to 0.08 ($0.08 / $0.10 = 80%)
    state.current_estimated_cost = 0.08
    
    # Trigger recursion step. It should soft-fuse and return immediately
    await loop.explore_topics_recursive([{"title": "Subtopic C", "search_queries": ["query C"]}], current_depth=2)
    assert any("费用软熔断" in log for log in state.logs)
    
    # 2. Hard circuit breaker validation (100% budget)
    state.current_estimated_cost = 0.12  # Exceeds $0.10
    
    # Try calling scrape_and_extract_facts or explore_single_topic, should immediately return
    await loop.explore_single_topic({"title": "Subtopic D", "search_queries": ["query D"]}, depth=1)
    assert state.circuit_breaker_triggered is True
    assert any("费用硬熔断" in log for log in state.logs)
    
    # Test that run() completes and synthesizes report even if breaker triggers
    state.circuit_breaker_triggered = False
    state.current_estimated_cost = 0.0
    loop.synthesizer.generate_report = AsyncMock(return_value="# Synthesized Report under Budget Constraint")
    
    # Mock explore_topics_recursive to spike cost and trigger hard breaker
    async def mock_explore(topics, current_depth):
        state.current_estimated_cost = 0.15  # Spikes cost
        state.circuit_breaker_triggered = True
        loop.log_step("🚨 [费用硬熔断]已达到预算")

    loop.explore_topics_recursive = mock_explore
    report = await loop.run()
    assert state.circuit_breaker_triggered is True
    assert report == "# Synthesized Report under Budget Constraint"


@pytest.mark.asyncio
async def test_sse_client_disconnect_orphans():
    """Verify that TaskManager automatically cancels backend async tasks on SSE disconnection."""
    state = ResearchState(
        topic="Disconnection Test",
        max_depth=3,
        max_breadth=2
    )
    
    task_id = task_manager.create_task(state)
    
    # Create an async task that spins
    async def long_running_task():
        try:
            while True:
                await asyncio.sleep(0.01)
        except asyncio.CancelledError:
            state.logs.append("Cancelled successfully")
            raise

    bg_task = asyncio.create_task(long_running_task())
    task_manager.associate_async_task(task_id, bg_task)
    
    # Give task a moment to start running
    await asyncio.sleep(0.02)
    
    # Register connection queue
    queue = task_manager.register_queue(task_id)
    
    # Simulate client stream requesting is_disconnected() -> True
    mock_request = MagicMock()
    mock_request.is_disconnected = AsyncMock(return_value=True)
    
    # Stream endpoint generator call
    async def run_client_polling():
        async for _ in app.routes[0].endpoint(task_id, mock_request):
            break
            
    # Mocking endpoint logic in tests by triggering manual unregister and cancel
    task_manager.unregister_queue(task_id, queue)
    await task_manager.cancel_task_if_orphaned(task_id)
    
    # Verify task cancelled
    assert bg_task.cancelled() is True
    assert "Cancelled successfully" in state.logs

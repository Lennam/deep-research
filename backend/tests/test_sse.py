import pytest
import pytest_asyncio
import asyncio
import json
import os
import tempfile
import httpx
from unittest.mock import patch
from httpx import AsyncClient

from app.config import settings

# Route temporary SQLite file for testing
db_fd, temp_db_path = tempfile.mkstemp()
settings.SQLITE_DB_PATH = temp_db_path

from app.main import app
from app.core.loop import AsyncResearchLoop
from app.utils.db import init_db

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
async def test_research_start_and_sse_flow():
    async def mock_run(self):
        self.log_step("Mock Loop: Starting planning phase...")
        await asyncio.sleep(0.05)
        self.log_step("Mock Loop: Crawling web contents...")
        await asyncio.sleep(0.05)
        self.log_step("Mock Loop: Compiling final summary report...")
        return "# Mocked Deep Research Report Markdown"

    with patch.object(AsyncResearchLoop, "run", mock_run):
        async with AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            # 1. Post to start research
            response = await client.post("/api/research/start", json={
                "topic": "Quantum Encryption Mock",
                "max_depth": 2,
                "max_breadth": 1,
                "search_mode": "all"
            })
            assert response.status_code == 200
            start_data = response.json()
            assert start_data["status"] == "running"
            task_id = start_data["task_id"]
            assert task_id != ""

            # 2. Consume from the SSE event stream
            sse_events = []
            async with client.stream("GET", f"/api/research/stream/{task_id}") as stream_resp:
                assert stream_resp.status_code == 200
                async for line in stream_resp.aiter_lines():
                    if line.startswith("data:"):
                        payload = json.loads(line[5:].strip())
                        sse_events.append(payload)
            
            # 3. Assert events are successfully streamed and logged
            assert len(sse_events) > 0
            
            # Check logs contain loop steps
            log_messages = [ev["message"] for ev in sse_events if "message" in ev]
            assert any("Mock Loop: Starting planning" in msg for msg in log_messages)
            assert any("Mock Loop: Crawling web" in msg for msg in log_messages)
            
            # Check there is a final complete event containing report
            complete_events = [ev for ev in sse_events if "report" in ev]
            assert len(complete_events) == 1
            assert complete_events[0]["report"] == "# Mocked Deep Research Report Markdown"

@pytest.mark.asyncio
async def test_research_stop_and_abort():
    async def mock_run_long(self):
        self.log_step("Mock Long: Running part 1...")
        await asyncio.sleep(1.0)
        self.log_step("Mock Long: Running part 2...")
        await asyncio.sleep(1.0)
        return "# Report Done"

    with patch.object(AsyncResearchLoop, "run", mock_run_long):
        async with AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            # 1. Start long research task
            response = await client.post("/api/research/start", json={
                "topic": "Abort Test Topic",
                "max_depth": 3,
                "max_breadth": 2
            })
            assert response.status_code == 200
            task_id = response.json()["task_id"]

            # Let it spin briefly
            await asyncio.sleep(0.05)

            # 2. Stop the task
            stop_response = await client.post(f"/api/research/stop/{task_id}")
            assert stop_response.status_code == 200
            assert stop_response.json()["status"] == "stopped"

            # 3. Verify it's no longer actively streaming or raises user abort in stream
            sse_events = []
            async with client.stream("GET", f"/api/research/stream/{task_id}") as stream_resp:
                async for line in stream_resp.aiter_lines():
                    if line.startswith("data:"):
                        payload = json.loads(line[5:].strip())
                        sse_events.append(payload)

            # The final event streamed should contain abort / error information
            assert len(sse_events) > 0
            assert any("已被用户中止" in ev["message"] for ev in sse_events if "message" in ev)

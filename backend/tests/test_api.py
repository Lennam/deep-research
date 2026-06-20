import pytest
import os
import tempfile
from fastapi.testclient import TestClient
import pytest_asyncio
from app.config import settings

# Route temporary SQLite file for testing
db_fd, temp_db_path = tempfile.mkstemp()
settings.SQLITE_DB_PATH = temp_db_path

from app.main import app
from app.utils.db import init_db, save_report

client = TestClient(app)

@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup_db():
    await init_db()
    yield
    # Cleanup DB file after test runs
    if os.path.exists(temp_db_path):
        try:
            os.close(db_fd)
            os.unlink(temp_db_path)
        except Exception:
            pass

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

@pytest.mark.asyncio
async def test_reports_crud():
    report_id = "test-report-uuid-123"
    await save_report(
        report_id=report_id,
        topic="Test Research Topic API",
        max_depth=2,
        max_breadth=1,
        report_content="# Summary Report\n\nThis is a mock report content.",
        state_dict={
            "topic": "Test Research Topic API",
            "max_depth": 2,
            "max_breadth": 1,
            "sources": [{"title": "Source 1", "url": "http://example.com"}],
            "extracted_facts": [],
            "tool_calls": [],
            "llm_logs": [],
            "logs": ["Task started", "Finished mock save"]
        },
        created_at="2026-06-20T12:00:00Z"
    )

    # 1. Test fetching list
    response = client.get("/api/reports")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["id"] == report_id
    assert data[0]["topic"] == "Test Research Topic API"
    assert data[0]["sources_count"] == 1
    assert data[0]["facts_count"] == 0

    # 2. Test fetching detailed report
    response = client.get(f"/api/reports/{report_id}")
    assert response.status_code == 200
    detail = response.json()
    assert detail["id"] == report_id
    assert detail["report_content"] == "# Summary Report\n\nThis is a mock report content."
    assert "state_json" in detail
    assert detail["state_json"]["logs"][0] == "Task started"

    # 3. Test deleting report
    response = client.delete(f"/api/reports/{report_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Fetching details again should yield 404
    response = client.get(f"/api/reports/{report_id}")
    assert response.status_code == 404

    # Deleting missing report should yield 404
    response = client.delete(f"/api/reports/{report_id}")
    assert response.status_code == 404

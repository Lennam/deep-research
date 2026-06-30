import pytest
import os
import tempfile
import asyncio
from unittest.mock import AsyncMock, MagicMock
from app.utils.vector_store import chunk_markdown, cosine_similarity, SQLiteVectorStore
from app.core.llm import LLMClient
from app.config import settings

def test_cosine_similarity():
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    assert abs(cosine_similarity(v1, v2) - 1.0) < 1e-6

    v3 = [0.0, 1.0, 0.0]
    assert abs(cosine_similarity(v1, v3) - 0.0) < 1e-6

    v4 = [1.0, 1.0, 0.0]
    # Cosine distance: 1 / sqrt(2) = ~0.7071
    assert abs(cosine_similarity(v1, v4) - 0.7071) < 0.01

    assert cosine_similarity([], []) == 0.0
    assert cosine_similarity([1.0], [1.0, 2.0]) == 0.0

def test_chunk_markdown():
    text = "Paragraph 1\n\nParagraph 2\n\nParagraph 3"
    chunks = chunk_markdown(text, chunk_size=20, overlap=5)
    assert len(chunks) == 3
    assert "Paragraph 1" in chunks[0]
    assert "Paragraph 2" in chunks[1]
    assert "Paragraph 3" in chunks[2]

    huge_text = "A" * 100
    chunks_huge = chunk_markdown(huge_text, chunk_size=30, overlap=10)
    assert len(chunks_huge) > 1

@pytest.mark.asyncio
async def test_sqlite_vector_store():
    # Use a temporary file for the database path in testing
    fd, temp_db_path = tempfile.mkstemp()
    try:
        os.close(fd)
        store = SQLiteVectorStore(db_path=temp_db_path)
        await store.init_db()

        task_id = "test-task-123"
        texts = ["Python is a programming language", "Apple is a red fruit", "The sky is blue"]
        metadatas = [{"tag": "coding"}, {"tag": "fruit"}, {"tag": "nature"}]
        embeddings = [
            [0.9, 0.1, 0.0],
            [0.1, 0.9, 0.0],
            [0.0, 0.1, 0.9]
        ]

        await store.add_documents(task_id, texts, metadatas, embeddings)

        # Search for "Python coding" similar to [0.9, 0.1, 0.0]
        results = await store.similarity_search(task_id, [0.8, 0.2, 0.0], k=2)
        assert len(results) == 2
        assert "Python" in results[0]["text"]
        assert results[0]["metadata"]["tag"] == "coding"
        assert results[0]["similarity"] > 0.9

        # Search for non-existent task_id
        empty_results = await store.similarity_search("other-task", [0.8, 0.2, 0.0], k=2)
        assert len(empty_results) == 0

    finally:
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)

@pytest.mark.asyncio
async def test_llm_client_embeddings():
    client = LLMClient(api_key="mock-key")
    mock_embeddings = MagicMock()
    mock_data = [MagicMock(embedding=[0.1, 0.2, 0.3])]
    mock_embeddings.create.return_value = MagicMock(data=mock_data)
    client.client = MagicMock()
    client.client.embeddings = mock_embeddings

    emb = await client.get_embedding("Hello world")
    assert emb == [0.1, 0.2, 0.3]
    mock_embeddings.create.assert_called_once()

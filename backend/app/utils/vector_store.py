import aiosqlite
import json
import math
import uuid
from typing import List, Dict, Any, Optional
from app.config import settings

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Computes cosine similarity between two float vectors."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot_product = sum(x * y for x, y in zip(v1, v2))
    norm_v1 = math.sqrt(sum(x * x for x in v1))
    norm_v2 = math.sqrt(sum(y * y for y in v2))
    if norm_v1 == 0.0 or norm_v2 == 0.0:
        return 0.0
    return dot_product / (norm_v1 * norm_v2)

def chunk_markdown(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Chunks Markdown text into coherent chunks, trying to split on paragraph boundaries
    (double newlines) or line boundaries when possible.
    """
    if not text:
        return []
    
    if len(text) <= chunk_size:
        return [text]

    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = []
    current_length = 0

    for paragraph in paragraphs:
        if len(paragraph) > chunk_size:
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_length = 0
            
            start = 0
            while start < len(paragraph):
                end = start + chunk_size
                chunks.append(paragraph[start:end])
                start += (chunk_size - overlap)
        else:
            if current_length + len(paragraph) + 2 > chunk_size:
                chunks.append("\n\n".join(current_chunk))
                overlap_chunk = []
                overlap_len = 0
                for p in reversed(current_chunk):
                    if overlap_len + len(p) + 2 <= overlap:
                        overlap_chunk.insert(0, p)
                        overlap_len += len(p) + 2
                    else:
                        break
                current_chunk = overlap_chunk
                current_length = overlap_len
            
            current_chunk.append(paragraph)
            current_length += len(paragraph) + 2
            
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))
        
    return chunks

class SQLiteVectorStore:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.SQLITE_DB_PATH

    async def init_db(self):
        """Initializes the vector store database table and index."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS document_embeddings (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    text TEXT NOT NULL,
                    embedding TEXT NOT NULL,
                    metadata TEXT NOT NULL
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_embeddings_task 
                ON document_embeddings(task_id)
            """)
            await db.commit()

    async def add_documents(
        self, 
        task_id: str, 
        texts: List[str], 
        metadatas: List[Dict[str, Any]], 
        embeddings: List[List[float]]
    ):
        """Inserts documents and their corresponding embedding vectors."""
        if not texts or not embeddings or len(texts) != len(embeddings):
            return
        
        # Ensure metadata is available for each text
        if not metadatas:
            metadatas = [{} for _ in texts]
        elif len(metadatas) < len(texts):
            metadatas = list(metadatas) + [{} for _ in range(len(texts) - len(metadatas))]

        async with aiosqlite.connect(self.db_path) as db:
            for text, meta, emb in zip(texts, metadatas, embeddings):
                doc_id = str(uuid.uuid4())
                await db.execute(
                    """
                    INSERT OR REPLACE INTO document_embeddings (id, task_id, text, embedding, metadata)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (doc_id, task_id, text, json.dumps(emb), json.dumps(meta))
                )
            await db.commit()

    async def similarity_search(
        self, 
        task_id: str, 
        query_embedding: List[float], 
        k: int = 5
    ) -> List[Dict[str, Any]]:
        """Retrieves top k documents matching the query vector for the specified task."""
        if not query_embedding:
            return []

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT id, text, embedding, metadata FROM document_embeddings WHERE task_id = ?",
                (task_id,)
            ) as cursor:
                rows = await cursor.fetchall()

        results = []
        for row in rows:
            try:
                emb = json.loads(row["embedding"])
                similarity = cosine_similarity(query_embedding, emb)
                results.append({
                    "id": row["id"],
                    "text": row["text"],
                    "metadata": json.loads(row["metadata"]),
                    "similarity": similarity
                })
            except Exception as e:
                print(f"Error parsing row in similarity_search: {e}")
                continue

        # Sort by similarity descending
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:k]

# Global instance of vector store
vector_store = SQLiteVectorStore()

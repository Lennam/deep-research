import aiosqlite
import json
import hashlib
import time
from typing import List, Dict, Any, Optional
from app.config import settings

def _get_hash(val: str) -> str:
    return hashlib.md5(val.encode("utf-8")).hexdigest()

async def init_cache_db():
    """Initializes search and scrape cache tables in SQLite."""
    async with aiosqlite.connect(settings.SQLITE_DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS search_cache (
                query_hash TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                mode TEXT NOT NULL,
                results TEXT NOT NULL,
                timestamp REAL NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS page_cache (
                url_hash TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp REAL NOT NULL
            )
        """)
        await db.commit()

async def get_search_cache(query: str, mode: str) -> Optional[List[Dict[str, Any]]]:
    """Retrieves cached search results if valid (not expired)."""
    q_hash = _get_hash(f"{query}:{mode}")
    ttl = settings.CACHE_SEARCH_TTL_DAYS * 86400
    now = time.time()
    
    try:
        async with aiosqlite.connect(settings.SQLITE_DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT results, timestamp FROM search_cache WHERE query_hash = ?", 
                (q_hash,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    if now - row["timestamp"] < ttl:
                        try:
                            return json.loads(row["results"])
                        except Exception:
                            return None
                    else:
                        # Expired, clean up
                        await db.execute("DELETE FROM search_cache WHERE query_hash = ?", (q_hash,))
                        await db.commit()
    except aiosqlite.OperationalError as e:
        if "no such table" in str(e):
            await init_cache_db()
            return await get_search_cache(query, mode)
        raise
    return None

async def set_search_cache(query: str, mode: str, results: List[Dict[str, Any]]):
    """Saves search results to the SQLite cache."""
    q_hash = _get_hash(f"{query}:{mode}")
    now = time.time()
    results_str = json.dumps(results)
    
    try:
        async with aiosqlite.connect(settings.SQLITE_DB_PATH) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO search_cache (query_hash, query, mode, results, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (q_hash, query, mode, results_str, now)
            )
            await db.commit()
    except aiosqlite.OperationalError as e:
        if "no such table" in str(e):
            await init_cache_db()
            return await set_search_cache(query, mode, results)
        raise

async def get_page_cache(url: str) -> Optional[str]:
    """Retrieves cleaned web page markdown content if valid."""
    u_hash = _get_hash(url)
    ttl = settings.CACHE_PAGE_TTL_DAYS * 86400
    now = time.time()
    
    try:
        async with aiosqlite.connect(settings.SQLITE_DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT content, timestamp FROM page_cache WHERE url_hash = ?", 
                (u_hash,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    if now - row["timestamp"] < ttl:
                        return row["content"]
                    else:
                        # Expired, clean up
                        await db.execute("DELETE FROM page_cache WHERE url_hash = ?", (u_hash,))
                        await db.commit()
    except aiosqlite.OperationalError as e:
        if "no such table" in str(e):
            await init_cache_db()
            return await get_page_cache(url)
        raise
    return None

async def set_page_cache(url: str, content: str):
    """Saves cleaner web page content to cache."""
    u_hash = _get_hash(url)
    now = time.time()
    
    try:
        async with aiosqlite.connect(settings.SQLITE_DB_PATH) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO page_cache (url_hash, url, content, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                (u_hash, url, content, now)
            )
            await db.commit()
    except aiosqlite.OperationalError as e:
        if "no such table" in str(e):
            await init_cache_db()
            return await set_page_cache(url, content)
        raise

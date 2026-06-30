import aiosqlite
import json
from app.config import settings

async def init_db():
    """初始化数据库表结构"""
    async with aiosqlite.connect(settings.SQLITE_DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id TEXT PRIMARY KEY,
                topic TEXT NOT NULL,
                max_depth INTEGER NOT NULL,
                max_breadth INTEGER NOT NULL,
                report_content TEXT NOT NULL,
                state_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        await db.commit()
        
    from app.utils.cache import init_cache_db
    await init_cache_db()
    
    from app.utils.vector_store import vector_store
    await vector_store.init_db()

async def save_report(
    report_id: str, 
    topic: str, 
    max_depth: int, 
    max_breadth: int, 
    report_content: str, 
    state_dict: dict,
    created_at: str
):
    """保存研究报告与状态"""
    async with aiosqlite.connect(settings.SQLITE_DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO reports (id, topic, max_depth, max_breadth, report_content, state_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (report_id, topic, max_depth, max_breadth, report_content, json.dumps(state_dict), created_at)
        )
        await db.commit()

async def get_all_reports_meta():
    """检索所有历史报告列表（排除大文本字段，仅供列表展示）"""
    async with aiosqlite.connect(settings.SQLITE_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, topic, max_depth, max_breadth, created_at, state_json FROM reports ORDER BY created_at DESC"
        ) as cursor:
            rows = await cursor.fetchall()
            results = []
            for r in rows:
                state_data = json.loads(r["state_json"])
                results.append({
                    "id": r["id"],
                    "topic": r["topic"],
                    "max_depth": r["max_depth"],
                    "max_breadth": r["max_breadth"],
                    "created_at": r["created_at"],
                    "facts_count": len(state_data.get("extracted_facts", [])),
                    "sources_count": len(state_data.get("sources", []))
                })
            return results

async def get_report_by_id(report_id: str):
    """按照 ID 查询单篇报告详细字段"""
    async with aiosqlite.connect(settings.SQLITE_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM reports WHERE id = ?", (report_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "id": row["id"],
                    "topic": row["topic"],
                    "max_depth": row["max_depth"],
                    "max_breadth": row["max_breadth"],
                    "report_content": row["report_content"],
                    "state_json": json.loads(row["state_json"]),
                    "created_at": row["created_at"]
                }
            return None

async def delete_report_by_id(report_id: str) -> bool:
    """按照 ID 物理删除单篇报告"""
    async with aiosqlite.connect(settings.SQLITE_DB_PATH) as db:
        async with db.execute("DELETE FROM reports WHERE id = ?", (report_id,)) as cursor:
            rowcount = cursor.rowcount
            await db.commit()
            return rowcount > 0

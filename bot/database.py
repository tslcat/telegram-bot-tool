import aiosqlite
import os
from datetime import datetime

DB_PATH = "data/notes.db"

async def init_db():
    """初始化数据库表"""
    os.makedirs("data", exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        # 笔记表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        # 图床图片记录表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                url TEXT NOT NULL,
                filename TEXT,
                uploaded_at TEXT NOT NULL
            )
        """)
        await db.commit()

# ==================== 笔记相关 ====================
async def add_note(user_id: int, content: str):
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO notes (user_id, content, created_at) VALUES (?, ?, ?)",
            (user_id, content, created_at)
        )
        await db.commit()

async def get_user_notes(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT id, content, created_at FROM notes WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        )
        rows = await cursor.fetchall()
        return [{"id": r[0], "content": r[1], "created_at": r[2]} for r in rows]

async def get_all_notes():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT user_id, content, created_at FROM notes ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        return [{"user_id": r[0], "content": r[1], "created_at": r[2]} for r in rows]

async def clear_all_notes():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM notes")
        await db.commit()

async def bulk_insert_notes(notes: list):
    async with aiosqlite.connect(DB_PATH) as db:
        for note in notes:
            await db.execute(
                "INSERT INTO notes (user_id, content, created_at) VALUES (?, ?, ?)",
                (note["user_id"], note["content"], note["created_at"])
            )
        await db.commit()

# ==================== 图床图片相关 ====================
async def add_image_record(user_id: int, url: str, filename: str = ""):
    uploaded_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO images (user_id, url, filename, uploaded_at) VALUES (?, ?, ?, ?)",
            (user_id, url, filename, uploaded_at)
        )
        await db.commit()

async def get_all_images():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT user_id, url, filename, uploaded_at FROM images ORDER BY uploaded_at DESC")
        rows = await cursor.fetchall()
        return [{"user_id": r[0], "url": r[1], "filename": r[2], "uploaded_at": r[3]} for r in rows]

async def clear_all_images():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM images")
        await db.commit()

async def bulk_insert_images(images: list):
    async with aiosqlite.connect(DB_PATH) as db:
        for img in images:
            await db.execute(
                "INSERT INTO images (user_id, url, filename, uploaded_at) VALUES (?, ?, ?, ?)",
                (img["user_id"], img["url"], img.get("filename", ""), img["uploaded_at"])
            )
        await db.commit()

async def delete_note_by_id(note_id: int, user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM notes WHERE id = ? AND user_id = ?",
            (note_id, user_id)
        )
        await db.commit()
        return db.total_changes > 0
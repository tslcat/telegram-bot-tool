import sqlite3
import os
from datetime import datetime
from config import DB_PATH

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 记事本表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 收藏夹表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            remark TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("数据库初始化完成")

def add_note(title: str, content: str) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO notes (title, content) VALUES (?, ?)",
        (title, content)
    )
    note_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return note_id

def get_all_notes():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notes ORDER BY updated_at DESC")
    notes = cursor.fetchall()
    conn.close()
    return notes

def get_note(note_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
    note = cursor.fetchone()
    conn.close()
    return note

def update_note(note_id: int, title: str, content: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE notes SET title = ?, content = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (title, content, note_id)
    )
    conn.commit()
    conn.close()

def delete_note(note_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    conn.commit()
    conn.close()

def add_bookmark(title: str, url: str, remark: str = "") -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO bookmarks (title, url, remark) VALUES (?, ?, ?)",
        (title, url, remark)
    )
    bookmark_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return bookmark_id

def get_all_bookmarks():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bookmarks ORDER BY updated_at DESC")
    bookmarks = cursor.fetchall()
    conn.close()
    return bookmarks

def get_bookmark(bookmark_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bookmarks WHERE id = ?", (bookmark_id,))
    bookmark = cursor.fetchone()
    conn.close()
    return bookmark

def update_bookmark(bookmark_id: int, title: str, url: str, remark: str = ""):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE bookmarks SET title = ?, url = ?, remark = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (title, url, remark, bookmark_id)
    )
    conn.commit()
    conn.close()

def delete_bookmark(bookmark_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM bookmarks WHERE id = ?", (bookmark_id,))
    conn.commit()
    conn.close()
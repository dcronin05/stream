import sqlite3
import time
from datetime import datetime
import os

DB_PATH = os.environ.get("DB_PATH", "data/clipboard.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=60.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS clips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            source TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            comment TEXT,
            item_type TEXT DEFAULT 'text'
        )
    ''')
    try:
        c.execute('ALTER TABLE clips ADD COLUMN comment TEXT')
    except sqlite3.OperationalError:
        pass # Column already exists
    try:
        c.execute("ALTER TABLE clips ADD COLUMN item_type TEXT DEFAULT 'text'")
    except sqlite3.OperationalError:
        pass # Column already exists
    try:
        c.execute("ALTER TABLE clips ADD COLUMN author TEXT DEFAULT 'Anonymous'")
    except sqlite3.OperationalError:
        pass # Column already exists
    conn.commit()
    conn.close()

def add_clip(content: str, source: str = "api", comment: str = None, item_type: str = "text", author: str = "Anonymous"):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('INSERT INTO clips (content, source, comment, item_type, author) VALUES (?, ?, ?, ?, ?)', (content, source, comment, item_type, author))
        conn.commit()
        time.sleep(0.05)  # Yield write-lock
    finally:
        conn.close()

def get_latest_clip():
    conn = get_connection()
    try:
        cur = conn.execute("SELECT * FROM clips ORDER BY timestamp DESC LIMIT 1")
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def update_clip_comment(clip_id: int, comment: str):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('UPDATE clips SET comment = ? WHERE id = ?', (comment, clip_id))
        conn.commit()
        time.sleep(0.05)
    finally:
        conn.close()

def get_clips(limit: int = 50):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('SELECT id, content, source, timestamp, comment, item_type, author FROM clips ORDER BY timestamp DESC LIMIT ?', (limit,))
        clips = []
        for row in c.fetchall():
            clips.append({
                "id": row[0],
                "content": row[1],
                "source": row[2],
                "timestamp": row[3],
                "comment": row[4],
                "item_type": row[5] or "text",
                "author": row[6] or "Anonymous"
            })
        return clips
    finally:
        conn.close()

def clear_clips():
    conn = get_connection()
    try:
        conn.execute("DELETE FROM clips")
        conn.commit()
        time.sleep(0.05)
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()

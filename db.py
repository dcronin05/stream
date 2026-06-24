import sqlite3
import time
from datetime import datetime
import os
import json

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
    try:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS clips (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                source TEXT DEFAULT 'web-ui',
                comment TEXT,
                item_type TEXT DEFAULT 'text',
                author TEXT DEFAULT 'Anonymous',
                reactions TEXT DEFAULT '{}',
                parent_id INTEGER DEFAULT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Add columns if they don't exist (migration)
        try:
            c.execute('ALTER TABLE clips ADD COLUMN comment TEXT')
        except sqlite3.OperationalError:
            pass
        try:
            c.execute("ALTER TABLE clips ADD COLUMN item_type TEXT DEFAULT 'text'")
        except sqlite3.OperationalError:
            pass
        try:
            c.execute("ALTER TABLE clips ADD COLUMN author TEXT DEFAULT 'Anonymous'")
        except sqlite3.OperationalError:
            pass
        try:
            c.execute("ALTER TABLE clips ADD COLUMN reactions TEXT DEFAULT '{}'")
        except sqlite3.OperationalError:
            pass
        try:
            c.execute('ALTER TABLE clips ADD COLUMN parent_id INTEGER DEFAULT NULL')
        except sqlite3.OperationalError:
            pass
        conn.commit()
    finally:
        conn.close()

def add_clip(content: str, source: str = "web-ui", comment: str = None, item_type: str = "text", author: str = "Anonymous", parent_id: int = None):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute(
            'INSERT INTO clips (content, source, comment, item_type, author, parent_id) VALUES (?, ?, ?, ?, ?, ?)',
            (content, source, comment, item_type, author, parent_id)
        )
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

def update_clip_comment(clip_id: int, comment: str | None):
    with sqlite3.connect(DB_PATH, timeout=60.0) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("UPDATE clips SET comment = ? WHERE id = ?", (comment, clip_id))
        conn.commit()
    time.sleep(0.05)

def update_clip_content(clip_id: int, content: str):
    with sqlite3.connect(DB_PATH, timeout=60.0) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("UPDATE clips SET content = ? WHERE id = ?", (content, clip_id))
        conn.commit()
    time.sleep(0.05)

def update_reaction(clip_id: int, emoji: str, author: str):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('SELECT reactions FROM clips WHERE id = ?', (clip_id,))
        row = c.fetchone()
        if not row: return
        
        try:
            reactions = json.loads(row[0]) if row[0] else {}
        except:
            reactions = {}
            
        if emoji not in reactions:
            reactions[emoji] = []
            
        if author in reactions[emoji]:
            reactions[emoji].remove(author)
            if not reactions[emoji]:
                del reactions[emoji]
        else:
            reactions[emoji].append(author)
            
        c.execute('UPDATE clips SET reactions = ? WHERE id = ?', (json.dumps(reactions), clip_id))
        conn.commit()
        time.sleep(0.05)
    finally:
        conn.close()

def get_clips(limit: int = 50):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('SELECT id, content, source, timestamp, comment, item_type, author, reactions, parent_id FROM clips ORDER BY timestamp DESC LIMIT ?', (limit,))
        clips = []
        for row in c.fetchall():
            try:
                reactions = json.loads(row[7]) if row[7] else {}
            except:
                reactions = {}
            clips.append({
                "id": row[0],
                "content": row[1],
                "source": row[2],
                "timestamp": row[3],
                "comment": row[4],
                "item_type": row[5] or "text",
                "author": row[6] or "Anonymous",
                "reactions": reactions,
                "parent_id": row[8]
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

import os
import sqlite3
import requests
import json
import time

DB_PATH = "data/clipboard.db"
SYNC_STATE_PATH = "data/last_sync_id.txt"
MEMEX_URL = "http://localhost:8001/api/ingest"

def get_last_sync_id():
    if os.path.exists(SYNC_STATE_PATH):
        with open(SYNC_STATE_PATH, "r") as f:
            return int(f.read().strip() or 0)
    return 0

def set_last_sync_id(last_id):
    with open(SYNC_STATE_PATH, "w") as f:
        f.write(str(last_id))

def sync_clips():
    last_id = get_last_sync_id()
    
    if not os.path.exists(DB_PATH):
        return
        
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    c = conn.cursor()
    c.execute('SELECT id, content, source, timestamp, comment, item_type, author FROM clips WHERE id > ? ORDER BY id ASC', (last_id,))
    rows = c.fetchall()
    
    max_id = last_id
    for row in rows:
        clip_id, content, source, timestamp, comment, item_type, author = row
        
        # Build Memex Payload
        title = f"Stream: Post by {author}"
        
        body = f"**Author:** `{author}`\n**Source:** `{source}`\n**Time:** `{timestamp}`\n"
        if comment:
            body += f"\n**Context/Comment:**\n> {comment}\n"
            
        if item_type == "image":
            body += f"\n**Content (Image Path):** `{content}`\n"
        else:
            body += f"\n**Content:**\n```\n{content}\n```\n"
            
        payload = {
            "title": title,
            "text": body,
            "draft": False,
            "source": "clipboard-mcp"
        }
        
        try:
            resp = requests.post(MEMEX_URL, json=payload, timeout=10)
            if resp.status_code in [200, 201]:
                max_id = max(max_id, clip_id)
            else:
                print(f"Failed to ingest clip {clip_id}: {resp.text}")
                break # Stop and retry next time
        except Exception as e:
            print(f"Error connecting to Memex: {e}")
            break
            
        time.sleep(0.1) # Be nice to the Memex API

    set_last_sync_id(max_id)
    conn.close()

if __name__ == "__main__":
    # Ensure we run from the app directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    sync_clips()

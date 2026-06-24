from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import db
import uvicorn
import os
import uuid
import base64

os.makedirs("data/uploads", exist_ok=True)

app = FastAPI(title="Clipboard MCP Web UI")
app.mount("/static/uploads", StaticFiles(directory="data/uploads"), name="uploads")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

db.init_db()

class ClipRequest(BaseModel):
    content: str
    source: str = "web-ui"
    comment: str | None = None
    item_type: str = "text"
    author: str = "Anonymous"

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    clips = db.get_clips(50)
    for c in clips:
        author = c.get("author", "Anonymous")
        if os.path.exists(f"static/avatars/{author}.png"):
            c["avatar_url"] = f"/static/avatars/{author}.png"
        else:
            c["avatar_url"] = None
            hash_val = sum(ord(char) for char in author)
            colors = ["#f43f5e", "#d946ef", "#8b5cf6", "#3b82f6", "#0ea5e9", "#10b981", "#84cc16", "#eab308", "#f97316"]
            c["color"] = colors[hash_val % len(colors)]
            c["initial"] = author[0].upper() if author else "?"
            
    brand_logo_exists = os.path.exists("static/brand/logo-horizontal.svg")
    return templates.TemplateResponse(request=request, name="index.html", context={"clips": clips, "brand_logo_exists": brand_logo_exists})

@app.post("/api/clip")
async def create_clip(clip: ClipRequest, request: Request):
    content = clip.content
    item_type = clip.item_type
    source = clip.source

    if source == "web-ui":
        ua = request.headers.get("user-agent", "").lower()
        if "macintosh" in ua or "mac os x" in ua:
            source = "web-ui (macOS)"
        elif "iphone" in ua or "ipad" in ua:
            source = "web-ui (iOS)"
        elif "android" in ua:
            source = "web-ui (Android)"
        elif "windows" in ua:
            source = "web-ui (Windows)"
        elif "linux" in ua:
            source = "web-ui (Linux)"

    if item_type == "image" and content.startswith("data:image/"):
        try:
            # Extract the base64 part
            header, encoded = content.split(",", 1)
            # Find extension
            ext = "png"
            if "jpeg" in header or "jpg" in header:
                ext = "jpg"
            elif "gif" in header:
                ext = "gif"
            
            image_data = base64.b64decode(encoded)
            filename = f"{uuid.uuid4().hex}.{ext}"
            os.makedirs("data/uploads", exist_ok=True)
            filepath = os.path.join("data/uploads", filename)
            
            with open(filepath, "wb") as f:
                f.write(image_data)
            
            content = f"/static/uploads/{filename}" # We will mount this later
        except Exception as e:
            print("Failed to save image:", e)
            item_type = "text" # Fallback

    db.add_clip(content, source, clip.comment, item_type, clip.author)
    return {"status": "success"}

class CommentRequest(BaseModel):
    comment: str | None

@app.put("/api/clip/{clip_id}/comment")
async def update_comment(clip_id: int, req: CommentRequest):
    db.update_clip_comment(clip_id, req.comment)
    return {"status": "success"}

@app.get("/api/clips")
async def get_clips():
    return db.get_clips(50)

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)

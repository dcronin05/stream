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
import boto3
from botocore.exceptions import ClientError

S3_ENDPOINT = os.getenv("S3_ENDPOINT")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_BUCKET = os.getenv("S3_BUCKET", "stream-media")
S3_PUBLIC_URL = os.getenv("S3_PUBLIC_URL")

s3_client = None
if S3_ENDPOINT and S3_ACCESS_KEY and S3_SECRET_KEY:
    try:
        s3_client = boto3.client('s3', endpoint_url=S3_ENDPOINT, aws_access_key_id=S3_ACCESS_KEY, aws_secret_access_key=S3_SECRET_KEY, region_name="us-east-1")
        try:
            s3_client.head_bucket(Bucket=S3_BUCKET)
        except ClientError:
            s3_client.create_bucket(Bucket=S3_BUCKET)
            # Set public read policy for the bucket
            policy = f'{{"Version":"2012-10-17","Statement":[{{"Effect":"Allow","Principal":{{"AWS":["*"]}},"Action":["s3:GetObject"],"Resource":["arn:aws:s3:::{S3_BUCKET}/*"]}}]}}'
            s3_client.put_bucket_policy(Bucket=S3_BUCKET, Policy=policy)
    except Exception as e:
        print("S3 Init Error:", e)

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
    parent_id: int | None = None

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    from fastapi.responses import FileResponse
    return FileResponse("static/avatars/agy.png")

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

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    from fastapi.responses import FileResponse
    return FileResponse("static/brand/logo-icon.svg")

@app.post("/api/clip")
async def create_clip(clip: ClipRequest, request: Request):
    content = clip.content
    item_type = clip.item_type
    source = clip.source
    author = clip.author

    # Guess the user based on the device if they are anonymous
    if author == "Anonymous" or not author:
        ua = request.headers.get("user-agent", "").lower()
        if "macintosh" in ua or "iphone" in ua or "ipad" in ua or "windows" in ua:
            author = "dcronin05"

    if source == "web-ui":
        ua = request.headers.get("user-agent", "").lower()
        if "macintosh" in ua or "mac os x" in ua:
            source = f"{author}'s Mac Mini" if author == "dcronin05" else "Mac"
        elif "iphone" in ua:
            source = f"{author}'s iPhone" if author == "dcronin05" else "iPhone"
        elif "ipad" in ua:
            source = f"{author}'s iPad" if author == "dcronin05" else "iPad"
        elif "windows" in ua:
            source = f"{author}'s PC" if author == "dcronin05" else "Windows PC"
        elif "android" in ua:
            source = f"{author}'s Android" if author == "dcronin05" else "Android"
        elif "linux" in ua:
            source = "Linux"

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
            
            upload_success = False
            if s3_client:
                try:
                    # Upload to MinIO S3
                    s3_client.put_object(
                        Bucket=S3_BUCKET,
                        Key=filename,
                        Body=image_data,
                        ContentType=f"image/{ext}"
                    )
                    if S3_PUBLIC_URL:
                        content = f"{S3_PUBLIC_URL}/{S3_BUCKET}/{filename}"
                    else:
                        content = f"{S3_ENDPOINT}/{S3_BUCKET}/{filename}"
                    upload_success = True
                except Exception as s3_err:
                    print(f"S3 Upload failed, falling back to local: {s3_err}")
                    
            if not upload_success:
                # Local volume fallback
                os.makedirs("data/uploads", exist_ok=True)
                filepath = os.path.join("data/uploads", filename)
                with open(filepath, "wb") as f:
                    f.write(image_data)
                content = f"/static/uploads/{filename}"
                
        except Exception as e:
            print(f"Error parsing image: {e}")
            item_type = "text" # Fallback

    db.add_clip(content, source, clip.comment, item_type, author, clip.parent_id)
    return {"status": "success"}

class CommentRequest(BaseModel):
    comment: str | None

@app.put("/api/clip/{clip_id}/comment")
async def update_comment(clip_id: int, req: CommentRequest):
    db.update_clip_comment(clip_id, req.comment)
    return {"status": "success"}

class EditRequest(BaseModel):
    content: str

@app.put("/api/clip/{clip_id}")
async def edit_clip(clip_id: int, req: EditRequest):
    db.update_clip_content(clip_id, req.content)
    return {"status": "success"}

class ReactionRequest(BaseModel):
    emoji: str
    author: str

@app.put("/api/clip/{clip_id}/reaction")
async def toggle_reaction(clip_id: int, req: ReactionRequest):
    db.update_reaction(clip_id, req.emoji, req.author)
    return {"status": "success"}

@app.get("/api/clips")
async def get_clips():
    return db.get_clips(50)

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)

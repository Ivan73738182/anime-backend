from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import boto3
from botocore.config import Config
import os
import uuid

app = FastAPI()

S3_ENDPOINT = os.getenv("S3_ENDPOINT")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_BUCKET = "anime-app-storage"

s3 = boto3.client(
    's3',
    endpoint_url=S3_ENDPOINT,
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY,
    config=Config(signature_version='s3v4')
)

active_codes = {}
videos_db = []

class CodeRequest(BaseModel):
    phone: str
    code: str

@app.post("/save-code")
async def save_code(data: CodeRequest):
    active_codes[data.phone] = data.code
    return {"status": "ok"}

class VerifyRequest(BaseModel):
    phone: str
    code: str

@app.post("/verify-code")
async def verify_code(data: VerifyRequest):
    saved_code = active_codes.get(data.phone)
    if saved_code and saved_code == data.code:
        del active_codes[data.phone]
        return {"status": "success", "token": "user_token_123"}
    raise HTTPException(status_code=400, detail="Неверный код")

class UploadRequest(BaseModel):
    filename: str
    file_type: str

@app.post("/get-upload-url")
async def get_upload_url(data: UploadRequest):
    file_key = f"{data.file_type}/{uuid.uuid4()}_{data.filename}"
    url = s3.generate_presigned_url(
        ClientMethod='put_object',
        Params={'Bucket': S3_BUCKET, 'Key': file_key},
        ExpiresIn=900
    )
    public_url = f"{S3_ENDPOINT}/{S3_BUCKET}/{file_key}"
    return {"upload_url": url, "public_url": public_url}

class VideoSaveRequest(BaseModel):
    title: str
    description: str
    author_phone: str
    video_url: str
    image_url: str

@app.post("/save-video")
async def save_video(data: VideoSaveRequest):
    video_data = {
        "id": str(uuid.uuid4()),
        "title": data.title,
        "description": data.description,
        "author_phone": data.author_phone,
        "video_url": data.video_url,
        "image_url": data.image_url,
        "status": "pending",
        "likes": 0,
        "views": 0
    }
    videos_db.append(video_data)
    return {"status": "ok", "video": video_data}

@app.get("/videos")
async def get_videos():
    approved = [v for v in videos_db if v["status"] == "approved"]
    return {"videos": approved}

@app.get("/my-videos/{phone}")
async def get_my_videos(phone: str):
    my_videos = [v for v in videos_db if v["author_phone"] == phone]
    return {"videos": my_videos}

@app.get("/admin/pending")
async def get_pending():
    pending = [v for v in videos_db if v["status"] == "pending"]
    return {"videos": pending}

@app.post("/admin/approve/{video_id}")
async def approve_video(video_id: str):
    for v in videos_db:
        if v["id"] == video_id:
            v["status"] = "approved"
            return {"status": "ok"}
    raise HTTPException(status_code=404, detail="Видео не найдено")

@app.post("/admin/reject/{video_id}")
async def reject_video(video_id: str):
    global videos_db
    videos_db = [v for v in videos_db if v["id"] != video_id]
    return {"status": "ok"}

# НОВЫЕ ЭНДПОИНТЫ ДЛЯ ЛАЙКОВ И ПРОСМОТРОВ
@app.post("/like/{video_id}")
async def like_video(video_id: str):
    for v in videos_db:
        if v["id"] == video_id:
            v["likes"] += 1
            return {"status": "ok", "likes": v["likes"]}
    raise HTTPException(status_code=404, detail="Видео не найдено")

@app.post("/view/{video_id}")
async def view_video(video_id: str):
    for v in videos_db:
        if v["id"] == video_id:
            v["views"] += 1
            return {"status": "ok", "views": v["views"]}
    raise HTTPException(status_code=404, detail="Видео не найдено")

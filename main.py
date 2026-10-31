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

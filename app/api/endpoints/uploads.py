from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Any
from app.services.upload_service import UploadService

router = APIRouter()

@router.post("/", response_model=dict)
async def upload_file(file: UploadFile = File(...)) -> Any:
    """Upload a file to Cloudinary and return its URL."""
    try:
        url = await UploadService.upload_file(file)
        return {"url": url, "filename": file.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

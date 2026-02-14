import cloudinary
import cloudinary.uploader
from fastapi import UploadFile, HTTPException
from app.core.config import settings

# Configure Cloudinary
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET
)

class UploadService:
    @staticmethod
    async def upload_file(file: UploadFile, folder: str = "skillnscale") -> str:
        """
        Uploads a file to Cloudinary and returns the secure URL.
        """
        try:
            # Read file content
            content = await file.read()
            
            # Upload to Cloudinary
            response = cloudinary.uploader.upload(
                content,
                folder=folder,
                resource_type="auto"
            )
            
            return response.get("secure_url")
            
        except Exception as e:
            print(f"Cloudinary upload error: {str(e)}")
            raise HTTPException(status_code=500, detail="File upload failed")
        finally:
            await file.seek(0)  # Reset file pointer if needed

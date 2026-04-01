from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
import os
from core.config import settings
from core.storage import storage_service
from api.deps import get_current_active_user
from models.users import User

router = APIRouter()


@router.get("/{folder}/{filename}")
async def get_private_file(
    folder: str,
    filename: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Securely serve files after checking authentication.
    - MinIO/S3 backend: redirects to a time-limited presigned URL.
    - Local backend: streams the file directly from disk.
    """
    # Prevent path traversal
    if ".." in folder or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid path")

    if settings.STORAGE_BACKEND == "s3":
        try:
            presigned_url = storage_service.get_presigned_url(folder, filename)
        except Exception:
            raise HTTPException(status_code=404, detail="File not found")
        return RedirectResponse(url=presigned_url)

    # Local storage
    file_path = os.path.join(settings.LOCAL_STORAGE_PATH, folder, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path)

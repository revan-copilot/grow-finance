from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
import os
from core.config import settings
from api.deps import get_current_active_user
from models.users import User
from models.clients import Client

router = APIRouter()

@router.get("/{folder}/{filename}")
async def get_private_file(
    folder: str,
    filename: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Securely serve files after checking authentication.
    """
    # Prevent path traversal
    if ".." in folder or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid path")
    
    file_path = os.path.join(settings.LOCAL_STORAGE_PATH, folder, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    # TODO: Add granular check (e.g., if customer, check if file belongs to them)
    # For now, being authenticated is much better than public access
    
    return FileResponse(file_path)

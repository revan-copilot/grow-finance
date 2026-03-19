"""
User-related endpoints.

This module contains routers for user authentication, profile management,
password resets, and administrative user management.
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid

from models.users import User, PasswordResetCode, UserSession
from schemas.user import (
    UserCreate, 
    UserRead, 
    UserUpdate,
    UserUpdateStatus,
    ProfileUpdate,
    ProfilePasswordUpdate,
    ChangePasswordRequest,
    LoginRequest, 
    ForgotPasswordRequest, 
    SetPasswordRequest, 
    Token
)
from core.security import verify_password, get_password_hash, create_access_token
from api.deps import get_db, get_current_active_user, get_admin
from core.storage import storage_service

router = APIRouter()

def send_reset_email(email: str, code: str):
    """
    Simulates sending a password reset email.
    
    Args:
        email (str): Recipient email address.
        code (str): The 6-digit reset code.
    """
    import logging
    logger = logging.getLogger(__name__)
    # Simulate email sending (console backend approach)
    logger.info(f"Sending email to {email}")
    logger.info(f"Subject: Password Reset Request")
    logger.info(f"Body: Your 6-digit password reset code is: {code}\nThis code expires in 10 minutes.")

from fastapi.security import OAuth2PasswordRequestForm

@router.post("/login", response_model=Token)
def login(
    request: Request,
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    Authenticate a user and return a JWT access token.
    Compatible with OAuth2 standard (Swagger Authorize button).
    """
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if user.status != 'active':
        raise HTTPException(status_code=403, detail="Account is inactive.")
    
    # Record Login Stats
    user.last_login_at = datetime.utcnow()
    user.last_login_ip = request.client.host
    
    # Create Session Record
    session_id = str(uuid.uuid4())
    new_session = UserSession(
        user_id=user.id,
        session_id=session_id,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent"),
        expires_at=datetime.utcnow() + timedelta(days=7) # example expiry
    )
    db.add(new_session)
    db.commit()
        
    access_token = create_access_token(
        subject=user.email,
        extra_claims={"sid": session_id}
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/profile", response_model=UserRead)
def read_users_me(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    """
    Get the profile information with login history and active sessions.
    """
    return current_user

@router.put("/profile", response_model=UserRead)
def update_profile(
    profile_in: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update the current user's profile (full_name, first_name, last_name, phone_number, job_title).
    """
    if profile_in.full_name is not None:
        current_user.full_name = profile_in.full_name
    if profile_in.first_name is not None:
        current_user.first_name = profile_in.first_name
    if profile_in.last_name is not None:
        current_user.last_name = profile_in.last_name
    if profile_in.phone_number is not None:
        current_user.phone_number = profile_in.phone_number
    if profile_in.job_title is not None:
        current_user.job_title = profile_in.job_title
    
    db.commit()
    db.refresh(current_user)
    return current_user

@router.post("/profile/password")
def update_profile_password(
    request: ProfilePasswordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update password from the user profile security settings.
    Requires the current password and confirmation.
    """
    if request.new_password != request.confirm_new_password:
        raise HTTPException(status_code=400, detail="New passwords do not match")

    if not verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    current_user.hashed_password = get_password_hash(request.new_password)
    db.commit()
    return {"status": "success", "message": "Profile password updated successfully"}

@router.post("/profile/picture")
async def update_profile_picture(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Upload and update the current user's profile picture.
    """
    ext = file.filename.split(".")[-1]
    unique_name = f"profile_{current_user.uuid}_{uuid.uuid4().hex[:8]}.{ext}"
    
    file_url = await storage_service.upload_file(file.file, unique_name, folder="profiles")
    
    current_user.profile_picture_url = file_url
    db.commit()
    db.refresh(current_user)
    
    return {"status": "success", "message": "Profile picture updated", "data": {"url": file_url}}

@router.post("/change-password")
def change_password(
    request: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Change the password for newly registered users.
    Typically used for the first-time setup or after account creation.
    """
    if request.new_password != request.confirm_new_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    
    current_user.hashed_password = get_password_hash(request.new_password)
    db.commit()
    return {"status": "success", "message": "Password changed successfully"}

@router.post("/logout")
def logout(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Logout the current user by invalidating the specific session.
    """
    sid = getattr(current_user, "_current_sid", None)
    if sid:
        db.query(UserSession).filter(UserSession.session_id == sid).delete()
        db.commit()
        
    return {"status": "success", "message": "Logout successful"}

@router.post("/forgot-password")
def forgot_password(request: ForgotPasswordRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Initiate a password reset flow by sending a code to the user's email.
    """
    user = db.query(User).filter(User.email == request.email).first()
    if user and user.status == 'active':
        code = PasswordResetCode.generate_code(db, user.id)
        background_tasks.add_task(send_reset_email, user.email, code)
    # Always return success to prevent email enumeration
    return {"message": "If the email exists, a reset link has been sent."}

@router.post("/reset-password")
def set_password(request: SetPasswordRequest, db: Session = Depends(get_db)):
    """
    Reset a user's password using a valid reset code.
    """
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired token.")
        
    reset_entry = user.reset_code_entry
    if not reset_entry or reset_entry.code != request.code or not reset_entry.is_valid():
        raise HTTPException(status_code=400, detail="Invalid or expired token.")
        
    user.hashed_password = get_password_hash(request.password)
    db.delete(reset_entry)
    db.commit()
    
    return {"message": "Password has been safely updated."}

@router.get("/management")
def list_users(
    skip: int = 0,
    limit: int = 20,
    sort_by: str = "created_at",
    order: str = "desc",
    db: Session = Depends(get_db), 
    current_admin: User = Depends(get_admin)
):
    """
    List all users with pagination and sorting.
    """
    query = db.query(User).filter(User.status != "deleted")
    
    # Sorting logic
    sort_attr = getattr(User, sort_by, User.created_at)
    if order.lower() == "asc":
        query = query.order_by(sort_attr.asc())
    else:
        query = query.order_by(sort_attr.desc())
        
    total = query.count()
    users = query.offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "data": users
    }

@router.post("/management", response_model=UserRead, status_code=201)
def create_user(user_in: UserCreate, db: Session = Depends(get_db), current_admin: User = Depends(get_admin)):
    """
    Create a new user. (Administrative)
    """
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")
        
    import secrets
    import string
    # Generate a random 12-character password
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    random_password = ''.join(secrets.choice(alphabet) for i in range(12))
    
    hashed_password = get_password_hash(random_password)
    new_user = User(
        email=user_in.email,
        full_name=user_in.full_name,
        role=user_in.role,
        status=user_in.status,
        hashed_password=hashed_password,
        is_active=(user_in.status == 'active')
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.delete("/management/{user_uuid}", status_code=204)
def delete_user(user_uuid: str, db: Session = Depends(get_db), current_admin: User = Depends(get_admin)):
    """
    Soft-delete a user by UUID. Frees up email for reuse. (Administrative)
    """
    user = db.query(User).filter(User.uuid == user_uuid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.status == 'deleted':
        raise HTTPException(status_code=400, detail="User is already deleted")
        
    user.status = 'deleted'
    user.is_active = False
    
    # Suffix email to free the original for reuse
    user.email = f"{user.email}_deleted_{user.uuid[:8]}"
    
    db.commit()
    return None

@router.put("/management/{user_uuid}", response_model=UserRead)
def update_user(
    user_uuid: str,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_admin)
):
    """
    Edit user details (full_name, email, role, status) by UUID. (Administrative)
    """
    user = db.query(User).filter(User.uuid == user_uuid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check for email uniqueness if email is being changed
    if user_in.email and user_in.email != user.email:
        existing = db.query(User).filter(User.email == user_in.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already in use")
        user.email = user_in.email
    
    if user_in.full_name is not None:
        user.full_name = user_in.full_name
    if user_in.role is not None:
        user.role = user_in.role
    if user_in.status is not None:
        user.status = user_in.status
        user.is_active = (user.status == 'active')
    
    db.commit()
    db.refresh(user)
    return user

@router.patch("/management/{user_uuid}/status", response_model=UserRead)
def change_user_status(user_uuid: str, status_update: UserUpdateStatus, db: Session = Depends(get_db), current_admin: User = Depends(get_admin)):
    """
    Change the status of a user (active/inactive/on_hold) by UUID. (Administrative)
    """
    user = db.query(User).filter(User.uuid == user_uuid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user.status = status_update.status
    user.is_active = (user.status == 'active')
    db.commit()
    db.refresh(user)
    return user

"""
Pydantic schemas for user-related data transfer objects (DTOs).
"""
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List
from datetime import datetime

class UserBase(BaseModel):
    """
    Base user schema with shared attributes.
    """
    email: str
    full_name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    job_title: Optional[str] = None
    role: str
    status: str = "active"

class UserCreate(BaseModel):
    """
    Schema for creating a new user.
    """
    email: EmailStr
    full_name: str
    role: str
    status: str = "active"

class UserSessionRead(BaseModel):
    """
    Schema for reading session data.
    """
    session_id: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    last_activity_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class UserRead(UserBase):
    """
    Schema for reading user data.
    """
    uuid: str
    last_login_at: Optional[datetime] = None
    last_login_ip: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    sessions: List[UserSessionRead] = []

    model_config = ConfigDict(from_attributes=True)

class UserUpdateStatus(BaseModel):
    """
    Schema for updating a user's status.
    """
    status: str

class UserUpdate(BaseModel):
    """
    Schema for editing user details (admin action).
    """
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    job_title: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None

class ProfileUpdate(BaseModel):
    """
    Schema for users to update their own profile.
    """
    full_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    job_title: Optional[str] = None

class ChangePasswordRequest(BaseModel):
    """
    Schema for changing password for newly registered users.
    """
    new_password: str = Field(..., min_length=8)
    confirm_new_password: str = Field(..., min_length=8)

class ProfilePasswordUpdate(BaseModel):
    """
    Schema for updating password from the user profile security settings.
    """
    current_password: str
    new_password: str = Field(..., min_length=8)
    confirm_new_password: str = Field(..., min_length=8)
        
class LoginRequest(BaseModel):
    """
    Schema for user login credentials.
    """
    email: EmailStr
    password: str

class ForgotPasswordRequest(BaseModel):
    """
    Schema for initiating a password reset.
    """
    email: EmailStr

class SetPasswordRequest(BaseModel):
    """
    Schema for resetting a password with a code.
    """
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6)
    password: str = Field(..., min_length=8)

class Token(BaseModel):
    """
    Schema for JWT access token response.
    """
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """
    Schema for data stored within the JWT payload.
    """
    email: Optional[str] = None
    sid: Optional[str] = None

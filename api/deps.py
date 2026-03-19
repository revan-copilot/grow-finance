"""
Global dependencies for the API.

This module contains dependency functions for database sessions,
authentication, and user authorization.
"""
from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from pydantic import ValidationError

from core.config import settings
from db.database import SessionLocal
from models.users import User
from schemas.user import TokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/users/login")

def get_db() -> Generator:
    """
    Dependency to provide a database session to a request.
    
    Yields:
        Generator[Session, None, None]: The database session.
    """
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()

def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> User:
    """
    Dependency to authenticate a user via JWT, extracting subject and session ID.
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = TokenData(email=payload.get("sub"), sid=payload.get("sid"))
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(User).filter(User.email == token_data.email).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    # Optional: Attach session_id to user object temporarily for use in routers
    user._current_sid = token_data.sid
    return user

def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency to check if the authenticated user is active.

    Args:
        current_user (User): The user object from get_current_user.

    Returns:
        User: The authenticated and active user.

    Raises:
        HTTPException: If the user is inactive.
    """
    if not current_user.is_active or current_user.status != 'active':
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def get_finance_staff(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """
    Dependency to check if the user is a finance staff.
    Admins are strictly excluded from this permission point.
    """
    if current_user.role.lower() != "staff":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only finance staff have access to this action."
        )
    return current_user

def get_admin(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """
    Dependency to check if the user is an administrator.
    """
    if current_user.role.strip().lower() != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required."
        )
    return current_user

def get_staff_or_admin(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """
    Dependency to check if the user is either staff or admin.
    """
    if current_user.role.lower() not in ["staff", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to staff or administrators."
        )
    return current_user

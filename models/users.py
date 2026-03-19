"""
Database models for users and authentication.
"""
import uuid
import random
import string
from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from db.database import Base

class User(Base):
    """
    SQLAlchemy model representing a system user.
    """
    __tablename__ = "core_users"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, index=True, nullable=False, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    phone_number = Column(String(20), nullable=True)
    job_title = Column(String(100), nullable=True)
    role = Column(String(50), index=True, nullable=False)
    status = Column(String(20), default="active", index=True, nullable=False)
    
    is_staff = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    
    hashed_password = Column(String(255), nullable=False)
    
    last_login_at = Column(DateTime, nullable=True)
    last_login_ip = Column(String(45), nullable=True) # supports IPv6
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    reset_code_entry = relationship("PasswordResetCode", back_populates="user", uselist=False, cascade="all, delete-orphan")
    client_profile = relationship("Client", back_populates="user", uselist=False, foreign_keys="Client.user_id")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")


class UserSession(Base):
    """
    SQLAlchemy model for tracking active user sessions/logins.
    """
    __tablename__ = "core_user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("core_users.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(String(255), unique=True, index=True, nullable=False) # e.g. JWT JTI or random string
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(512), nullable=True)
    last_activity_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    
    user = relationship("User", back_populates="sessions")


class PasswordResetCode(Base):
    """
    SQLAlchemy model for temporary password reset codes.
    """
    __tablename__ = "core_password_resets"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("core_users.id", ondelete="CASCADE"), unique=True, nullable=False)
    code = Column(String(6), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    user = relationship("User", back_populates="reset_code_entry")
    
    def is_valid(self):
        """
        Check if the reset code is still valid (less than 10 minutes old).
        """
        return datetime.utcnow() < self.created_at + timedelta(minutes=10)
    
    @classmethod
    def generate_code(cls, db_session, user_id: int):
        """
        Generate a new 6-digit code for a user and store/update it in the DB.
        """
        code = ''.join(random.choices(string.digits, k=6))
        
        # Check if exists
        db_obj = db_session.query(cls).filter(cls.user_id == user_id).first()
        if db_obj:
            db_obj.code = code
            db_obj.created_at = datetime.utcnow()
        else:
            db_obj = cls(user_id=user_id, code=code)
            db_session.add(db_obj)
            
        db_session.commit()
        db_session.refresh(db_obj)
        return db_obj.code

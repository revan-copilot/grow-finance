"""
Database models for notifications.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from db.database import Base

class Notification(Base):
    """
    SQLAlchemy model representing a user notification.
    """
    __tablename__ = "sys_notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("core_users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    type = Column(String(50), nullable=False, index=True) # e.g., 'cheque_bounce', 'loan_disbursed'
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    link = Column(String(512), nullable=True) # Optional URL or internal route
    
    is_read = Column(Boolean, default=False, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = relationship("User", backref="notifications")

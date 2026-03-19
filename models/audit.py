"""
Database models for system auditing and activity logs.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from db.database import Base

class AuditLog(Base):
    """
    SQLAlchemy model for tracking staff and administrative actions.
    """
    __tablename__ = "sys_audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("core_users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False, index=True) # e.g., "Loan Approved", "Client Created"
    entity_type = Column(String(50), nullable=True) # e.g., "Loan", "Client"
    entity_id = Column(String(50), nullable=True)
    details = Column(Text, nullable=True) # JSON or descriptive string
    ip_address = Column(String(45), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    user = relationship("User")

"""
Database models for loans.

This module defines the Loan model and its attributes.
"""
from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, Numeric, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from db.database import Base

class Loan(Base):
    """
    SQLAlchemy model representing a loan.
    """
    __tablename__ = "fin_loans"
    
    id = Column(Integer, primary_key=True, index=True)
    loan_custom_id = Column(String(20), unique=True, index=True, nullable=True)
    client_id = Column(Integer, ForeignKey("core_clients.id", ondelete="RESTRICT"), nullable=False, index=True)
    
    loan_amount = Column(Numeric(12, 2), nullable=False)
    interest_rate = Column(Numeric(12, 2), nullable=False)
    commission_percentage = Column(Numeric(5, 2), nullable=False)
    commission_amount = Column(Numeric(12, 2), nullable=False)
    cutting_fee = Column(Numeric(12, 2), nullable=False)
    
    middle_man_name = Column(String(255), nullable=True)
    status = Column(String(50), default="Pending", index=True, nullable=False)
    
    frequency = Column(String(50), nullable=False, index=True)
    tenure = Column(Integer, nullable=False)
    emi_start_date = Column(Date, nullable=False, index=True)
    collection_date = Column(Integer, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    client = relationship("Client", back_populates="loans")
    repayment_schedules = relationship("RepaymentSchedule", back_populates="loan", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="loan", cascade="all, delete-orphan")

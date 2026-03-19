"""
Database models for transactions and repayment schedules.
"""
from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, Numeric, Text, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from db.database import Base

class RepaymentSchedule(Base):
    """
    SQLAlchemy model representing an EMI/Repayment schedule.
    """
    __tablename__ = "fin_repayment_schedules"
    
    id = Column(Integer, primary_key=True, index=True)
    loan_id = Column(Integer, ForeignKey("fin_loans.id", ondelete="CASCADE"), nullable=False, index=True)
    
    due_date = Column(Date, nullable=False, index=True)
    expected_amount = Column(Numeric(12, 2), nullable=False)
    principal_component = Column(Numeric(12, 2), default=0.00, nullable=False)
    interest_component = Column(Numeric(12, 2), default=0.00, nullable=False)
    balance_remaining = Column(Numeric(12, 2), default=0.00, nullable=False)
    
    status = Column(String(50), default="Pending", index=True, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    loan = relationship("Loan", back_populates="repayment_schedules")
    transactions = relationship("Transaction", back_populates="repayment_schedule")


class Transaction(Base):
    """
    SQLAlchemy model representing a loan repayment transaction.
    """
    __tablename__ = "fin_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    loan_id = Column(Integer, ForeignKey("fin_loans.id", ondelete="CASCADE"), nullable=False, index=True)
    repayment_schedule_id = Column(Integer, ForeignKey("fin_repayment_schedules.id", ondelete="SET NULL"), nullable=True, index=True)
    
    transaction_type = Column(String(50), nullable=False, default="Cash", index=True) # Cash, Cheque, Transfer
    payment_mode = Column(String(50), nullable=False, index=True)
    amount_paid = Column(Numeric(12, 2), nullable=False)
    transaction_date = Column(DateTime, nullable=False, index=True)
    description = Column(Text, nullable=True)
    remarks = Column(Text, nullable=True)
    status = Column(String(50), default="Cleared", index=True, nullable=False) # Cleared, Bounced, Pending
    
    # Cheque Details
    cheque_number = Column(String(50), nullable=True)
    bank_name = Column(String(255), nullable=True)
    cheque_date = Column(Date, nullable=True)
    clearance_date = Column(Date, nullable=True)
    
    proof_document = Column(String(100), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    loan = relationship("Loan", back_populates="transactions")
    repayment_schedule = relationship("RepaymentSchedule", back_populates="transactions")

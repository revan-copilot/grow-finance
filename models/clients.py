"""
Database models for clients and their associated data.

This module defines models for Clients, KYC, Business details, and Loan Applications.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, ForeignKey, Text, Numeric, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from db.database import Base

class Client(Base):
    """
    SQLAlchemy model representing a client.
    """
    __tablename__ = "core_clients"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, index=True, nullable=False, default=lambda: str(uuid.uuid4()))
    client_custom_id = Column(String(20), unique=True, index=True, nullable=True)
    user_id = Column(Integer, ForeignKey("core_users.id", ondelete="SET NULL"), nullable=True, unique=True)
    
    full_name = Column(String(255), index=True, nullable=False)
    mobile_number = Column(String(15), unique=True, index=True, nullable=False)
    status = Column(String(20), default="Draft", index=True, nullable=False) # e.g. Draft, Active, Inactive
    
    spouse_name = Column(String(255), nullable=True)
    marital_status = Column(String(50), nullable=True)
    dob = Column(Date, nullable=True)
    resident_address = Column(Text, nullable=True)
    permanent_address = Column(Text, nullable=True)
    
    email = Column(String(254), index=True, nullable=True)
    gender = Column(String(20), nullable=True)
    profile_picture_url = Column(String(512), nullable=True)
    alternative_mobile_number = Column(String(15), nullable=True)
    occupation = Column(String(100), nullable=True)
    
    created_by_id = Column(Integer, ForeignKey("core_users.id", ondelete="RESTRICT"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="client_profile")
    created_by_user = relationship("User", foreign_keys=[created_by_id])
    
    kyc_details = relationship("ClientKyc", back_populates="client", uselist=False, cascade="all, delete-orphan")
    business_details = relationship("Business", back_populates="client", uselist=False, cascade="all, delete-orphan")
    loan_application = relationship("LoanApplication", back_populates="client", uselist=False)
    loans = relationship("Loan", back_populates="client")


class ClientKyc(Base):
    """
    SQLAlchemy model for client KYC documentation.
    """
    __tablename__ = "core_client_kyc"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("core_clients.id", ondelete="CASCADE"), unique=True, nullable=False)
    aadhar_client = Column(String(100), nullable=True)
    aadhar_spouse = Column(String(100), nullable=True)
    pan_client = Column(String(100), nullable=True)
    pan_spouse = Column(String(100), nullable=True)
    eb_bill = Column(String(100), nullable=True)
    photo = Column(String(100), nullable=True)
    kyc_status = Column(String(50), default="Pending", index=True, nullable=False)
    
    client = relationship("Client", back_populates="kyc_details")


class Business(Base):
    """
    SQLAlchemy model for client business details.
    """
    __tablename__ = "core_businesses"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("core_clients.id", ondelete="CASCADE"), unique=True, nullable=False)
    name = Column(String(255), index=True, nullable=False)
    ownership_type = Column(String(100), nullable=False)
    nature_of_business = Column(String(255), nullable=False)
    address = Column(Text, nullable=False)
    pincode = Column(String(20), index=True, nullable=False)
    visiting_card = Column(String(100), nullable=True)
    annual_turnover = Column(Numeric(12, 2), nullable=True)
    business_start_date = Column(Date, nullable=True)
    registration_number = Column(String(100), nullable=True)
    
    client = relationship("Client", back_populates="business_details")



class LoanApplication(Base):
    """
    SQLAlchemy model for loan applications (before approval).
    """
    __tablename__ = "fin_loan_applications"
    
    id = Column(Integer, primary_key=True, index=True)
    loan_custom_id = Column(String(20), unique=True, index=True, nullable=True)
    client_id = Column(Integer, ForeignKey("core_clients.id", ondelete="RESTRICT"), nullable=False)
    
    # Tab 2: Loan Amount & Charges
    loan_amount = Column(Numeric(12, 2), nullable=False)
    interest_rate = Column(Numeric(12, 2), nullable=False)
    commission_percentage = Column(Numeric(5, 2), nullable=True)
    commission_amount = Column(Numeric(12, 2), nullable=True)
    middle_man_name = Column(String(255), nullable=True)
    cutting_fee = Column(Numeric(12, 2), nullable=True)
    
    # Tab 3: Repayment Terms
    repayment_terms = Column(String(50), nullable=False) # e.g., Monthly
    total_months = Column(Integer, nullable=False)
    loan_start_date = Column(Date, nullable=False)
    loan_collection_date = Column(Integer, nullable=False)
    
    status = Column(String(50), default="Pending Approval", index=True, nullable=False)
    purpose_of_loan = Column(String(255), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    client = relationship("Client", back_populates="loan_application")
    documents = relationship("LoanApplicationDocument", back_populates="loan_application", cascade="all, delete-orphan")


class LoanApplicationDocument(Base):
    """
    SQLAlchemy model for loan application documents.
    """
    __tablename__ = "fin_loan_application_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    loan_application_id = Column(Integer, ForeignKey("fin_loan_applications.id", ondelete="CASCADE"), nullable=False)
    document = Column(String(100), nullable=False)
    document_name = Column(String(100), nullable=False)
    
    loan_application = relationship("LoanApplication", back_populates="documents")

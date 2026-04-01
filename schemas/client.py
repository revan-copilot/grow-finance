"""
Pydantic schemas for Client management.
"""
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal

class BusinessBase(BaseModel):
    name: str
    ownership_type: str
    nature_of_business: str
    address: str
    pincode: str
    annual_turnover: Optional[Decimal] = None
    business_start_date: Optional[date] = None
    registration_number: Optional[str] = None

class BusinessCreate(BusinessBase):
    pass

class BusinessRead(BusinessBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class LoanApplicationBase(BaseModel):
    loan_amount: Decimal
    interest_rate: Decimal
    commission_percentage: Optional[Decimal] = None
    commission_amount: Optional[Decimal] = None
    middle_man_name: Optional[str] = None
    cutting_fee: Optional[Decimal] = None
    repayment_terms: str
    total_months: int
    loan_start_date: date
    loan_collection_date: int
    status: str = "Pending Approval"
    purpose_of_loan: Optional[str] = None

class LoanApplicationCreate(LoanApplicationBase):
    pass

class LoanApplicationRead(LoanApplicationBase):
    id: int
    uuid: str
    loan_custom_id: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ClientBase(BaseModel):
    full_name: str
    mobile_number: str
    status: str = "Draft"
    spouse_name: Optional[str] = None
    marital_status: Optional[str] = None
    dob: Optional[date] = None
    resident_address: Optional[str] = None
    permanent_address: Optional[str] = None
    email: Optional[EmailStr] = None
    gender: Optional[str] = None
    occupation: Optional[str] = None

class ClientCreate(ClientBase):
    # Optional business info during creation
    business: Optional[BusinessCreate] = None
    # Optional loan app during creation
    loan_application: Optional[LoanApplicationCreate] = None

class ClientRead(ClientBase):
    """
    Client schema for Staff/General view. Excludes sensitive financial config.
    """
    uuid: str
    client_custom_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    business_details: Optional[BusinessRead] = None
    
    # Enhanced fields for list view
    loan_status: Optional[str] = None
    kyc_status: Optional[str] = None
    outstanding_amount: Optional[Decimal] = Decimal("0.00")
    created_by_name: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class ClientAdminRead(ClientRead):
    """
    Client schema for Admin view. Includes full financial config.
    """
    loan_application: Optional[LoanApplicationRead] = None

"""
Pydantic schemas for EMI and Transaction management.
"""
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal

class RepaymentScheduleRead(BaseModel):
    id: int
    loan_id: int
    due_date: date
    expected_amount: Decimal
    principal_component: Decimal
    interest_component: Decimal
    balance_remaining: Decimal
    status: str
    
    model_config = ConfigDict(from_attributes=True)

class EMIScheduledRead(BaseModel):
    id: int
    loan_id: int
    loan_custom_id: Optional[str] = None
    client_name: str
    due_date: date
    expected_amount: Decimal
    status: str
    installment_no: int
    
    model_config = ConfigDict(from_attributes=True)

class TransactionRead(BaseModel):
    """Schema for reading transaction data in listing and detail views."""
    id: int
    loan_id: int
    loan_custom_id: Optional[str] = None
    client_name: Optional[str] = None
    repayment_schedule_id: Optional[int] = None
    transaction_type: str
    payment_mode: str
    amount_paid: Decimal
    transaction_date: datetime
    description: Optional[str] = None
    remarks: Optional[str] = None
    status: str
    # Cheque details
    cheque_number: Optional[str] = None
    bank_name: Optional[str] = None
    cheque_date: Optional[date] = None
    clearance_date: Optional[date] = None
    proof_document: Optional[str] = None
    created_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class TransactionDetailRead(TransactionRead):
    """Extended schema for transaction detail view with business context."""
    business_name: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class EMIOverdueRead(BaseModel):
    loan_id: int
    loan_custom_id: str
    client_name: str
    client_uuid: str
    total_overdue_amount: Decimal
    missed_emis_count: int
    last_payment_date: Optional[datetime] = None
    next_due_date: Optional[date] = None
    
    model_config = ConfigDict(from_attributes=True)

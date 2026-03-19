"""
Pydantic schemas for dashboard data.
"""
from pydantic import BaseModel
from typing import List, Optional
from decimal import Decimal
from datetime import datetime

class DashboardStat(BaseModel):
    """
    Schema for a single dashboard stat card.
    """
    label: str
    value: str
    change_text: Optional[str] = None
    change_type: Optional[str] = "neutral" # positive, negative, neutral

class RecentLoanApproval(BaseModel):
    """
    Schema for a row in the Recent Loan Approvals table.
    """
    loan_id: str
    client_name: str
    amount: Decimal
    status: str

class ClosureRequest(BaseModel):
    """
    Schema for a row in the Closure Requests table.
    """
    loan_id: str
    client_name: str
    amount: Decimal
    status: str

class DashboardData(BaseModel):
    """
    Schema for the aggregated dashboard response.
    """
    stats: List[DashboardStat]
    recent_approvals: List[RecentLoanApproval]
    closure_requests: List[ClosureRequest]

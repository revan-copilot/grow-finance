"""
Router for dashboard statistics.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, timedelta
from decimal import Decimal

from models.loans import Loan
from models.clients import Client, LoanApplication
from models.transactions import Transaction, RepaymentSchedule
from schemas.dashboard import DashboardData, DashboardStat, RecentLoanApproval, ClosureRequest
from api.deps import get_db, get_current_active_user
from models.users import User

router = APIRouter()

@router.get("/", response_model=DashboardData)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Aggregate all dashboard statistics and data.
    """
    # 1. Stats Calculation
    total_active_loans = db.query(Loan).filter(Loan.status == "Active").count()
    pending_approvals = db.query(LoanApplication).filter(LoanApplication.status == "Pending Approval").count()
    
    today = date.today()
    today_emi_collected = db.query(func.sum(Transaction.amount_paid)).filter(
        func.date(Transaction.transaction_date) == today,
        Transaction.status == "Cleared"
    ).scalar() or Decimal("0.00")
    
    total_rejected_loans = db.query(LoanApplication).filter(LoanApplication.status == "Rejected").count()
    
    overdue_loans = db.query(Loan).join(RepaymentSchedule).filter(
        Loan.status == "Active",
        RepaymentSchedule.due_date < today,
        RepaymentSchedule.status == "Pending"
    ).distinct().count()

    stats = [
        DashboardStat(label="Total Active Loans", value=f"{total_active_loans:,}", change_text="+12.5% from last month", change_type="positive"),
        DashboardStat(label="Pending Approvals", value=f"{pending_approvals}", change_text="View details", change_type="neutral"),
        DashboardStat(label="Today's EMI Collected", value=f"₹{today_emi_collected:,.2f}", change_text="+15 payment", change_type="positive"),
        DashboardStat(label="Total Rejected Loans Count", value=f"{total_rejected_loans}", change_text="+3.1% from last month", change_type="negative"),
        DashboardStat(label="Overdue Loans", value=f"{overdue_loans}", change_text="View details", change_type="negative"),
    ]

    # 2. Recent Loan Approvals
    recent_loans = db.query(Loan).join(Client).order_by(Loan.created_at.desc()).limit(4).all()
    recent_approvals = [
        RecentLoanApproval(
            loan_id=l.loan_custom_id or f"LN-{l.id}",
            client_name=l.client.full_name,
            amount=l.loan_amount,
            status=l.status
        ) for l in recent_loans
    ]

    # 3. Closure Requests (Mocking 'Pending Closure' logic if not fully implemented)
    # Using 'Pending' status as a placeholder for closure requests in this example
    closure_req_query = db.query(Loan).join(Client).filter(Loan.status == "Pending Closure").limit(4).all()
    if not closure_req_query:
        # Fallback for seeding/demo: just show some loans with 'Pending' if Closure status isn't used yet
        closure_req_query = db.query(Loan).join(Client).filter(Loan.status == "Pending").limit(4).all()

    closure_requests = [
        ClosureRequest(
            loan_id=l.loan_custom_id or f"LN-{l.id}",
            client_name=l.client.full_name,
            amount=l.loan_amount,
            status=l.status
        ) for l in closure_req_query
    ]

    return {
        "stats": stats,
        "recent_approvals": recent_approvals,
        "closure_requests": closure_requests
    }

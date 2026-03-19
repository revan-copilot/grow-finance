"""
Core logic for EMI calculations and schedule generation.
"""
from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta
from decimal import Decimal
from models.loans import Loan
from models.transactions import RepaymentSchedule

def generate_repayment_schedule(db: Session, loan: Loan):
    """
    Generates a full repayment schedule for a loan.
    Simple interest / Flat rate calculation for demo.
    """
    total_principal = loan.loan_amount
    total_months = loan.tenure
    interest_rate = loan.interest_rate / 100 # Annual rate
    
    # Monthly interest (simple)
    monthly_interest = (total_principal * interest_rate) / 12
    monthly_principal = total_principal / total_months
    total_emi = monthly_principal + monthly_interest
    
    current_balance = total_principal
    start_date = loan.emi_start_date or date.today()
    
    for i in range(1, total_months + 1):
        # Calculate next due date (approximate simple month increment)
        # In a production app, we'd use relativedelta for precise calendar months
        due_date = start_date + timedelta(days=30 * (i - 1))
        
        current_balance -= monthly_principal
        
        schedule_item = RepaymentSchedule(
            loan_id=loan.id,
            due_date=due_date,
            expected_amount=total_emi,
            principal_component=monthly_principal,
            interest_component=monthly_interest,
            balance_remaining=max(Decimal("0.00"), current_balance),
            status="Pending"
        )
        db.add(schedule_item)
    
    db.flush()

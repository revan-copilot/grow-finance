"""
EMI and Transaction Management API.
Handles repayment recording, transaction CRUD, and viewing schedules.
"""
from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date
from decimal import Decimal

from db.database import get_db
from api.deps import get_current_active_user, get_finance_staff, get_staff_or_admin
from models.users import User
from models.clients import Client
from models.loans import Loan
from models.transactions import Transaction, RepaymentSchedule
from schemas.transaction import (
    RepaymentScheduleRead, EMIScheduledRead, TransactionRead,
    TransactionDetailRead, EMIOverdueRead
)
from api.routers.notifications import create_notification

router = APIRouter()


def _serialize_transaction(t: Transaction) -> dict:
    """Helper to serialize a Transaction ORM object into a dict."""
    return {
        "id": t.id,
        "loan_id": t.loan_id,
        "loan_custom_id": t.loan.loan_custom_id if t.loan else None,
        "client_name": t.loan.client.full_name if t.loan and t.loan.client else None,
        "repayment_schedule_id": t.repayment_schedule_id,
        "transaction_type": t.transaction_type,
        "payment_mode": t.payment_mode,
        "amount_paid": t.amount_paid,
        "transaction_date": t.transaction_date,
        "description": t.description,
        "remarks": t.remarks,
        "status": t.status,
        "cheque_number": t.cheque_number,
        "bank_name": t.bank_name,
        "cheque_date": t.cheque_date,
        "clearance_date": t.clearance_date,
        "proof_document": t.proof_document,
        "created_at": t.created_at,
    }


# ─── Transaction CRUD ──────────────────────────────────────────────────────────

@router.get("/", response_model=List[TransactionRead])
def list_transactions(
    search: Optional[str] = None,
    payment_mode: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List all transactions with search, filters, and pagination.
    """
    query = db.query(Transaction).join(Loan).join(Client)

    if search:
        query = query.filter(
            or_(
                Loan.loan_custom_id.ilike(f"%{search}%"),
                Client.full_name.ilike(f"%{search}%"),
                Client.mobile_number.ilike(f"%{search}%"),
            )
        )
    if payment_mode:
        query = query.filter(Transaction.payment_mode.ilike(f"%{payment_mode}%"))
    if status:
        query = query.filter(Transaction.status.ilike(f"%{status}%"))

    # BOLA for customers
    if current_user.role.lower() == "customer":
        query = query.filter(Client.user_id == current_user.id)

    total = query.count()
    transactions = query.order_by(Transaction.transaction_date.desc()).offset(skip).limit(limit).all()

    return [_serialize_transaction(t) for t in transactions]


@router.post("/", status_code=201)
def create_transaction(
    loan_id: int = Form(...),
    transaction_type: str = Form(...),
    payment_mode: str = Form(...),
    amount: Decimal = Form(...),
    transaction_date: str = Form(...),
    description: Optional[str] = Form(None),
    status: str = Form("Cleared"),
    schedule_id: Optional[int] = Form(None),
    cheque_number: Optional[str] = Form(None),
    bank_name: Optional[str] = Form(None),
    cheque_date: Optional[str] = Form(None),
    clearance_date: Optional[str] = Form(None),
    proof: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_staff: User = Depends(get_staff_or_admin)
):
    """
    Create a new transaction. Staff or Admin only.
    """
    loan = db.query(Loan).filter(Loan.id == loan_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")

    try:
        parsed_txn_date = datetime.fromisoformat(transaction_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid transaction_date format. Use ISO format.")

    parsed_cheque_date = None
    parsed_clearance_date = None
    if cheque_date:
        try:
            parsed_cheque_date = date.fromisoformat(cheque_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid cheque_date format.")
    if clearance_date:
        try:
            parsed_clearance_date = date.fromisoformat(clearance_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid clearance_date format.")

    proof_path = None
    if proof:
        from core.storage import storage_service
        import asyncio
        loop = asyncio.new_event_loop()
        proof_path = loop.run_until_complete(
            storage_service.upload_file(proof.file, proof.filename, folder="transactions")
        )
        loop.close()

    txn = Transaction(
        loan_id=loan_id,
        repayment_schedule_id=schedule_id,
        transaction_type=transaction_type,
        payment_mode=payment_mode,
        amount_paid=amount,
        transaction_date=parsed_txn_date,
        description=description,
        status=status,
        cheque_number=cheque_number,
        bank_name=bank_name,
        cheque_date=parsed_cheque_date,
        clearance_date=parsed_clearance_date,
        proof_document=proof_path,
    )
    db.add(txn)

    if schedule_id:
        schedule_item = db.query(RepaymentSchedule).filter(
            RepaymentSchedule.id == schedule_id,
            RepaymentSchedule.loan_id == loan_id
        ).first()
        if schedule_item:
            schedule_item.status = "Paid"

    db.commit()
    db.refresh(txn)
    
    # Notification for Customer
    if loan.client.user_id:
        if txn.status == "Bounced":
            create_notification(
                db, 
                user_id=loan.client.user_id,
                type="cheque_bounce",
                title="Cheque Bounced",
                message=f"Cheque for Loan #{loan.loan_custom_id} has been rejected by bank.",
                link=f"/loans/detail/{loan.loan_custom_id}"
            )
        else:
            create_notification(
                db, 
                user_id=loan.client.user_id,
                type="emi_payment",
                title="EMI Payment Recorded",
                message=f"A payment of ₹{amount:,.2f} has been recorded for Loan #{loan.loan_custom_id}.",
                link=f"/loans/detail/{loan.loan_custom_id}"
            )
        db.commit()

    return {"status": "success", "message": "Transaction created", "data": {"id": txn.id}}


# ─── EMI Endpoints ─────────────────────────────────────────────────────────────

@router.get("/emi-scheduled", response_model=List[EMIScheduledRead])
def list_emi_scheduled(
    day: str = "today",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List scheduled EMI payments.
    """
    query = db.query(RepaymentSchedule).join(Loan)

    if day == "today":
        query = query.filter(RepaymentSchedule.due_date <= datetime.utcnow().date())

    query = query.filter(RepaymentSchedule.status == "Pending")

    if current_user.role.lower() == "customer":
        query = query.filter(Loan.client.has(user_id=current_user.id))

    schedules = query.all()

    result = []
    for s in schedules:
        all_emis = db.query(RepaymentSchedule).filter(
            RepaymentSchedule.loan_id == s.loan_id
        ).order_by(RepaymentSchedule.due_date).all()
        inst_no = next((idx + 1 for idx, item in enumerate(all_emis) if item.id == s.id), -1)

        result.append({
            "id": s.id,
            "loan_id": s.loan_id,
            "loan_custom_id": s.loan.loan_custom_id,
            "client_name": s.loan.client.full_name,
            "due_date": s.due_date,
            "expected_amount": s.expected_amount,
            "status": s.status,
            "installment_no": inst_no
        })

    return result


@router.get("/emi-history", response_model=List[TransactionRead])
def list_emi_history(
    loan_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List global EMI payment history or for a specific loan.
    """
    query = db.query(Transaction).join(Loan)

    if loan_id:
        query = query.filter(Transaction.loan_id == loan_id)

    if current_user.role.lower() == "customer":
        query = query.filter(Loan.client.has(user_id=current_user.id))

    transactions = query.order_by(Transaction.transaction_date.desc()).all()
    return [_serialize_transaction(t) for t in transactions]


@router.get("/emi-overdue", response_model=List[EMIOverdueRead])
def list_emi_overdue(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List loans with overdue EMI payments.
    """
    today = datetime.utcnow().date()
    overdue_emis = db.query(RepaymentSchedule).filter(
        RepaymentSchedule.due_date < today,
        RepaymentSchedule.status == "Pending"
    ).all()

    loan_map = {}
    for emi in overdue_emis:
        lid = emi.loan_id
        if lid not in loan_map:
            if current_user.role.lower() == "customer" and emi.loan.client.user_id != current_user.id:
                continue

            loan_map[lid] = {
                "loan_id": lid,
                "loan_custom_id": emi.loan.loan_custom_id or f"LN-{emi.loan_id}",
                "client_name": emi.loan.client.full_name,
                "client_uuid": emi.loan.client.uuid,
                "total_overdue_amount": Decimal("0.00"),
                "missed_emis_count": 0,
                "last_payment_date": None,
                "next_due_date": emi.due_date
            }
            last_p = db.query(Transaction).filter(
                Transaction.loan_id == lid
            ).order_by(Transaction.transaction_date.desc()).first()
            if last_p:
                loan_map[lid]["last_payment_date"] = last_p.transaction_date

        loan_map[lid]["total_overdue_amount"] += emi.expected_amount
        loan_map[lid]["missed_emis_count"] += 1
        if emi.due_date < loan_map[lid]["next_due_date"]:
            loan_map[lid]["next_due_date"] = emi.due_date

    return list(loan_map.values())


@router.get("/schedule/{loan_id}")
def get_repayment_schedule(
    loan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> List[RepaymentScheduleRead]:
    """
    View EMI schedule for a loan.
    """
    loan = db.query(Loan).filter(Loan.id == loan_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")

    if current_user.role.lower() == "customer" and loan.client.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return db.query(RepaymentSchedule).filter(RepaymentSchedule.loan_id == loan_id).all()


@router.post("/pay")
def record_emi_payment(
    loan_id: int = Form(...),
    schedule_id: int = Form(...),
    amount: Decimal = Form(...),
    payment_mode: str = Form(...),
    remarks: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_staff: User = Depends(get_finance_staff)
):
    """
    Record an EMI payment against a schedule.
    """
    loan = db.query(Loan).filter(Loan.id == loan_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")

    schedule_item = db.query(RepaymentSchedule).filter(
        RepaymentSchedule.id == schedule_id,
        RepaymentSchedule.loan_id == loan_id
    ).first()
    if not schedule_item:
        raise HTTPException(status_code=400, detail="Invalid schedule ID for this loan")

    try:
        transaction = Transaction(
            loan_id=loan_id,
            repayment_schedule_id=schedule_id,
            transaction_type=payment_mode,
            payment_mode=payment_mode,
            amount_paid=amount,
            transaction_date=datetime.utcnow(),
            remarks=remarks,
            status="Cleared"
        )
        db.add(transaction)
        schedule_item.status = "Paid"
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Transaction failed")

    return {"status": "success", "message": "Payment recorded successfully"}


@router.get("/history/{loan_id}")
def get_loan_payment_history(
    loan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> List[TransactionRead]:
    """
    View payment history for a specific loan.
    """
    loan = db.query(Loan).filter(Loan.id == loan_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")

    if current_user.role.lower() == "customer" and loan.client.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    transactions = db.query(Transaction).filter(Transaction.loan_id == loan_id).all()
    return [_serialize_transaction(t) for t in transactions]


# ─── Dynamic path routes (must be LAST) ────────────────────────────────────────

@router.get("/detail/{transaction_id}", response_model=TransactionDetailRead)
def get_transaction_detail(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get detailed view of a single transaction.
    """
    txn = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if current_user.role.lower() == "customer" and txn.loan.client.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    data = _serialize_transaction(txn)
    biz = txn.loan.client.business_details if txn.loan and txn.loan.client else None
    data["business_name"] = biz.name if biz else None
    return data


@router.put("/detail/{transaction_id}")
def update_transaction(
    transaction_id: int,
    transaction_type: Optional[str] = Form(None),
    payment_mode: Optional[str] = Form(None),
    amount: Optional[Decimal] = Form(None),
    description: Optional[str] = Form(None),
    status: Optional[str] = Form(None),
    cheque_number: Optional[str] = Form(None),
    bank_name: Optional[str] = Form(None),
    cheque_date: Optional[str] = Form(None),
    clearance_date: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_staff: User = Depends(get_staff_or_admin)
):
    """
    Edit a transaction. Staff or Admin only.
    """
    txn = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if transaction_type is not None: txn.transaction_type = transaction_type
    if payment_mode is not None: txn.payment_mode = payment_mode
    if amount is not None: txn.amount_paid = amount
    if description is not None: txn.description = description
    if status is not None: txn.status = status
    if cheque_number is not None: txn.cheque_number = cheque_number
    if bank_name is not None: txn.bank_name = bank_name
    if cheque_date is not None:
        txn.cheque_date = date.fromisoformat(cheque_date)
    if clearance_date is not None:
        txn.clearance_date = date.fromisoformat(clearance_date)

    db.commit()
    db.refresh(txn)

    # Notification for Customer if status changed
    if status is not None and txn.loan and txn.loan.client and txn.loan.client.user_id:
        if status == "Cleared":
            create_notification(
                db, 
                user_id=txn.loan.client.user_id,
                type="cheque_cleared",
                title="Cheque Cleared",
                message=f"Cheque for Loan #{txn.loan.loan_custom_id} has been cleared by bank.",
                link=f"/loans/detail/{txn.loan.loan_custom_id}"
            )
        elif status == "Bounced":
            create_notification(
                db, 
                user_id=txn.loan.client.user_id,
                type="cheque_bounce",
                title="Cheque Bounced",
                message=f"Cheque for Loan #{txn.loan.loan_custom_id} has been rejected by bank.",
                link=f"/loans/detail/{txn.loan.loan_custom_id}"
            )
        db.commit()

    return {"status": "success", "message": "Transaction updated", "data": _serialize_transaction(txn)}

"""
Loan Management API.
Includes endpoints for loan listing, details (pre-approval), and approval workflows.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Form, Request, UploadFile, File
from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
from datetime import datetime
from decimal import Decimal
import pandas as pd
import io

from db.database import get_db
from core.storage import storage_service
from api.deps import get_current_active_user, get_admin, get_finance_staff, get_staff_or_admin
from models.users import User
from models.clients import Client, LoanApplication, LoanApplicationDocument
from models.loans import Loan
from models.audit import AuditLog
from schemas.client import LoanApplicationRead
from api.routers.notifications import create_notification

router = APIRouter()

@router.get("/")
def list_loans(
    search: Optional[str] = None,
    loan_status: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List all loans (Applications and Approved) with filters.
    """
    # Query for applications
    app_query = db.query(LoanApplication).join(Client)
    
    if search:
        app_query = app_query.filter(
            or_(
                LoanApplication.loan_custom_id.ilike(f"%{search}%"),
                Client.full_name.ilike(f"%{search}%"),
                Client.mobile_number.ilike(f"%{search}%")
            )
        )
    
    if loan_status:
        app_query = app_query.filter(LoanApplication.status.ilike(f"%{loan_status}%"))

    # Ownership check for Customers
    if current_user.role.lower() == "customer":
        app_query = app_query.filter(Client.user_id == current_user.id)

    apps = app_query.offset(skip).limit(limit).all()
    
    return {
        "status": "success",
        "data": apps,
        "total": app_query.count()
    }

@router.get("/applications/{loan_uuid}", response_model=LoanApplicationRead)
def get_loan_application(
    loan_uuid: str, # Note: using client uuid or loan application uuid
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get detailed loan application info (the 3 tabs).
    """
    # Finding by technical UUID
    app = db.query(LoanApplication).filter(LoanApplication.uuid == loan_uuid).first()
    if not app:
        raise HTTPException(status_code=404, detail="Loan application not found")
    
    # Ownership check for Customers
    if current_user.role.lower() == "customer" and app.client.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return app

@router.patch("/applications/{loan_uuid}")
def update_loan_application(
    loan_uuid: str,
    loan_amount: Optional[Decimal] = Form(None),
    interest_rate: Optional[Decimal] = Form(None),
    commission_percentage: Optional[Decimal] = Form(None),
    middle_man_name: Optional[str] = Form(None),
    cutting_fee: Optional[Decimal] = Form(None),
    repayment_terms: Optional[str] = Form(None),
    total_months: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_admin) # Only Admin can edit details before approval
):
    """
    Edit loan application details across the 3 tabs. Restricted to Admin.
    """
    app = db.query(LoanApplication).filter(LoanApplication.uuid == loan_uuid).first()
    if not app:
        raise HTTPException(status_code=404, detail="Loan application not found")

    if loan_amount is not None: app.loan_amount = loan_amount
    if interest_rate is not None: app.interest_rate = interest_rate
    if commission_percentage is not None: app.commission_percentage = commission_percentage
    if middle_man_name is not None: app.middle_man_name = middle_man_name
    if cutting_fee is not None: app.cutting_fee = cutting_fee
    if repayment_terms is not None: app.repayment_terms = repayment_terms
    if total_months is not None: app.total_months = total_months
    
    # Auto-calculate commission amount if possible
    if app.loan_amount and app.commission_percentage:
        app.commission_amount = (app.loan_amount * app.commission_percentage) / 100

    db.commit()
    db.refresh(app)
    return {"status": "success", "message": "Loan application updated", "data": app}

@router.post("/applications/{loan_uuid}/approve")
def approve_loan(
    loan_uuid: str,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_admin)
):
    """
    Approve a loan application and move it to the Active Loans table.
    """
    # Use SELECT FOR UPDATE to prevent race conditions
    app = db.query(LoanApplication).filter(LoanApplication.uuid == loan_uuid).with_for_update().first()
    if not app:
        raise HTTPException(status_code=404, detail="Loan application not found")

    if app.status == "Active" or app.status == "Approved":
        raise HTTPException(status_code=400, detail="Loan is already processed")

    # Create active Loan record
    new_loan = Loan(
        client_id=app.client_id,
        loan_amount=app.loan_amount,
        interest_rate=app.interest_rate,
        commission_percentage=app.commission_percentage or 0,
        commission_amount=app.commission_amount or 0,
        cutting_fee=app.cutting_fee or 0,
        middle_man_name=app.middle_man_name,
        status="Active",
        frequency=app.repayment_terms,
        tenure=app.total_months,
        emi_start_date=app.loan_start_date,
        collection_date=app.loan_collection_date
    )
    
    app.status = "Active"
    db.add(new_loan)
    db.flush() # Flush to get new_loan.id
    
    from core.emi import generate_repayment_schedule
    generate_repayment_schedule(db, new_loan)
    
    # Audit Log
    audit = AuditLog(
        user_id=current_admin.id,
        action="Loan Approved",
        entity_type="Loan",
        entity_id=loan_uuid,
        details=f"Loan approved by Admin: {current_admin.full_name}",
        ip_address=request.client.host
    )
    db.add(audit)
    
    # Notification for Customer
    if app.client.user_id:
        create_notification(
            db, 
            user_id=app.client.user_id,
            type="loan_disbursed",
            title="Loan Disbursed",
            message=f"Your loan application {loan_uuid} has been approved and disbursed. Welcome to SS Traders!",
            link=f"/loans/detail/{loan_uuid}"
        )

    db.commit()
    
    return {"status": "success", "message": "Loan approved and activated"}

@router.post("/applications/{loan_uuid}/reject")
def reject_loan(
    loan_uuid: str,
    request: Request,
    reason: str = Form(...),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_admin)
):
    """
    Reject a loan application.
    """
    app = db.query(LoanApplication).filter(LoanApplication.uuid == loan_uuid).first()
    if not app:
        raise HTTPException(status_code=404, detail="Loan application not found")

    app.status = "Rejected"
    
    # Audit Log
    audit = AuditLog(
        user_id=current_admin.id,
        action="Loan Rejected",
        entity_type="Loan",
        entity_id=loan_uuid,
        details=f"Reason: {reason}",
        ip_address=request.client.host
    )
    db.add(audit)
    
    # Notification for Customer
    if app.client.user_id:
        create_notification(
            db, 
            user_id=app.client.user_id,
            type="loan_rejected",
            title="Loan Application Rejected",
            message=f"The loan application {loan_uuid} has been rejected due to {reason}.",
            link=f"/loans/applications/{loan_uuid}"
        )

    db.commit()
    
    return {"status": "success", "message": "Loan application rejected"}

@router.get("/{loan_uuid}/export")
async def export_loan_details(
    loan_uuid: str,
    format: str = "xlsx", # "xlsx" or "pdf"
    db: Session = Depends(get_db),
    current_user: User = Depends(get_staff_or_admin)
):
    """
    Export loan details as Excel or PDF.
    """
    app = db.query(LoanApplication).filter(LoanApplication.uuid == loan_uuid).first()
    if not app:
        raise HTTPException(status_code=404, detail="Loan application not found")
    
    # Ownership check for Customers (if they can export their own)
    if current_user.role.lower() == "customer" and app.client.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    filename = f"loan_{loan_uuid}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}"
    
    if format.lower() == "xlsx":
        data = {
            "Field": ["Loan ID", "Client Name", "Loan Amount", "Interest Rate", "Status", "Tenure"],
            "Value": [app.loan_custom_id, app.client.full_name, str(app.loan_amount), f"{app.interest_rate}%", app.status, f"{app.total_months} months"]
        }
        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Loan Details')
        output.seek(0)
        file_url = await storage_service.upload_file(output, filename, folder="exports")
        
    elif format.lower() == "pdf":
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        
        output = io.BytesIO()
        c = canvas.Canvas(output, pagesize=letter)
        c.drawString(100, 750, f"Loan Summary: {app.loan_custom_id}")
        c.drawString(100, 730, f"Client: {app.client.full_name}")
        c.drawString(100, 710, f"Amount: {app.loan_amount}")
        c.drawString(100, 690, f"Status: {app.status}")
        c.drawString(100, 670, f"Interest Rate: {app.interest_rate}%")
        c.save()
        output.seek(0)
        file_url = await storage_service.upload_file(output, filename, folder="exports")
    else:
        raise HTTPException(status_code=400, detail="Invalid format. Use 'xlsx' or 'pdf'.")

    return {
        "status": "success",
        "export_url": file_url,
        "message": f"Loan details exported as {format.upper()}."
    }

@router.post("/applications/{loan_uuid}/documents/upload")
async def upload_loan_documents(
    loan_uuid: str,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_staff: User = Depends(get_staff_or_admin)
):
    """
    Upload additional supporting documents for a loan application.
    """
    app = db.query(LoanApplication).filter(LoanApplication.uuid == loan_uuid).first()
    if not app:
        raise HTTPException(status_code=404, detail="Loan application not found")
    
    uploaded_docs = []
    for file in files:
        ext = file.filename.split(".")[-1]
        unique_name = f"doc_{loan_uuid}_{uuid.uuid4().hex[:6]}.{ext}"
        file_path = await storage_service.upload_file(file.file, unique_name, folder=f"loans/{loan_uuid}")
        
        db_doc = LoanApplicationDocument(
            loan_application_id=app.id,
            document=file_path,
            document_name=file.filename
        )
        db.add(db_doc)
        uploaded_docs.append({"name": file.filename, "url": file_path})
        
    db.commit()
    return {"status": "success", "message": f"{len(files)} documents uploaded", "data": uploaded_docs}

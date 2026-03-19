"""
Client management CRUD endpoints with file upload support.
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from decimal import Decimal
import uuid
from datetime import datetime, date
import pandas as pd
import io
from sqlalchemy import or_

from db.database import get_db
from api.deps import get_current_active_user, get_finance_staff, get_admin, get_staff_or_admin
from models.users import User
from models.clients import Client, Business, LoanApplication, LoanApplicationDocument, ClientKyc
from schemas.client import ClientRead, ClientAdminRead
from core.storage import storage_service

router = APIRouter()

@router.post("/", response_model=ClientRead, status_code=201)
async def create_client(
    # Client Basic Info
    full_name: str = Form(...),
    mobile_number: str = Form(...),
    status: str = Form("Draft"), # Draft or Active
    spouse_name: Optional[str] = Form(None),
    marital_status: Optional[str] = Form(None),
    dob: Optional[date] = Form(None),
    resident_address: Optional[str] = Form(None),
    permanent_address: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    gender: Optional[str] = Form(None),
    occupation: Optional[str] = Form(None),
    client_type: str = Form("Individual"), # Individual or Business
    
    # Business Info
    business_name: Optional[str] = Form(None),
    ownership_type: Optional[str] = Form(None),
    
    # Files
    profile_pic: Optional[UploadFile] = File(None),
    
    db: Session = Depends(get_db),
    # Only finance staff can add
    current_staff: User = Depends(get_finance_staff)
):
    """
    Create a new client. Restricted to Finance Staff.
    """
    existing = db.query(Client).filter(Client.mobile_number == mobile_number).first()
    if existing:
        raise HTTPException(status_code=400, detail="Client with this mobile number already exists")

    if status == "Active":
        missing_fields = []
        if not marital_status: missing_fields.append("marital_status")
        if not dob: missing_fields.append("dob")
        if not resident_address: missing_fields.append("resident_address")
        if not permanent_address: missing_fields.append("permanent_address")
        if missing_fields:
            raise HTTPException(
                status_code=400, 
                detail=f"Missing fields for Active client: {', '.join(missing_fields)}"
            )

    new_client = Client(
        full_name=full_name,
        mobile_number=mobile_number,
        status=status,
        spouse_name=spouse_name,
        marital_status=marital_status,
        dob=dob,
        resident_address=resident_address,
        permanent_address=permanent_address,
        email=email,
        gender=gender,
        occupation=occupation,
        created_by_id=current_staff.id
    )

    # Generate custom CL-XXXX ID
    db.add(new_client)
    db.flush()
    new_client.client_custom_id = f"CL-{str(new_client.id).zfill(4)}"

    if profile_pic:
        ext = profile_pic.filename.split(".")[-1]
        unique_name = f"{uuid.uuid4()}.{ext}"
        file_url = await storage_service.upload_file(profile_pic.file, unique_name, folder="profiles")
        new_client.profile_picture_url = file_url
    
    if business_name or client_type == "Business":
        business = Business(
            name=business_name or f"{full_name} Venture", 
            ownership_type=ownership_type or "Individual", 
            nature_of_business="Retail", 
            address=resident_address, 
            pincode="000000"
        )
        new_client.business_details = business

    # Mock KYC
    kyc = ClientKyc(client_id=new_client.id, kyc_status="Completed")
    new_client.kyc_details = kyc

    db.commit()
    db.refresh(new_client)
    return new_client

@router.get("/")
def list_clients(
    search: Optional[str] = None,
    client_type: Optional[str] = None,
    ownership: Optional[str] = None,
    loan_status: Optional[str] = None,
    kyc_status: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    sort_by: str = "created_at",
    order: str = "desc",
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_active_user)
):
    """
    List all clients with advanced filters, pagination, and sorting.
    """
    query = db.query(Client).filter(Client.status != "deleted")

    # Search (Client ID, Name, Mobile)
    if search:
        query = query.filter(
            or_(
                Client.client_custom_id.ilike(f"%{search}%"),
                Client.full_name.ilike(f"%{search}%"),
                Client.mobile_number.ilike(f"%{search}%")
            )
        )

    # Filters
    if client_type:
        if client_type.lower() == "business":
            query = query.filter(Client.business_details.has())
        elif client_type.lower() == "individual":
            query = query.filter(~Client.business_details.has())

    if ownership:
        query = query.join(Business).filter(Business.ownership_type.ilike(f"%{ownership}%"))

    if loan_status:
        # Check both active loans or applications
        query = query.join(LoanApplication).filter(LoanApplication.status.ilike(f"%{loan_status}%"))

    if kyc_status:
        query = query.join(ClientKyc).filter(ClientKyc.kyc_status.ilike(f"%{kyc_status}%"))

    # Sorting
    sort_attr = getattr(Client, sort_by, Client.created_at)
    if order.lower() == "asc":
        query = query.order_by(sort_attr.asc())
    else:
        query = query.order_by(sort_attr.desc())

    total = query.count()
    clients = query.offset(skip).limit(limit).all()
    
    # Calculate enhanced fields for each client
    result_data = []
    for c in clients:
        # 1. Loan Status
        # Priority: Active Loan > Pending Application > Application Status > Client Status
        l_status = "None"
        if c.loans:
            # Check if any loan is active
            active_loan = next((l for l in c.loans if l.status == "Active"), None)
            if active_loan:
                l_status = "Active"
            else:
                l_status = c.loans[0].status # Just take the first one if multiple
        elif c.loan_application:
            l_status = c.loan_application.status
        else:
            l_status = c.status # Fallback to client status

        # 2. KYC Status
        k_status = c.kyc_details.kyc_status if c.kyc_details else "Pending"

        # 3. Outstanding Amount
        # Sum of expected_amount for all Pending schedules across all active loans
        outstanding = Decimal("0.00")
        for loan in c.loans:
            if loan.status == "Active":
                pending_sum = db.query(RepaymentSchedule).filter(
                    RepaymentSchedule.loan_id == loan.id,
                    RepaymentSchedule.status == "Pending"
                ).with_entities(RepaymentSchedule.expected_amount).all()
                outstanding += sum(p[0] for p in pending_sum if p[0])

        # 4. Created By
        c_by = c.created_by_user.full_name if c.created_by_user else "System"

        # Construct response dict
        client_dict = ClientRead.model_validate(c).model_dump()
        client_dict.update({
            "loan_status": l_status,
            "kyc_status": k_status,
            "outstanding_amount": outstanding,
            "created_by_name": c_by
        })
        
        # If Admin, use Admin schema for base but we've already dumped it
        # Actually, let's just return the dict list
        result_data.append(client_dict)

    if current_user.role.lower() == "admin":
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "data": result_data
        }
            
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "data": result_data
    }

@router.get("/export")
async def export_clients(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_staff_or_admin)
):
    """
    Export all clients to Excel and return a public link. Restricted to Finance Staff.
    """
    clients = db.query(Client).all()
    
    data = []
    for c in clients:
        data.append({
            "Client ID": c.client_custom_id,
            "Client Name": c.full_name,
            "Mobile": c.mobile_number,
            "Type": "Business" if c.business_details else "Individual",
            "Business Name": c.business_details.name if c.business_details else "-",
            "Loan Status": c.loan_application.status if c.loan_application else "None",
            "KYC Status": c.kyc_details.kyc_status if c.kyc_details else "Pending"
        })

    df = pd.DataFrame(data)
    
    # Save to Excel in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Clients')
    output.seek(0)

    # Upload to storage
    filename = f"clients_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    file_url = await storage_service.upload_file(output, filename, folder="exports")

    return {
        "status": "success",
        "export_url": file_url,
        "message": "Excel report generated successfully."
    }

@router.patch("/{client_uuid}", response_model=ClientRead)
def update_client(
    client_uuid: str,
    full_name: Optional[str] = Form(None),
    mobile_number: Optional[str] = Form(None),
    status: Optional[str] = Form(None),
    marital_status: Optional[str] = Form(None),
    dob: Optional[str] = Form(None),
    resident_address: Optional[str] = Form(None),
    permanent_address: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_staff: User = Depends(get_finance_staff)
):
    """
    Update client details. Restricted to Finance Staff.
    """
    client = db.query(Client).filter(Client.uuid == client_uuid).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
        
    if full_name: client.full_name = full_name
    if mobile_number: client.mobile_number = mobile_number
    if marital_status: client.marital_status = marital_status
    if dob: client.dob = dob
    if resident_address: client.resident_address = resident_address
    if permanent_address: client.permanent_address = permanent_address
    
    # If activating the draft, or currently active, enforce completeness
    new_status = status or client.status
    if new_status == "Active":
        missing_fields = []
        if not client.marital_status: missing_fields.append("marital_status")
        if not client.dob: missing_fields.append("dob")
        if not client.resident_address: missing_fields.append("resident_address")
        if not client.permanent_address: missing_fields.append("permanent_address")
        if missing_fields:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot activate client. Missing fields: {', '.join(missing_fields)}"
            )
            
    if status:
        client.status = status
    
    db.commit()
    db.refresh(client)
    return client

@router.get("/{client_uuid}", response_model=None)
def get_client(client_uuid: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    """
    Get a specific client's details by UUID.
    Financial Config (loan_application) is only visible to Admin.
    """
    client = db.query(Client).filter(Client.uuid == client_uuid).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Ownership check for Customers
    if current_user.role.lower() == "customer" and client.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # RBAC: Use specialized schemas
    if current_user.role.lower() == "admin":
        return ClientAdminRead.model_validate(client)
        
    return ClientRead.model_validate(client)

@router.post("/{client_uuid}/loan-application")
async def add_loan_application(
    client_uuid: str,
    loan_amount: float = Form(...),
    purpose: str = Form(...),
    status: str = Form("Draft"),
    documents: List[UploadFile] = File([]),
    db: Session = Depends(get_db),
    current_staff: User = Depends(get_finance_staff) # Only staff can create apps
):
    """
    Add a loan application to a client by UUID.
    """
    client = db.query(Client).filter(Client.uuid == client_uuid).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    if client.loan_application:
        raise HTTPException(status_code=400, detail="Client already has a loan application")

    # This model needs several fields, using defaults for enterprise format demo
    loan_app = LoanApplication(
        client_id=client.id,
        loan_amount=loan_amount,
        purpose_of_loan=purpose,
        status=status,
        commission_amount=0,
        interest_rate=12,
        repayment_terms="Monthly",
        total_months=12,
        loan_start_date=datetime.now().date(),
        loan_collection_date=1,
        cutting_fee=0
    )
    db.add(loan_app)
    db.flush()
    loan_app.loan_custom_id = f"LA-{str(loan_app.id).zfill(4)}"
    db.commit()
    db.refresh(loan_app)

    # Handle multiple documents
    for doc in documents:
        ext = doc.filename.split(".")[-1]
        unique_name = f"{uuid.uuid4()}.{ext}"
        file_path = await storage_service.upload_file(doc.file, unique_name, folder=f"loans/{client.id}")
        
        db_doc = LoanApplicationDocument(
            loan_application_id=loan_app.id,
            document=file_path,
            document_name=doc.filename
        )
        db.add(db_doc)

    db.commit()
    return {"status": "success", "message": f"Loan application created as {status}"}

@router.patch("/{client_uuid}/loan", status_code=200)
async def update_loan_details(
    client_uuid: str,
    status: Optional[str] = Form(None),
    loan_amount: Optional[Decimal] = Form(None),
    interest_rate: Optional[Decimal] = Form(None),
    total_months: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_admin) # Only Admin can manage
):
    """
    Update loan details. Restricted to Admin.
    """
    client = db.query(Client).filter(Client.uuid == client_uuid).first()
    if not client or not client.loan_application:
        raise HTTPException(status_code=404, detail="Client or Loan application not found")

    loan = client.loan_application
    if status is not None:
        loan.status = status
    if loan_amount is not None:
        loan.loan_amount = loan_amount
    if interest_rate is not None:
        loan.interest_rate = interest_rate
    if total_months is not None:
        loan.total_months = total_months

    db.commit()
    db.refresh(loan)
    return {"status": "success", "message": "Loan details updated successfully", "data": loan}

@router.post("/{client_uuid}/kyc/upload")
async def upload_client_kyc(
    client_uuid: str,
    aadhar_client_file: Optional[UploadFile] = File(None),
    aadhar_spouse_file: Optional[UploadFile] = File(None),
    pan_client_file: Optional[UploadFile] = File(None),
    pan_spouse_file: Optional[UploadFile] = File(None),
    eb_bill_file: Optional[UploadFile] = File(None),
    photo_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_staff: User = Depends(get_finance_staff)
):
    """
    Upload KYC documents for a client.
    """
    client = db.query(Client).filter(Client.uuid == client_uuid).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
        
    if not client.kyc_details:
        client.kyc_details = ClientKyc(client_id=client.id)
        db.add(client.kyc_details)
        db.flush()
        
    kyc = client.kyc_details
    files_to_upload = {
        "aadhar_client": aadhar_client_file,
        "aadhar_spouse": aadhar_spouse_file,
        "pan_client": pan_client_file,
        "pan_spouse": pan_spouse_file,
        "eb_bill": eb_bill_file,
        "photo": photo_file
    }
    
    for field, file in files_to_upload.items():
        if file:
            ext = file.filename.split(".")[-1]
            unique_name = f"{field}_{client_uuid}_{uuid.uuid4().hex[:6]}.{ext}"
            file_url = await storage_service.upload_file(file.file, unique_name, folder=f"kyc/{client_uuid}")
            setattr(kyc, field, file_url)
            
    kyc.kyc_status = "Completed" # Update status to completed if files are uploaded
    db.commit()
    db.refresh(kyc)
    
    return {"status": "success", "message": "KYC documents uploaded successfully", "data": kyc}

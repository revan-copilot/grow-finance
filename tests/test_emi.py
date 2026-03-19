
import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from models.loans import Loan
from models.transactions import RepaymentSchedule, Transaction

from models.users import User
from core.security import get_password_hash

def test_emi_generation_and_listing(client, db):
    # 0. Setup Admin and User
    admin = User(
        email="admin_test@example.com",
        full_name="Admin Test",
        hashed_password=get_password_hash("admin123"),
        role="admin",
        status="active",
        is_active=True,
        is_superuser=True
    )
    db.add(admin)
    db.flush()

    # Login to get token
    login_res = client.post(
        "/api/v1/users/login",
        data={"username": "admin_test@example.com", "password": "admin123"}
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 0.1 Setup Staff for payment recording
    staff = User(
        email="staff_test@example.com",
        full_name="Staff Test",
        hashed_password=get_password_hash("staff123"),
        role="staff",
        status="active",
        is_active=True
    )
    db.add(staff)
    db.flush()
    
    # Staff login for payment headers
    staff_login_res = client.post(
        "/api/v1/users/login",
        data={"username": "staff_test@example.com", "password": "staff123"}
    )
    staff_token = staff_login_res.json()["access_token"]
    staff_headers = {"Authorization": f"Bearer {staff_token}"}

    # Setup a client and active loan
    from models.clients import Client
    test_client = Client(
        full_name="Test Customer",
        mobile_number="1234567890",
        status="Active",
        created_by_id=admin.id
    )
    db.add(test_client)
    db.flush()
    
    from core.emi import generate_repayment_schedule
    loan = Loan(
        client_id=test_client.id,
        loan_custom_id="LN-TEST-001",
        loan_amount=Decimal("100000.00"),
        interest_rate=Decimal("12.00"),
        commission_percentage=Decimal("2.00"),
        commission_amount=Decimal("2000.00"),
        cutting_fee=Decimal("500.00"),
        status="Active",
        frequency="Monthly",
        tenure=12,
        emi_start_date=date.today(),
        collection_date=5
    )
    db.add(loan)
    db.flush()
    generate_repayment_schedule(db, loan)
    db.commit()
    
    schedules = db.query(RepaymentSchedule).filter(RepaymentSchedule.loan_id == loan.id).all()
    
    # 2. Test Scheduled EMIs (Today/Past due)
    response = client.get("/api/v1/transactions/emi-scheduled", headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    print(f"DEBUG DATA: {data}")
    if not data:
        # Check all EMIs in DB
        all_db = db.query(RepaymentSchedule).all()
        print(f"DEBUG DB EMIS: {[(e.id, e.due_date, e.status) for e in all_db]}")
        print(f"DEBUG TODAY: {datetime.utcnow().date()}")
    
    assert len(data) > 0
    assert "client_name" in data[0]
    assert "installment_no" in data[0]

    # 3. Test Overdue API (Manipulate one EMI to be overdue)
    overdue_emi = schedules[0]
    overdue_emi.due_date = date.today() - timedelta(days=5)
    db.commit()
    
    response = client.get("/api/v1/transactions/emi-overdue", headers=headers)
    assert response.status_code == 200
    ov_data = response.json()["data"]
    assert len(ov_data) > 0
    assert ov_data[0]["missed_emis_count"] >= 1

    # 4. Test Payment Recording
    payload = {
        "loan_id": loan.id,
        "schedule_id": overdue_emi.id,
        "amount": overdue_emi.expected_amount,
        "payment_mode": "Cash",
        "remarks": "Test Payment"
    }
    # Note: record_payment uses Form data
    response = client.post("/api/v1/transactions/pay", data=payload, headers=staff_headers)
    assert response.status_code == 200
    
    # Verify status changed
    db.refresh(overdue_emi)
    assert overdue_emi.status == "Paid"
    
    # 5. Test History
    response = client.get("/api/v1/transactions/emi-history", headers=headers)
    assert response.status_code == 200
    hist_data = response.json()["data"]
    assert len(hist_data) > 0
    assert Decimal(hist_data[0]["amount_paid"]) == overdue_emi.expected_amount

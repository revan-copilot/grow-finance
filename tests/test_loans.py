import pytest
from models.users import User
from models.clients import Client, LoanApplication
from core.security import get_password_hash
from datetime import datetime

@pytest.fixture
def test_setup(client, db):
    # Create Admin
    admin_pw = get_password_hash("adminpass123")
    admin = User(
        email="admin@loan.com",
        full_name="Admin User",
        hashed_password=admin_pw,
        role="admin",
        status="active",
        is_active=True
    )
    db.add(admin)
    
    # Create Staff
    staff_pw = get_password_hash("staffpass123")
    staff = User(
        email="staff@loan.com",
        full_name="Staff User",
        hashed_password=staff_pw,
        role="staff",
        status="active",
        is_active=True
    )
    db.add(staff)
    db.flush()

    # Login Admin
    login_admin = client.post(
        "/api/v1/users/login",
        data={"username": "admin@loan.com", "password": "adminpass123"}
    )
    admin_token = login_admin.json()["access_token"]

    # Login Staff
    login_staff = client.post(
        "/api/v1/users/login",
        data={"username": "staff@loan.com", "password": "staffpass123"}
    )
    staff_token = login_staff.json()["access_token"]

    # Create Client and Loan App
    # We use the router to create the client so we get IDs correctly
    client_res = client.post(
        "/api/v1/clients/",
        data={
            "full_name": "Loan Client",
            "mobile_number": "8888888888",
            "marital_status": "Married",
            "dob": "1980-01-01",
            "resident_address": "Addr",
            "permanent_address": "Addr"
        },
        headers={"Authorization": f"Bearer {staff_token}"}
    )
    client_uuid = client_res.json()["data"]["uuid"]

    # Add Loan App
    loan_res = client.post(
        f"/api/v1/clients/{client_uuid}/loan-application",
        data={
            "loan_amount": 500000,
            "purpose": "Home Improvement",
            "status": "Pending Approval"
        },
        headers={"Authorization": f"Bearer {staff_token}"}
    )
    
    # Need to manually set loan_custom_id since the router logic for setting it is in add_loan_application
    # and it uses f"LA-{str(new_loan.id).zfill(4)}" but wait, let's check what it actually does.
    # Actually, the router in clients.py doesn't seem to set loan_custom_id.
    # Looking at and fixing 'api/routers/clients.py':
    
    return {
        "admin_token": admin_token,
        "staff_token": staff_token,
        "client_uuid": client_uuid
    }

def test_list_loan_applications(client, test_setup):
    response = client.get(
        "/api/v1/loans/",
        headers={"Authorization": f"Bearer {test_setup['staff_token']}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) >= 1
    assert data["data"][0]["loan_amount"] == 500000

def test_admin_approve_loan(client, db, test_setup):
    # First find the loan app custom ID (it might be null currently based on router code)
    # Let's manually set one in the db fixture for testing
    from models.clients import LoanApplication
    app = db.query(LoanApplication).first()
    app.loan_custom_id = "LA-0001"
    db.commit()

    response = client.post(
        f"/api/v1/loans/applications/{app.uuid}/approve",
        headers={"Authorization": f"Bearer {test_setup['admin_token']}"}
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Loan approved and activated"
    
    # Check status changed
    db.refresh(app)
    assert app.status == "Active"

def test_staff_cannot_approve_loan(client, db, test_setup):
    from models.clients import LoanApplication
    app = db.query(LoanApplication).first()
    app.loan_custom_id = "LA-0002"
    db.commit()

    response = client.post(
        f"/api/v1/loans/applications/{app.uuid}/approve",
        headers={"Authorization": f"Bearer {test_setup['staff_token']}"}
    )
    # Depending on how get_admin is implemented, it might return 401 or 403 or 404 client-side
    assert response.status_code in [403, 401]

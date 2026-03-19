import pytest
from models.users import User
from models.clients import Client
from core.security import get_password_hash

@pytest.fixture
def admin_token(client, db):
    hashed_pw = get_password_hash("adminpass123")
    user = User(
        email="admin@test.com",
        full_name="Admin User",
        hashed_password=hashed_pw,
        role="admin",
        status="active",
        is_active=True
    )
    db.add(user)
    db.flush()

    login_res = client.post(
        "/api/v1/users/login",
        data={"username": "admin@test.com", "password": "adminpass123"}
    )
    return login_res.json()["access_token"]

@pytest.fixture
def staff_token(client, db):
    hashed_pw = get_password_hash("staffpass123")
    user = User(
        email="staff@test.com",
        full_name="Staff User",
        hashed_password=hashed_pw,
        role="staff",
        status="active",
        is_active=True
    )
    db.add(user)
    db.flush()

    login_res = client.post(
        "/api/v1/users/login",
        data={"username": "staff@test.com", "password": "staffpass123"}
    )
    return login_res.json()["access_token"]

def test_create_client_staff_only(client, staff_token):
    response = client.post(
        "/api/v1/clients/",
        data={
            "full_name": "New Client",
            "mobile_number": "1234567890",
            "marital_status": "Single",
            "dob": "1990-01-01",
            "resident_address": "Test Address",
            "permanent_address": "Test Address",
            "client_type": "Individual"
        },
        headers={"Authorization": f"Bearer {staff_token}"}
    )
    assert response.status_code == 201
    assert response.json()["data"]["full_name"] == "New Client"

def test_staff_cannot_see_financial_config(client, db, admin_token, staff_token):
    # Admin creates a client with a loan
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    staff_headers = {"Authorization": f"Bearer {staff_token}"}
    
    # First create client
    res = client.post(
        "/api/v1/clients/",
        data={
            "full_name": "Fin Client",
            "mobile_number": "9999999999",
            "marital_status": "Single",
            "dob": "1985-01-01",
            "resident_address": "Add",
            "permanent_address": "Add",
            "client_type": "Individual"
        },
        headers=staff_headers
    )
    client_uuid = res.json()["data"]["uuid"]
    
    # Create loan app (only staff can do this in our routes currently, or admin if we didn't restrict)
    client.post(
        f"/api/v1/clients/{client_uuid}/loan-application",
        data={
            "loan_amount": 100000,
            "purpose": "Business Expansion",
            "status": "Pending Approval"
        },
        headers=staff_headers
    )
    
    # Admin should see loan details
    res_admin = client.get(f"/api/v1/clients/{client_uuid}", headers=admin_headers)
    assert res_admin.json()["data"]["loan_application"] is not None
    
    # Staff should NOT see loan details (key should be missing from response)
    res_staff = client.get(f"/api/v1/clients/{client_uuid}", headers=staff_headers)
    assert "loan_application" not in res_staff.json()["data"]

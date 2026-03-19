import pytest
from models.users import User
from core.security import get_password_hash

def test_login_success(client, db):
    # Create a test user
    hashed_pw = get_password_hash("testpassword123")
    user = User(
        email="test@example.com",
        full_name="Test User",
        hashed_password=hashed_pw,
        role="admin",
        status="active",
        is_active=True
    )
    db.add(user)
    db.flush()

    response = client.post(
        "/api/v1/users/login",
        data={"username": "test@example.com", "password": "testpassword123"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data

def test_read_profile(client, db):
    # Create and login user
    hashed_pw = get_password_hash("testpassword123")
    user = User(
        email="test2@example.com",
        full_name="Test User 2",
        hashed_password=hashed_pw,
        role="staff",
        status="active",
        is_active=True
    )
    db.add(user)
    db.flush()

    login_res = client.post(
        "/api/v1/users/login",
        data={"username": "test2@example.com", "password": "testpassword123"}
    )
    token = login_res.json()["access_token"]

    # Read profile
    response = client.get(
        "/api/v1/users/profile",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["email"] == "test2@example.com"
    assert data["data"]["full_name"] == "Test User 2"
    assert "sessions" in data["data"]

"""
Tests for the Settings API endpoints.
"""
import pytest
from models.users import User
from core.security import get_password_hash


@pytest.fixture
def admin_token(client, db):
    """
    Create an admin user and return a valid JWT token.
    """
    hashed_pw = get_password_hash("adminpass123")
    user = User(
        email="settings_admin@test.com",
        full_name="Settings Admin",
        hashed_password=hashed_pw,
        role="admin",
        status="active",
        is_active=True,
    )
    db.add(user)
    db.commit()

    login_res = client.post(
        "/api/v1/users/login",
        data={"username": "settings_admin@test.com", "password": "adminpass123"},
    )
    return login_res.json()["access_token"]


# ─── General Settings ─────────────────────────────────────────────────────────

def test_get_general_settings(client, admin_token):
    """Test retrieving general settings (auto-creates singleton)."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    res = client.get("/api/v1/settings/general", headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert "system_name" in data
    assert "company_name" in data


def test_update_general_settings(client, admin_token):
    """Test updating general settings with partial payload."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    res = client.put(
        "/api/v1/settings/general",
        json={"system_name": "New System Name"},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["system_name"] == "New System Name"


# ─── Loan Settings ────────────────────────────────────────────────────────────

def test_get_loan_settings(client, admin_token):
    """Test retrieving loan settings (auto-creates singleton)."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    res = client.get("/api/v1/settings/loan", headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert "min_loan_amount" in data
    assert "max_loan_amount" in data


def test_update_loan_settings(client, admin_token):
    """Test updating loan settings with partial payload."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    res = client.put(
        "/api/v1/settings/loan",
        json={"min_loan_amount": "75000.00", "default_interest_rate": "10.5"},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["min_loan_amount"] == "75000.00"
    assert data["default_interest_rate"] == "10.50"


# ─── Notification Settings ────────────────────────────────────────────────────

def test_get_notification_settings(client, admin_token):
    """Test retrieving notification settings."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    res = client.get("/api/v1/settings/notification", headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert "email_notifications" in data


def test_update_notification_settings(client, admin_token):
    """Test toggling notification settings."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    res = client.put(
        "/api/v1/settings/notification",
        json={"email_notifications": False},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["email_notifications"] is False


# ─── Role Permissions ─────────────────────────────────────────────────────────

def test_get_role_permissions_seeds_defaults(client, admin_token):
    """Test that fetching permissions for a new role auto-seeds defaults."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    res = client.get("/api/v1/settings/roles/staff", headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) == 7
    modules = [p["module"] for p in data]
    assert "client_management" in modules


def test_update_role_permissions(client, admin_token):
    """Test bulk-updating permissions for a role."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    # Seed defaults first
    client.get("/api/v1/settings/roles/staff", headers=headers)

    res = client.put(
        "/api/v1/settings/roles/staff",
        json={
            "permissions": [
                {"module": "audit", "access_level": "view", "can_create_edit": True}
            ]
        },
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()["data"]
    audit_perm = [p for p in data if p["module"] == "audit"][0]
    assert audit_perm["access_level"] == "view"
    assert audit_perm["can_create_edit"] is True


def test_reset_role_permissions(client, admin_token):
    """Test that resetting a role restores factory defaults."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    # First update, then reset
    client.get("/api/v1/settings/roles/staff", headers=headers)
    client.put(
        "/api/v1/settings/roles/staff",
        json={"permissions": [{"module": "audit", "access_level": "full", "can_create_edit": True}]},
        headers=headers,
    )

    res = client.post("/api/v1/settings/roles/staff/reset", headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]
    audit_perm = [p for p in data if p["module"] == "audit"][0]
    assert audit_perm["access_level"] == "none"
    assert audit_perm["can_create_edit"] is False


# ─── Authorization ─────────────────────────────────────────────────────────

def test_non_admin_cannot_access_settings(client, db):
    """Test that non-admin users are denied access to settings endpoints."""
    hashed_pw = get_password_hash("staffpass123")
    user = User(
        email="staff_settings@test.com",
        full_name="Staff User",
        hashed_password=hashed_pw,
        role="staff",
        status="active",
        is_active=True,
    )
    db.add(user)
    db.commit()

    login_res = client.post(
        "/api/v1/users/login",
        data={"username": "staff_settings@test.com", "password": "staffpass123"},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/settings/general", headers=headers)
    assert res.status_code == 403

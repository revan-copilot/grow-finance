"""
Settings API endpoints.

This module contains routers for managing system-wide settings:
General Settings, Loan Settings, Notification Settings, and
Role-based Permission mappings. All endpoints are Admin-only.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from models.settings import GeneralSettings, LoanSettings, NotificationSettings, RolePermission
from schemas.settings import (
    GeneralSettingsRead, GeneralSettingsUpdate,
    LoanSettingsRead, LoanSettingsUpdate,
    NotificationSettingsRead, NotificationSettingsUpdate,
    RolePermissionRead, RolePermissionUpdate, RolePermissionBulkUpdate,
)
from api.deps import get_db, get_admin
from models.users import User

router = APIRouter()

# ─── Default permission matrix for roles ─────────────────────────────────────

DEFAULT_STAFF_PERMISSIONS = [
    {"module": "users_management",   "access_level": "none",              "can_create_edit": False},
    {"module": "client_management",  "access_level": "create_edit_draft", "can_create_edit": True},
    {"module": "loan_management",    "access_level": "view",              "can_create_edit": True},
    {"module": "emi_payment",        "access_level": "view",              "can_create_edit": True},
    {"module": "report",             "access_level": "limited",           "can_create_edit": True},
    {"module": "audit",              "access_level": "none",              "can_create_edit": False},
    {"module": "bank_transaction",   "access_level": "none",              "can_create_edit": False},
]


def _get_or_create_singleton(db: Session, model_class):
    """
    Retrieve the singleton row for a settings model, creating it with
    defaults if it does not yet exist.

    Args:
        db: The database session.
        model_class: The SQLAlchemy model class.

    Returns:
        The singleton instance of the model.
    """
    instance = db.query(model_class).first()
    if not instance:
        instance = model_class()
        db.add(instance)
        db.commit()
        db.refresh(instance)
    return instance


# ═══════════════════════════════════ General Settings ═════════════════════════

@router.get("/general", response_model=GeneralSettingsRead)
def get_general_settings(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_admin),
):
    """
    Retrieve the current general settings (system name, company, etc.).
    """
    return _get_or_create_singleton(db, GeneralSettings)


@router.put("/general", response_model=GeneralSettingsRead)
def update_general_settings(
    payload: GeneralSettingsUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_admin),
):
    """
    Update general settings. Only provided fields are changed.
    """
    settings = _get_or_create_singleton(db, GeneralSettings)
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)
    db.commit()
    db.refresh(settings)
    return settings


# ═══════════════════════════════════ Loan Settings ════════════════════════════

@router.get("/loan", response_model=LoanSettingsRead)
def get_loan_settings(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_admin),
):
    """
    Retrieve the current loan configuration parameters.
    """
    return _get_or_create_singleton(db, LoanSettings)


@router.put("/loan", response_model=LoanSettingsRead)
def update_loan_settings(
    payload: LoanSettingsUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_admin),
):
    """
    Update loan configuration parameters. Only provided fields are changed.
    """
    settings = _get_or_create_singleton(db, LoanSettings)
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)
    db.commit()
    db.refresh(settings)
    return settings


# ═══════════════════════════════════ Notification Settings ════════════════════

@router.get("/notification", response_model=NotificationSettingsRead)
def get_notification_settings(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_admin),
):
    """
    Retrieve the current notification preferences.
    """
    return _get_or_create_singleton(db, NotificationSettings)


@router.put("/notification", response_model=NotificationSettingsRead)
def update_notification_settings(
    payload: NotificationSettingsUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_admin),
):
    """
    Update notification preferences. Only provided fields are changed.
    """
    settings = _get_or_create_singleton(db, NotificationSettings)
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)
    db.commit()
    db.refresh(settings)
    return settings


# ═══════════════════════════════════ Role Permissions ═════════════════════════

def _ensure_role_permissions(db: Session, role: str) -> List[RolePermission]:
    """
    Ensure that permission rows exist for a given role.
    If no rows are found for the role, seed them from defaults.

    Args:
        db: The database session.
        role: The role name (e.g., 'staff').

    Returns:
        List of RolePermission instances for the role.
    """
    existing = db.query(RolePermission).filter(RolePermission.role == role).all()
    if not existing:
        defaults = DEFAULT_STAFF_PERMISSIONS  # fallback defaults
        for perm in defaults:
            db.add(RolePermission(role=role, **perm))
        db.commit()
        existing = db.query(RolePermission).filter(RolePermission.role == role).all()
    return existing


@router.get("/roles", response_model=List[RolePermissionRead])
def list_all_role_permissions(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_admin),
):
    """
    List permissions for all roles.
    """
    return db.query(RolePermission).order_by(RolePermission.role, RolePermission.module).all()


@router.get("/roles/{role}", response_model=List[RolePermissionRead])
def get_role_permissions(
    role: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_admin),
):
    """
    Get the permission matrix for a specific role.
    Seeds default permissions if none exist.
    """
    return _ensure_role_permissions(db, role.lower())


@router.put("/roles/{role}", response_model=List[RolePermissionRead])
def update_role_permissions(
    role: str,
    payload: RolePermissionBulkUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_admin),
):
    """
    Bulk-update the permission matrix for a role.
    Creates missing permission rows; updates existing ones.
    """
    role_lower = role.lower()
    _ensure_role_permissions(db, role_lower)

    for perm_update in payload.permissions:
        existing = (
            db.query(RolePermission)
            .filter(RolePermission.role == role_lower, RolePermission.module == perm_update.module)
            .first()
        )
        if existing:
            if perm_update.access_level is not None:
                existing.access_level = perm_update.access_level
            if perm_update.can_create_edit is not None:
                existing.can_create_edit = perm_update.can_create_edit
        else:
            db.add(RolePermission(
                role=role_lower,
                module=perm_update.module,
                access_level=perm_update.access_level or "none",
                can_create_edit=perm_update.can_create_edit or False,
            ))

    db.commit()
    return db.query(RolePermission).filter(RolePermission.role == role_lower).order_by(RolePermission.module).all()


@router.post("/roles/{role}/reset", response_model=List[RolePermissionRead])
def reset_role_permissions(
    role: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_admin),
):
    """
    Reset a role's permissions back to factory defaults.
    Deletes all existing permissions for the role and re-seeds them.
    """
    role_lower = role.lower()
    db.query(RolePermission).filter(RolePermission.role == role_lower).delete()
    db.commit()
    return _ensure_role_permissions(db, role_lower)

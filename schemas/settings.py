"""
Pydantic schemas for settings-related data transfer objects (DTOs).

This module defines schemas for General Settings, Loan Settings,
Notification Settings, and Role Permission read/update operations.
"""
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from typing import Optional, List
from decimal import Decimal
from datetime import datetime


# ─── General Settings ────────────────────────────────────────────────────────

class GeneralSettingsRead(BaseModel):
    """
    Schema for reading general settings.
    """
    system_name: str
    company_name: str
    support_email: str
    default_currency: str
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GeneralSettingsUpdate(BaseModel):
    """
    Schema for updating general settings. All fields are optional.
    """
    system_name: Optional[str] = None
    company_name: Optional[str] = None
    support_email: Optional[EmailStr] = None
    default_currency: Optional[str] = None


# ─── Loan Settings ───────────────────────────────────────────────────────────

class LoanSettingsRead(BaseModel):
    """
    Schema for reading loan configuration settings.
    """
    min_loan_amount: Decimal
    max_loan_amount: Decimal
    default_interest_rate: Decimal
    max_loan_tenure_months: int
    processing_fee_percentage: Decimal
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LoanSettingsUpdate(BaseModel):
    """
    Schema for updating loan configuration settings. All fields are optional.
    """
    min_loan_amount: Optional[Decimal] = Field(None, max_digits=12, decimal_places=2)
    max_loan_amount: Optional[Decimal] = Field(None, max_digits=12, decimal_places=2)
    default_interest_rate: Optional[Decimal] = Field(None, max_digits=5, decimal_places=2)
    max_loan_tenure_months: Optional[int] = Field(None, gt=0)
    processing_fee_percentage: Optional[Decimal] = Field(None, max_digits=5, decimal_places=2)


# ─── Notification Settings ──────────────────────────────────────────────────

class NotificationSettingsRead(BaseModel):
    """
    Schema for reading notification preferences.
    """
    email_notifications: bool
    overdue_payment_alerts: bool
    new_loan_application_alerts: bool
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationSettingsUpdate(BaseModel):
    """
    Schema for updating notification preferences. All fields are optional.
    """
    email_notifications: Optional[bool] = None
    overdue_payment_alerts: Optional[bool] = None
    new_loan_application_alerts: Optional[bool] = None


# ─── Role Permissions ────────────────────────────────────────────────────────

class RolePermissionRead(BaseModel):
    """
    Schema for reading a single role-module permission mapping.
    """
    id: int
    role: str
    module: str
    access_level: str
    can_create_edit: bool

    model_config = ConfigDict(from_attributes=True)


class RolePermissionUpdate(BaseModel):
    """
    Schema for updating a single module permission within a role.
    """
    module: str
    access_level: Optional[str] = None
    can_create_edit: Optional[bool] = None


class RolePermissionBulkUpdate(BaseModel):
    """
    Schema for bulk-updating all module permissions for a role.
    """
    permissions: List[RolePermissionUpdate]

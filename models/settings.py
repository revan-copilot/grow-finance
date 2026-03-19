"""
Database models for system settings and role-based permissions.

This module defines models for General Settings, Loan Settings,
Notification Settings, and Role-Permission mappings used to control
access across the application.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Numeric, UniqueConstraint
from datetime import datetime
from db.database import Base


class GeneralSettings(Base):
    """
    Singleton model for global application settings.

    Stores system-wide configuration like company name, support email,
    and default currency.
    """
    __tablename__ = "sys_general_settings"

    id = Column(Integer, primary_key=True, index=True)
    system_name = Column(String(255), nullable=False, default="Finance Admin System")
    company_name = Column(String(255), nullable=False, default="Finance Solutions Inc.")
    support_email = Column(String(254), nullable=False, default="support@financeapp.com")
    default_currency = Column(String(50), nullable=False, default="Indian")

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class LoanSettings(Base):
    """
    Singleton model for loan configuration parameters.

    Stores the constraints and defaults used when creating or validating
    loan applications (e.g., min/max amounts, interest rate, tenure).
    All monetary and rate fields use Numeric for financial precision.
    """
    __tablename__ = "sys_loan_settings"

    id = Column(Integer, primary_key=True, index=True)
    min_loan_amount = Column(Numeric(12, 2), nullable=False, default=50000)
    max_loan_amount = Column(Numeric(12, 2), nullable=False, default=10000000)
    default_interest_rate = Column(Numeric(5, 2), nullable=False, default=12.5)
    max_loan_tenure_months = Column(Integer, nullable=False, default=60)
    processing_fee_percentage = Column(Numeric(5, 2), nullable=False, default=1.0)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class NotificationSettings(Base):
    """
    Singleton model for notification preferences.

    Controls which system-wide notification channels and alert types are active.
    """
    __tablename__ = "sys_notification_settings"

    id = Column(Integer, primary_key=True, index=True)
    email_notifications = Column(Boolean, nullable=False, default=True)
    overdue_payment_alerts = Column(Boolean, nullable=False, default=True)
    new_loan_application_alerts = Column(Boolean, nullable=False, default=True)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class RolePermission(Base):
    """
    Model mapping a role to a module with specific access levels.

    Each row defines what a given role (e.g., 'staff') can do within
    a specific module (e.g., 'client_management'). The combination of
    role + module is unique.

    Access levels:
        - none: No access to the module.
        - view: Read-only access.
        - limited: Restricted access (e.g., own data only).
        - create_edit_draft: Can create and edit drafts but not approve.
        - full: Full CRUD access.
    """
    __tablename__ = "sys_role_permissions"

    id = Column(Integer, primary_key=True, index=True)
    role = Column(String(50), nullable=False, index=True)
    module = Column(String(100), nullable=False, index=True)
    access_level = Column(String(50), nullable=False, default="none")
    can_create_edit = Column(Boolean, nullable=False, default=False)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("role", "module", name="uq_role_module"),
    )

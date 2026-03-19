"""seed_default_settings

Revision ID: 07aa99790dc3
Revises: 3fef1024c366
Create Date: 2026-03-11 19:20:57.223612

"""
from typing import Sequence, Union
from datetime import datetime

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '07aa99790dc3'
down_revision: Union[str, Sequence[str], None] = '3fef1024c366'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

now = datetime.utcnow()


def upgrade() -> None:
    """Seed default rows for General, Loan, Notification settings and Finance Staff permissions."""

    # General Settings
    op.execute(
        sa.text(
            "INSERT INTO sys_general_settings (system_name, company_name, support_email, default_currency, updated_at) "
            "VALUES (:sn, :cn, :se, :dc, :ua)"
        ).bindparams(
            sn="Finance Admin System",
            cn="Finance Solutions Inc.",
            se="support@financeapp.com",
            dc="Indian",
            ua=now,
        )
    )

    # Loan Settings
    op.execute(
        sa.text(
            "INSERT INTO sys_loan_settings (min_loan_amount, max_loan_amount, default_interest_rate, max_loan_tenure_months, processing_fee_percentage, updated_at) "
            "VALUES (:mn, :mx, :ir, :mt, :pf, :ua)"
        ).bindparams(
            mn=50000,
            mx=10000000,
            ir=12.5,
            mt=60,
            pf=1.0,
            ua=now,
        )
    )

    # Notification Settings
    op.execute(
        sa.text(
            "INSERT INTO sys_notification_settings (email_notifications, overdue_payment_alerts, new_loan_application_alerts, updated_at) "
            "VALUES (:en, :op, :nl, :ua)"
        ).bindparams(
            en=True,
            op=True,
            nl=True,
            ua=now,
        )
    )

    # Finance Staff Role Permissions — matches the UI screenshot
    staff_perms = [
        ("staff", "users_management",   "none",              False),
        ("staff", "client_management",  "create_edit_draft", True),
        ("staff", "loan_management",    "view",              True),
        ("staff", "emi_payment",        "view",              True),
        ("staff", "report",             "limited",           True),
        ("staff", "audit",              "none",              False),
        ("staff", "bank_transaction",   "none",              False),
    ]
    for role, module, access, can_edit in staff_perms:
        op.execute(
            sa.text(
                "INSERT INTO sys_role_permissions (role, module, access_level, can_create_edit, updated_at) "
                "VALUES (:r, :m, :al, :ce, :ua)"
            ).bindparams(r=role, m=module, al=access, ce=can_edit, ua=now)
        )


def downgrade() -> None:
    """Remove seeded default settings."""
    op.execute("DELETE FROM sys_role_permissions WHERE role = 'staff'")
    op.execute("DELETE FROM sys_notification_settings")
    op.execute("DELETE FROM sys_loan_settings")
    op.execute("DELETE FROM sys_general_settings")

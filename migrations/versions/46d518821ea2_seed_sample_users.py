"""Seed sample users

Revision ID: 46d518821ea2
Revises: a25f0d627aec
Create Date: 2026-03-04 02:24:41.018752

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '46d518821ea2'
down_revision: Union[str, Sequence[str], None] = 'a25f0d627aec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


import uuid
from datetime import datetime
from core.security import get_password_hash

def upgrade() -> None:
    """Add sample users."""
    user_table = sa.table(
        "core_users",
        sa.column("uuid", sa.String),
        sa.column("email", sa.String),
        sa.column("full_name", sa.String),
        sa.column("role", sa.String),
        sa.column("status", sa.String),
        sa.column("is_staff", sa.Boolean),
        sa.column("is_active", sa.Boolean),
        sa.column("is_superuser", sa.Boolean),
        sa.column("hashed_password", sa.String),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )

    op.bulk_insert(
        user_table,
        [
            {
                "uuid": str(uuid.uuid4()),
                "email": "admin@finance.com",
                "full_name": "System Administrator",
                "role": "admin",
                "status": "active",
                "is_staff": True,
                "is_active": True,
                "is_superuser": True,
                "hashed_password": get_password_hash("AdminPassword@123"),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
            {
                "uuid": str(uuid.uuid4()),
                "email": "staff1@finance.com",
                "full_name": "Sarah Finance",
                "role": "finance_staff",
                "status": "active",
                "is_staff": True,
                "is_active": True,
                "is_superuser": False,
                "hashed_password": get_password_hash("StaffPassword@123"),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
            {
                "uuid": str(uuid.uuid4()),
                "email": "staff2@finance.com",
                "full_name": "John Audit",
                "role": "finance_staff",
                "status": "active",
                "is_staff": True,
                "is_active": True,
                "is_superuser": False,
                "hashed_password": get_password_hash("StaffPassword@123"),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        ]
    )


def downgrade() -> None:
    """Remove sample users."""
    op.execute("DELETE FROM core_users WHERE email IN ('admin@finance.com', 'staff1@finance.com', 'staff2@finance.com')")

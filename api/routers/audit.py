"""
Audit Log API.
Allows Admins to view system activity logs.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from db.database import get_db
from api.deps import get_admin
from models.audit import AuditLog
from models.users import User

router = APIRouter()

@router.get("/")
def list_audit_logs(
    skip: int = 0,
    limit: int = 50,
    action: Optional[str] = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_admin)
):
    """
    List system audit logs. Restricted to Admins.
    """
    query = db.query(AuditLog)
    
    if action:
        query = query.filter(AuditLog.action.ilike(f"%{action}%"))
        
    query = query.order_by(AuditLog.created_at.desc())
    
    total = query.count()
    logs = query.offset(skip).limit(limit).all()
    
    return {
        "status": "success",
        "total": total,
        "data": logs
    }

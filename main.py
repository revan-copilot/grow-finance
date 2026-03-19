"""
Main entry point for the Grow Finance FastAPI application.

This module initializes the FastAPI app, configures middleware,
initializes the database, and includes the API routers.
"""
import logging
import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings
from api.routers import (
    users, clients, loans, audit, transactions, storage, 
    dashboard, notifications
)
from api.routers import settings as settings_router
from db.database import engine, Base

# Set up logging to output to console
logging.basicConfig(level=logging.INFO)

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize DB
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown logic (if any) could go here

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan
)

# Helper for including routers under the API prefix
api_router = FastAPI() # We can use a sub-app or simply include directly in app with prefix

@app.middleware("http")
async def security_and_envelope_middleware(request: Request, call_next):
    """
    1. Standardize response envelope
    2. Add Security Headers
    """
    path = request.url.path
    skip_wrapping = any(path.startswith(p) for p in [
        f"{settings.API_V1_STR}/docs", 
        f"{settings.API_V1_STR}/redoc", 
        f"{settings.API_V1_STR}/openapi.json",
        f"{settings.API_V1_STR}/users/login"
    ]) or path.endswith("/openapi.json") or "/docs" in path or "/redoc" in path

    response = await call_next(request)

    # Apply Security Headers to every response
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    if skip_wrapping or response.headers.get("content-type") != "application/json":
        return response

    import json
    body = b""
    async for chunk in response.body_iterator:
        body += chunk
    
    try:
        data = json.loads(body)
        # If not already wrapped, wrap it
        if not (isinstance(data, dict) and "status" in data and ("data" in data or "message" in data)):
            new_body = {
                "status": "success" if response.status_code < 400 else "error",
                "data": data if response.status_code < 400 else {},
                "message": data.get("detail") if response.status_code >= 400 and isinstance(data, dict) else None
            }
            headers = {k: v for k, v in response.headers.items() if k.lower() not in ["content-length", "content-type", "transfer-encoding", "content-encoding"]}
            return JSONResponse(status_code=response.status_code, content=new_body, headers=headers)
        else:
            # Already wrapped, but we consumed the body, so we must return a new response with the body
            headers = {k: v for k, v in response.headers.items() if k.lower() not in ["content-length", "content-type", "transfer-encoding", "content-encoding"]}
            return JSONResponse(status_code=response.status_code, content=data, headers=headers)
    except:
        # Fallback for non-JSON or invalid JSON after all
        from fastapi.responses import Response
        headers = {k: v for k, v in response.headers.items() if k.lower() not in ["content-length", "transfer-encoding", "content-encoding"]}
        return Response(content=body, status_code=response.status_code, headers=headers, media_type=response.media_type)

# CORS - Restricted in production, allowed for local dev
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8080").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles

app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["users"])
app.include_router(clients.router, prefix=f"{settings.API_V1_STR}/clients", tags=["clients"])
app.include_router(loans.router, prefix=f"{settings.API_V1_STR}/loans", tags=["loans"])
app.include_router(audit.router, prefix=f"{settings.API_V1_STR}/audit", tags=["audit"])
app.include_router(transactions.router, prefix=f"{settings.API_V1_STR}/transactions", tags=["transactions"])
app.include_router(storage.router, prefix=f"{settings.API_V1_STR}/view-uploads", tags=["storage"])
app.include_router(dashboard.router, prefix=f"{settings.API_V1_STR}/dashboard", tags=["dashboard"])
app.include_router(notifications.router, prefix=f"{settings.API_V1_STR}/notifications", tags=["notifications"])
app.include_router(settings_router.router, prefix=f"{settings.API_V1_STR}/settings", tags=["settings"])

# Ensure upload path exists but do NOT mount StaticFiles publicly
if not os.path.exists(settings.LOCAL_STORAGE_PATH):
    os.makedirs(settings.LOCAL_STORAGE_PATH)
# app.mount("/view-uploads", StaticFiles(directory=settings.LOCAL_STORAGE_PATH), name="uploads")

@app.get("/")
def root():
    return {"message": "Welcome to Grow Finance API"}

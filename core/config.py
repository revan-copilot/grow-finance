"""
Configuration management for the application.

This module defines the settings for the application using Pydantic BaseSettings,
which handles environment variables and default values.
"""
import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Project settings and configuration validator.
    """
    PROJECT_NAME: str = "Grow Finance API"
    API_V1_STR: str = "/api/v1"
    
    # SECURITY WARNING: keep the secret key used in production secret!
    SECRET_KEY: str = "django-insecure-g!&ipj9b#tc+4m=@*0@bn141$r)%wm5-k&)yan40_loux9gcza"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8 # 8 days
    
    # DB
    DB_USER: str = "grow_user"
    DB_PASSWORD: str = "grow_password"
    DB_HOST: str = "db"
    DB_PORT: str = "5432"
    DB_NAME: str = "grow_db"
    
    SQLALCHEMY_DATABASE_URI: str = ""

    def model_post_init(self, __context):
        if not self.SQLALCHEMY_DATABASE_URI:
            self.SQLALCHEMY_DATABASE_URI = f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="allow")

    # Storage Settings
    STORAGE_BACKEND: str = "local"  # "local" or "s3"
    LOCAL_STORAGE_PATH: str = "uploads"
    API_BASE_URL: str = "http://localhost:8008"

    # S3 / MinIO Settings
    S3_BUCKET: str = "finance-uploads"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    S3_ENDPOINT_URL: str = ""       # Internal Docker URL: http://minio:9000
    MINIO_PUBLIC_URL: str = ""      # External browser URL: http://localhost:9000
    
settings = Settings()

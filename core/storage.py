"""
Storage service abstraction for local and S3 storage.
"""
import os
import shutil
import boto3
from typing import BinaryIO
from botocore.exceptions import NoCredentialsError
from core.config import settings

class StorageService:
    def __init__(self):
        self.backend = settings.STORAGE_BACKEND
        self.local_path = settings.LOCAL_STORAGE_PATH
        
        if self.backend == "s3":
            self.s3_client = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION,
                endpoint_url=settings.S3_ENDPOINT_URL if settings.S3_ENDPOINT_URL else None
            )

    async def upload_file(self, file: BinaryIO, filename: str, folder: str = "general") -> str:
        """
        Upload a file to the configured backend.
        Returns the file URL or path.
        """
        key = f"{folder}/{filename}"
        
        if self.backend == "s3":
            try:
                self.s3_client.upload_fileobj(file, settings.S3_BUCKET, key)
                # Return S3 URL (assuming bucket is public or handled via CDN/Presigned)
                if settings.S3_ENDPOINT_URL:
                   return f"{settings.S3_ENDPOINT_URL}/{settings.S3_BUCKET}/{key}"
                return f"https://{settings.S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"
            except NoCredentialsError:
                raise Exception("AWS credentials not found.")
        else:
            # Local storage
            full_dir = os.path.join(self.local_path, folder)
            os.makedirs(full_dir, exist_ok=True)
            full_path = os.path.join(full_dir, filename)
            
            with open(full_path, "wb") as buffer:
                shutil.copyfileobj(file, buffer)
            
            # Return public endpoint URL
            return f"{settings.API_BASE_URL}/view-uploads/{folder}/{filename}"

    def delete_file(self, file_path: str):
        """
        Delete a file from the backend.
        """
        if self.backend == "s3":
            # Extract key from URL
            key = file_path.split("/")[-1] # Simplification
            self.s3_client.delete_object(Bucket=settings.S3_BUCKET, Key=key)
        else:
            if os.path.exists(file_path):
                os.remove(file_path)

storage_service = StorageService()

"""
Storage service abstraction for local and MinIO/S3 storage.
"""
import os
import shutil
import logging
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from botocore.client import Config
from typing import BinaryIO
from core.config import settings

logger = logging.getLogger(__name__)


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
                endpoint_url=settings.S3_ENDPOINT_URL or None,
                # Required for MinIO presigned URLs to work correctly
                config=Config(signature_version="s3v4")
            )
            self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """Create the S3/MinIO bucket if it does not already exist."""
        try:
            self.s3_client.head_bucket(Bucket=settings.S3_BUCKET)
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code in ("404", "NoSuchBucket"):
                try:
                    self.s3_client.create_bucket(Bucket=settings.S3_BUCKET)
                    logger.info("Created bucket: %s", settings.S3_BUCKET)
                except ClientError as create_err:
                    logger.error("Failed to create bucket %s: %s", settings.S3_BUCKET, create_err)
                    raise
            else:
                logger.error("Error checking bucket %s: %s", settings.S3_BUCKET, e)
                raise

    def _api_file_url(self, folder: str, filename: str) -> str:
        """Return the API-proxied URL used to serve the file to clients."""
        return f"{settings.API_BASE_URL}{settings.API_V1_STR}/view-uploads/{folder}/{filename}"

    async def upload_file(self, file: BinaryIO, filename: str, folder: str = "general") -> str:
        """
        Upload a file to the configured backend.
        Returns the API proxy URL so the stored URL is always consistent.
        """
        key = f"{folder}/{filename}"

        if self.backend == "s3":
            try:
                self.s3_client.upload_fileobj(file, settings.S3_BUCKET, key)
                logger.info("Uploaded %s to MinIO bucket %s", key, settings.S3_BUCKET)
            except NoCredentialsError:
                raise Exception("Storage credentials not found.")
            except ClientError as e:
                logger.error("Failed to upload %s: %s", key, e)
                raise
        else:
            full_dir = os.path.join(self.local_path, folder)
            os.makedirs(full_dir, exist_ok=True)
            full_path = os.path.join(full_dir, filename)
            with open(full_path, "wb") as buffer:
                shutil.copyfileobj(file, buffer)

        return self._api_file_url(folder, filename)

    def get_presigned_url(self, folder: str, filename: str, expiry: int = 3600) -> str:
        """
        Generate a presigned URL for a MinIO/S3 object.
        Replaces the internal Docker endpoint with the public MinIO URL so browsers can reach it.
        """
        key = f"{folder}/{filename}"
        url = self.s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.S3_BUCKET, "Key": key},
            ExpiresIn=expiry,
        )
        # Swap internal Docker hostname (http://minio:9000) for the public URL (http://localhost:9000)
        if settings.S3_ENDPOINT_URL and settings.MINIO_PUBLIC_URL:
            url = url.replace(settings.S3_ENDPOINT_URL, settings.MINIO_PUBLIC_URL)
        return url

    def delete_file(self, file_url: str):
        """
        Delete a file given its API proxy URL or S3 key path.
        Extracts folder/filename from the URL to determine the object key.
        """
        if self.backend == "s3":
            # URL pattern: .../view-uploads/{folder}/{filename}
            marker = "/view-uploads/"
            if marker in file_url:
                key = file_url.split(marker, 1)[1]
            else:
                key = file_url  # fallback: treat as raw key
            try:
                self.s3_client.delete_object(Bucket=settings.S3_BUCKET, Key=key)
                logger.info("Deleted %s from MinIO bucket %s", key, settings.S3_BUCKET)
            except ClientError as e:
                logger.error("Failed to delete %s: %s", key, e)
        else:
            # For local storage derive the filesystem path from the URL
            marker = "/view-uploads/"
            if marker in file_url:
                relative = file_url.split(marker, 1)[1]
                file_path = os.path.join(self.local_path, relative)
            else:
                file_path = file_url  # fallback: treat as absolute path
            if os.path.exists(file_path):
                os.remove(file_path)


storage_service = StorageService()

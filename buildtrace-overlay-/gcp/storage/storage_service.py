import os
import io
import logging
from typing import Optional, BinaryIO, List
from datetime import datetime, timedelta
from google.cloud import storage
from google.cloud.exceptions import NotFound
import mimetypes

logger = logging.getLogger(__name__)

class CloudStorageService:
    """Service for handling Google Cloud Storage operations"""

    def __init__(self, bucket_name: Optional[str] = None):
        self.bucket_name = bucket_name or os.getenv('GCS_BUCKET_NAME', 'buildtrace-storage')
        self.client = None
        self.bucket = None
        self.initialize()

    def initialize(self):
        """Initialize GCS client and bucket"""
        try:
            # Initialize client with explicit credential detection
            logger.info("Initializing GCS client...")

            # Force the client to use default credentials (service account in Cloud Run)
            self.client = storage.Client()

            # Test credentials by attempting to get the bucket
            self.bucket = self.client.bucket(self.bucket_name)

            # Test access by checking if bucket exists (this validates credentials)
            try:
                bucket_exists = self.bucket.exists()
                logger.info(f"Bucket {self.bucket_name} exists: {bucket_exists}")
                if not bucket_exists:
                    logger.warning(f"Bucket {self.bucket_name} does not exist, but client is authenticated")
            except Exception as bucket_error:
                logger.error(f"Failed to access bucket {self.bucket_name}: {bucket_error}")
                raise

            logger.info(f"Cloud Storage initialized successfully with bucket: {self.bucket_name}")

        except Exception as e:
            logger.error(f"Failed to initialize Cloud Storage: {str(e)}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")

            # Only fall back to None in development
            if os.getenv('ENVIRONMENT') == 'development':
                logger.warning("Falling back to local storage for development")
                self.client = None
                self.bucket = None
            else:
                # In production, don't fall back - we need GCS to work
                logger.error("Cloud Storage is required in production mode")
                raise

    def upload_file(self, file_content: BinaryIO, destination_path: str,
                   content_type: Optional[str] = None) -> str:
        """
        Upload file to GCS
        Returns: Public URL or GCS URI
        """
        if not self.bucket:
            # Fallback to local storage
            return self._save_local_file(file_content, destination_path)

        try:
            blob = self.bucket.blob(destination_path)

            # Set content type if provided
            if content_type:
                blob.content_type = content_type
            else:
                # Try to guess content type
                content_type, _ = mimetypes.guess_type(destination_path)
                if content_type:
                    blob.content_type = content_type

            # Upload file
            if isinstance(file_content, bytes):
                blob.upload_from_string(file_content)
            else:
                blob.upload_from_file(file_content, rewind=True)

            logger.info(f"File uploaded to GCS: {destination_path}")
            return f"gs://{self.bucket_name}/{destination_path}"

        except Exception as e:
            logger.error(f"Failed to upload file to GCS: {str(e)}")
            raise

    def upload_from_filename(self, local_path: str, destination_path: str) -> str:
        """Upload file from local filesystem to GCS"""
        if not self.bucket:
            return self._copy_local_file(local_path, destination_path)

        try:
            blob = self.bucket.blob(destination_path)
            blob.upload_from_filename(local_path)
            logger.info(f"File uploaded from {local_path} to GCS: {destination_path}")
            return f"gs://{self.bucket_name}/{destination_path}"

        except Exception as e:
            logger.error(f"Failed to upload file from {local_path}: {str(e)}")
            raise

    def download_file(self, source_path: str) -> bytes:
        """Download file from GCS as bytes"""
        if not self.bucket:
            return self._read_local_file(source_path)

        try:
            blob = self.bucket.blob(source_path)
            content = blob.download_as_bytes()
            logger.info(f"File downloaded from GCS: {source_path}")
            return content

        except NotFound:
            logger.error(f"File not found in GCS: {source_path}")
            raise
        except Exception as e:
            logger.error(f"Failed to download file from GCS: {str(e)}")
            raise

    def download_to_file(self, source_path: str, destination_file: BinaryIO):
        """Download file from GCS to a file object"""
        if not self.bucket:
            content = self._read_local_file(source_path)
            destination_file.write(content)
            return

        try:
            blob = self.bucket.blob(source_path)
            blob.download_to_file(destination_file)
            logger.info(f"File downloaded from GCS to file object: {source_path}")

        except Exception as e:
            logger.error(f"Failed to download file to file object: {str(e)}")
            raise

    def download_to_filename(self, source_path: str, local_path: str) -> bool:
        """Download file from GCS to local filesystem"""
        if not self.bucket:
            try:
                self._copy_from_local(source_path, local_path)
                return True
            except Exception as e:
                logger.error(f"Failed to copy local file: {str(e)}")
                return False

        try:
            blob = self.bucket.blob(source_path)
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            blob.download_to_filename(local_path)
            logger.info(f"File downloaded from GCS to {local_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to download file to {local_path}: {str(e)}")
            return False

    def file_exists(self, path: str) -> bool:
        """Check if file exists in GCS"""
        if not self.bucket:
            return self._local_file_exists(path)

        try:
            blob = self.bucket.blob(path)
            return blob.exists()
        except Exception as e:
            logger.error(f"Error checking file existence: {str(e)}")
            return False

    def delete_file(self, path: str) -> bool:
        """Delete file from GCS"""
        if not self.bucket:
            return self._delete_local_file(path)

        try:
            blob = self.bucket.blob(path)
            blob.delete()
            logger.info(f"File deleted from GCS: {path}")
            return True
        except NotFound:
            logger.warning(f"File not found for deletion: {path}")
            return False
        except Exception as e:
            logger.error(f"Failed to delete file: {str(e)}")
            return False

    def list_files(self, prefix: str = "", delimiter: Optional[str] = None) -> List[str]:
        """List files in GCS with optional prefix"""
        if not self.bucket:
            return self._list_local_files(prefix)

        try:
            blobs = self.bucket.list_blobs(prefix=prefix, delimiter=delimiter)
            return [blob.name for blob in blobs]
        except Exception as e:
            logger.error(f"Failed to list files: {str(e)}")
            return []

    def generate_signed_url(self, path: str, expiration_minutes: int = 60) -> str:
        """Generate a signed URL for temporary access to a file"""
        if not self.bucket:
            # For local development, return a local URL
            return f"/static/uploads/{path}"

        try:
            blob = self.bucket.blob(path)
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(minutes=expiration_minutes),
                method="GET"
            )
            return url
        except Exception as e:
            logger.error(f"Failed to generate signed URL: {str(e)}")
            raise

    def get_signed_url(self, path: str, expiration_minutes: int = 60) -> str:
        """Alias for generate_signed_url for compatibility with local storage service"""
        # Handle full GCS URIs by extracting just the blob path
        if path.startswith('gs://'):
            # Extract bucket and path from gs://bucket-name/path/to/file
            parts = path[5:].split('/', 1)  # Remove 'gs://' and split
            if len(parts) == 2:
                bucket_name, blob_path = parts
                # If this is a different bucket, log a warning but continue
                if bucket_name != self.bucket_name:
                    logger.warning(f"Blob path refers to different bucket: {bucket_name}, using configured bucket: {self.bucket_name}")
                path = blob_path
            else:
                logger.error(f"Invalid GCS URI format: {path}")
                raise ValueError(f"Invalid GCS URI format: {path}")

        return self.generate_signed_url(path, expiration_minutes)

    def generate_signed_upload_url(self, path: str, expiration_minutes: int = 60, content_type: Optional[str] = None) -> str:
        """Generate a signed URL for uploading a file directly to Cloud Storage"""
        if not self.bucket:
            # For local development, return a mock upload URL
            return f"/api/upload-local/{path}"

        try:
            # For Cloud Run, use our own upload endpoint instead of signed URLs
            # since the default service account doesn't have private key for signing
            logger.info("Using direct upload endpoint instead of signed URLs")
            return f"/api/upload-direct/{path}"

        except Exception as e:
            logger.error(f"Failed to generate signed upload URL: {str(e)}")
            # Fallback to direct upload endpoint
            logger.info("Falling back to direct upload endpoint")
            return f"/api/upload-direct/{path}"

    def move_file(self, source_path: str, destination_path: str) -> bool:
        """Move/rename file in GCS"""
        if not self.bucket:
            return self._move_local_file(source_path, destination_path)

        try:
            source_blob = self.bucket.blob(source_path)
            destination_blob = self.bucket.blob(destination_path)

            # Copy to new location
            destination_blob.upload_from_string(
                source_blob.download_as_bytes()
            )

            # Delete original
            source_blob.delete()

            logger.info(f"File moved from {source_path} to {destination_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to move file: {str(e)}")
            return False

    # Local storage fallback methods (for development)
    def _get_local_path(self, path: str) -> str:
        """Get local storage path"""
        base_dir = os.getenv('LOCAL_STORAGE_PATH', './uploads')
        return os.path.join(base_dir, path)

    def _save_local_file(self, file_content: BinaryIO, path: str) -> str:
        """Save file locally for development"""
        local_path = self._get_local_path(path)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        if isinstance(file_content, bytes):
            with open(local_path, 'wb') as f:
                f.write(file_content)
        else:
            with open(local_path, 'wb') as f:
                f.write(file_content.read())

        logger.info(f"File saved locally: {local_path}")
        return local_path

    def _copy_local_file(self, source: str, dest: str) -> str:
        """Copy local file for development"""
        import shutil
        dest_path = self._get_local_path(dest)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        shutil.copy2(source, dest_path)
        return dest_path

    def _read_local_file(self, path: str) -> bytes:
        """Read local file for development"""
        local_path = self._get_local_path(path)
        with open(local_path, 'rb') as f:
            return f.read()

    def _copy_from_local(self, source: str, dest: str):
        """Copy from local storage to filesystem"""
        import shutil
        source_path = self._get_local_path(source)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(source_path, dest)

    def _local_file_exists(self, path: str) -> bool:
        """Check if local file exists"""
        return os.path.exists(self._get_local_path(path))

    def _delete_local_file(self, path: str) -> bool:
        """Delete local file"""
        try:
            os.remove(self._get_local_path(path))
            return True
        except:
            return False

    def _list_local_files(self, prefix: str) -> List[str]:
        """List local files with prefix"""
        base_dir = self._get_local_path(prefix)
        if not os.path.exists(base_dir):
            return []

        files = []
        for root, _, filenames in os.walk(base_dir):
            for filename in filenames:
                full_path = os.path.join(root, filename)
                relative_path = os.path.relpath(full_path, self._get_local_path(""))
                files.append(relative_path)
        return files

    def _move_local_file(self, source: str, dest: str) -> bool:
        """Move local file"""
        import shutil
        try:
            source_path = self._get_local_path(source)
            dest_path = self._get_local_path(dest)
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.move(source_path, dest_path)
            return True
        except:
            return False


# Global storage service instance
storage_service = CloudStorageService()
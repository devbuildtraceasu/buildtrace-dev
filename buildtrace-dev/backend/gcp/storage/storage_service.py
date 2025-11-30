"""
Unified Storage Service for BuildTrace
Handles both GCS and local storage with a consistent interface
"""

import os
import io
import logging
import tempfile
from typing import Optional, BinaryIO, List
from datetime import datetime, timedelta
# Optional import - only needed if USE_GCS is True
try:
    from google.cloud import storage
    from google.cloud.exceptions import NotFound
    GCS_AVAILABLE = True
except ImportError:
    GCS_AVAILABLE = False
    storage = None

    class NotFound(Exception):
        """Fallback exception when google-cloud-storage is unavailable."""
        pass
import mimetypes
from config import config

logger = logging.getLogger(__name__)

class StorageService:
    """Unified storage service for handling file operations"""

    def __init__(self, bucket_name: Optional[str] = None):
        self.bucket_name = bucket_name or config.GCS_BUCKET_NAME
        self.client = None
        self.bucket = None
        self.use_gcs = config.USE_GCS
        self.initialize()

    def initialize(self):
        """Initialize GCS client and bucket if using GCS"""
        if not self.use_gcs:
            logger.info("Using local storage (GCS disabled)")
            return

        try:
            if not GCS_AVAILABLE:
                raise ImportError("google-cloud-storage is not installed")
            logger.info("Initializing GCS client...")
            self.client = storage.Client()
            self.bucket = self.client.bucket(self.bucket_name)

            # Test access
            try:
                bucket_exists = self.bucket.exists()
                logger.info(f"Bucket {self.bucket_name} exists: {bucket_exists}")
                if not bucket_exists:
                    logger.warning(f"Bucket {self.bucket_name} does not exist")
            except Exception as bucket_error:
                logger.error(f"Failed to access bucket {self.bucket_name}: {bucket_error}")
                raise

            logger.info(f"Cloud Storage initialized successfully with bucket: {self.bucket_name}")

        except Exception as e:
            logger.error(f"Failed to initialize Cloud Storage: {str(e)}")
            if config.IS_PRODUCTION:
                raise
            else:
                logger.warning("Falling back to local storage for development")
                self.use_gcs = False
                self.client = None
                self.bucket = None

    def upload_file(self, file_content: BinaryIO, destination_path: str,
                   content_type: Optional[str] = None,
                   session_id: Optional[str] = None,
                   job_id: Optional[str] = None,
                   save_to_outputs: bool = True) -> str:
        """
        Upload file to storage
        
        Args:
            file_content: File content (bytes or file-like object)
            destination_path: Destination path in storage
            content_type: Optional content type
            session_id: Optional session ID (for saving to outputs in dev mode)
            job_id: Optional job ID (for saving to outputs in dev mode)
            save_to_outputs: Whether to also save to local outputs in dev mode (default: True)
        """
        # Save to primary storage (GCS or local)
        if self.use_gcs and self.bucket:
            result = self._upload_to_gcs(file_content, destination_path, content_type)
        else:
            result = self._save_local_file(file_content, destination_path)
        
        # Also save to local outputs in dev mode for analysis
        if config.IS_DEVELOPMENT and save_to_outputs:
            try:
                from utils.local_output_manager import get_output_manager
                output_manager = get_output_manager()
                
                # Read file content if needed
                if isinstance(file_content, bytes):
                    content_bytes = file_content
                else:
                    file_content.seek(0)
                    content_bytes = file_content.read()
                    file_content.seek(0)  # Reset for primary storage
                
                # Determine file type and save appropriately
                if destination_path.endswith('.png') or destination_path.endswith('.jpg') or destination_path.endswith('.jpeg'):
                    if 'overlay' in destination_path.lower():
                        output_manager.save_overlay(
                            destination_path,
                            content_bytes,
                            session_id=session_id,
                            job_id=job_id
                        )
                    else:
                        output_manager.save_png(
                            destination_path,
                            content_bytes,
                            session_id=session_id,
                            job_id=job_id
                        )
                elif destination_path.endswith('.json'):
                    import json
                    try:
                        json_data = json.loads(content_bytes.decode('utf-8'))
                        if 'ocr' in destination_path.lower() or 'ocr_result' in destination_path.lower():
                            output_manager.save_ocr_result(
                                json_data,
                                session_id=session_id,
                                job_id=job_id
                            )
                        elif 'diff' in destination_path.lower():
                            output_manager.save_diff_result(
                                json_data,
                                session_id=session_id,
                                job_id=job_id
                            )
                        elif 'summary' in destination_path.lower():
                            output_manager.save_summary(
                                json_data,
                                session_id=session_id,
                                job_id=job_id
                            )
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        # Not JSON, skip output manager
                        pass
            except Exception as e:
                # Don't fail the upload if output saving fails
                logger.warning(f"Failed to save to local outputs: {e}")
        
        return result

    def upload_from_filename(self, local_path: str, destination_path: str) -> str:
        """Upload file from local filesystem to storage"""
        if self.use_gcs and self.bucket:
            return self._upload_from_filename_to_gcs(local_path, destination_path)
        else:
            return self._copy_local_file(local_path, destination_path)

    def download_file(self, source_path: str) -> bytes:
        """Download file from storage as bytes"""
        if self.use_gcs and self.bucket:
            return self._download_from_gcs(source_path)
        else:
            return self._read_local_file(source_path)

    def download_to_filename(self, source_path: str, local_path: str) -> bool:
        """Download file from storage to local filesystem"""
        if self.use_gcs and self.bucket:
            return self._download_from_gcs_to_file(source_path, local_path)
        else:
            return self._copy_from_local(source_path, local_path)

    def download_to_temp(self, source_path: str) -> str:
        """Download file to temporary location and return path"""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(source_path)[1])
        temp_path = temp_file.name
        temp_file.close()
        
        if self.download_to_filename(source_path, temp_path):
            return temp_path
        else:
            raise Exception(f"Failed to download {source_path} to temp file")

    def file_exists(self, path: str) -> bool:
        """Check if file exists in storage"""
        if self.use_gcs and self.bucket:
            return self._gcs_file_exists(path)
        else:
            return self._local_file_exists(path)

    def delete_file(self, path: str) -> bool:
        """Delete file from storage"""
        if self.use_gcs and self.bucket:
            return self._delete_from_gcs(path)
        else:
            return self._delete_local_file(path)

    def generate_signed_url(self, path: str, expiration_minutes: int = 60) -> str:
        """Generate a signed URL for temporary access to a file"""
        if self.use_gcs and self.bucket:
            return self._generate_gcs_signed_url(path, expiration_minutes)
        else:
            # For local development, return a local URL
            return f"/static/uploads/{path}"

    # GCS-specific methods
    def _upload_to_gcs(self, file_content: BinaryIO, destination_path: str, content_type: Optional[str] = None) -> str:
        """Upload file to GCS"""
        try:
            # Determine content type
            if not content_type:
                content_type, _ = mimetypes.guess_type(destination_path)
                if not content_type:
                    content_type = 'application/octet-stream'  # Default fallback
            
            blob = self.bucket.blob(destination_path)
            # Set content type on blob BEFORE upload
            blob.content_type = content_type
            
            # Convert bytes to BytesIO if needed, then upload
            # upload_from_file respects the blob's content_type setting
            if isinstance(file_content, bytes):
                file_io = io.BytesIO(file_content)
                blob.upload_from_file(file_io, rewind=True)
            else:
                blob.upload_from_file(file_content, rewind=True)

            # Verify the object was created
            blob.reload()
            logger.info(
                f"File uploaded to GCS successfully",
                extra={
                    'bucket': self.bucket_name,
                    'object_path': destination_path,
                    'content_type': blob.content_type,
                    'size': blob.size,
                    'gs_uri': f"gs://{self.bucket_name}/{destination_path}"
                }
            )
            return f"gs://{self.bucket_name}/{destination_path}"

        except Exception as e:
            logger.error(f"Failed to upload file to GCS: {str(e)}")
            raise

    def _upload_from_filename_to_gcs(self, local_path: str, destination_path: str) -> str:
        """Upload file from local filesystem to GCS"""
        try:
            blob = self.bucket.blob(destination_path)
            blob.upload_from_filename(local_path)
            logger.info(f"File uploaded from {local_path} to GCS: {destination_path}")
            return f"gs://{self.bucket_name}/{destination_path}"
        except Exception as e:
            logger.error(f"Failed to upload file from {local_path}: {str(e)}")
            raise

    def _download_from_gcs(self, source_path: str) -> bytes:
        """Download file from GCS as bytes"""
        try:
            blob = self.bucket.blob(self._normalize_gcs_path(source_path))
            content = blob.download_as_bytes()
            logger.info(f"File downloaded from GCS: {source_path}")
            return content
        except NotFound:
            logger.error(f"File not found in GCS: {source_path}")
            raise
        except Exception as e:
            logger.error(f"Failed to download file from GCS: {str(e)}")
            raise

    def _download_from_gcs_to_file(self, source_path: str, local_path: str) -> bool:
        """Download file from GCS to local filesystem"""
        try:
            blob = self.bucket.blob(self._normalize_gcs_path(source_path))
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            blob.download_to_filename(local_path)
            logger.info(f"File downloaded from GCS to {local_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to download file to {local_path}: {str(e)}")
            return False

    def _gcs_file_exists(self, path: str) -> bool:
        """Check if file exists in GCS"""
        try:
            blob = self.bucket.blob(self._normalize_gcs_path(path))
            return blob.exists()
        except Exception as e:
            logger.error(f"Error checking file existence: {str(e)}")
            return False

    def _delete_from_gcs(self, path: str) -> bool:
        """Delete file from GCS"""
        try:
            blob = self.bucket.blob(self._normalize_gcs_path(path))
            blob.delete()
            logger.info(f"File deleted from GCS: {path}")
            return True
        except NotFound:
            logger.warning(f"File not found for deletion: {path}")
            return False
        except Exception as e:
            logger.error(f"Failed to delete file: {str(e)}")
            return False

    def _generate_gcs_signed_url(self, path: str, expiration_minutes: int = 60) -> str:
        """Generate a signed URL for temporary access to a file in GCS"""
        try:
            blob = self.bucket.blob(self._normalize_gcs_path(path))
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(minutes=expiration_minutes),
                method="GET"
            )
            return url
        except Exception as e:
            logger.error(f"Failed to generate signed URL: {str(e)}")
            raise

    def _normalize_gcs_path(self, path: str) -> str:
        """Normalize object path by stripping gs://bucket prefixes if present."""
        if path.startswith("gs://"):
            _, remainder = path.split("gs://", 1)
            bucket, *rest = remainder.split("/", 1)
            if bucket != self.bucket_name:
                logger.warning(
                    f"Object bucket {bucket} does not match configured bucket {self.bucket_name}"
                )
            path = rest[0] if rest else ""
        return path.lstrip("/")

    # Local storage methods
    def _get_local_path(self, path: str) -> str:
        """Get local storage path, supporting both relative keys and absolute paths"""
        if os.path.isabs(path):
            return path
        base_dir = config.LOCAL_UPLOAD_PATH if hasattr(config, 'LOCAL_UPLOAD_PATH') else './uploads'
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
        return path if not os.path.isabs(path) else local_path

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
        except (FileNotFoundError, OSError, PermissionError) as e:
            logger.warning(f"Failed to delete local file {path}: {e}")
            return False

    # Helper methods for specific use cases
    def upload_ocr_result(self, drawing_version_id: str, ocr_data: dict) -> str:
        """Upload OCR result JSON to storage"""
        import json
        json_content = json.dumps(ocr_data).encode('utf-8')
        path = f"ocr/{drawing_version_id}.json"
        return self.upload_file(json_content, path, content_type='application/json')

    def upload_diff_result(self, diff_result_id: str, diff_data: dict) -> str:
        """Upload diff result JSON to storage"""
        import json
        import numpy as np
        
        def convert_numpy(obj):
            """Convert numpy types to Python native types for JSON serialization"""
            if isinstance(obj, np.bool_):
                return bool(obj)
            if isinstance(obj, np.integer):
                return int(obj)
            if isinstance(obj, np.floating):
                return float(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            return obj
        
        # Recursively convert numpy types
        def deep_convert(data):
            if isinstance(data, dict):
                return {k: deep_convert(v) for k, v in data.items()}
            elif isinstance(data, list):
                return [deep_convert(item) for item in data]
            else:
                return convert_numpy(data)
        
        converted_data = deep_convert(diff_data)
        json_content = json.dumps(converted_data).encode('utf-8')
        path = f"diffs/{diff_result_id}.json"
        return self.upload_file(json_content, path, content_type='application/json')

    def upload_overlay(self, overlay_id: str, overlay_data: dict) -> str:
        """Upload overlay JSON to storage"""
        import json
        json_content = json.dumps(overlay_data).encode('utf-8')
        path = f"overlays/{overlay_id}.json"
        return self.upload_file(json_content, path, content_type='application/json')
    
    def upload_diff_overlay(self, path: str, overlay_bytes: bytes) -> str:
        """Upload diff overlay image (PNG) to storage"""
        return self.upload_file(overlay_bytes, path, content_type='image/png')


# Global storage service instance
storage_service = StorageService()

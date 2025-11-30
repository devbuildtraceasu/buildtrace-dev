"""
Local file storage implementation
Provides file storage operations using local filesystem
"""

import os
import shutil
import logging
from pathlib import Path
from typing import Optional, List, BinaryIO
from services.interfaces import StorageInterface

logger = logging.getLogger(__name__)


class LocalStorageService(StorageInterface):
    """Local filesystem-based storage service"""

    def __init__(self, upload_path: str = 'uploads',
                 results_path: str = 'results',
                 temp_path: str = 'temp'):
        self.upload_path = Path(upload_path)
        self.results_path = Path(results_path)
        self.temp_path = Path(temp_path)

        # Create directories if they don't exist
        self.upload_path.mkdir(exist_ok=True)
        self.results_path.mkdir(exist_ok=True)
        self.temp_path.mkdir(exist_ok=True)

        logger.info(f"Local storage initialized: upload={self.upload_path}, "
                   f"results={self.results_path}, temp={self.temp_path}")

    def upload_file(self, file_content: BinaryIO, destination_path: str,
                   content_type: Optional[str] = None) -> str:
        """Upload file to local storage"""
        try:
            # Ensure destination directory exists
            full_path = self._get_full_path(destination_path)
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file content
            with open(full_path, 'wb') as f:
                if hasattr(file_content, 'read'):
                    # It's a file-like object
                    shutil.copyfileobj(file_content, f)
                else:
                    # It's bytes
                    f.write(file_content)

            logger.info(f"File uploaded to local storage: {full_path}")
            return str(full_path)

        except Exception as e:
            logger.error(f"Error uploading file to local storage: {e}")
            raise

    def download_file(self, storage_path: str) -> Optional[bytes]:
        """Download file from local storage"""
        try:
            full_path = self._get_full_path(storage_path)
            if not full_path.exists():
                logger.warning(f"File not found: {full_path}")
                return None

            with open(full_path, 'rb') as f:
                return f.read()

        except Exception as e:
            logger.error(f"Error downloading file from local storage: {e}")
            return None

    def download_to_filename(self, storage_path: str, local_path: str) -> bool:
        """Download file from storage to local path"""
        try:
            full_path = self._get_full_path(storage_path)
            if not full_path.exists():
                logger.warning(f"Source file not found: {full_path}")
                return False

            # Ensure destination directory exists
            local_path = Path(local_path)
            local_path.parent.mkdir(parents=True, exist_ok=True)

            # Copy file
            shutil.copy2(full_path, local_path)
            logger.info(f"File copied from {full_path} to {local_path}")
            return True

        except Exception as e:
            logger.error(f"Error copying file: {e}")
            return False

    def delete_file(self, storage_path: str) -> bool:
        """Delete file from local storage"""
        try:
            full_path = self._get_full_path(storage_path)
            if full_path.exists():
                if full_path.is_file():
                    full_path.unlink()
                    logger.info(f"File deleted: {full_path}")
                elif full_path.is_dir():
                    shutil.rmtree(full_path)
                    logger.info(f"Directory deleted: {full_path}")
                return True
            else:
                logger.warning(f"File not found for deletion: {full_path}")
                return False

        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return False

    def file_exists(self, storage_path: str) -> bool:
        """Check if file exists in local storage"""
        full_path = self._get_full_path(storage_path)
        return full_path.exists()

    def get_signed_url(self, storage_path: str, expiration_minutes: int = 60) -> Optional[str]:
        """
        For local storage, return the relative path (no signing needed)
        In a web server context, this would be served via /files/ endpoint
        """
        full_path = self._get_full_path(storage_path)
        if full_path.exists():
            # Return relative path that can be served by web server
            return f"/files/{storage_path}"
        return None

    def list_files(self, prefix: str = "") -> List[str]:
        """List files with given prefix"""
        files = []

        # Search in all storage directories
        for storage_dir in [self.upload_path, self.results_path, self.temp_path]:
            try:
                if prefix:
                    # Use glob to find files matching prefix
                    pattern = f"{prefix}*"
                    for file_path in storage_dir.rglob(pattern):
                        if file_path.is_file():
                            # Return relative path from storage root
                            relative_path = file_path.relative_to(storage_dir)
                            files.append(str(relative_path))
                else:
                    # List all files
                    for file_path in storage_dir.rglob("*"):
                        if file_path.is_file():
                            relative_path = file_path.relative_to(storage_dir)
                            files.append(str(relative_path))

            except Exception as e:
                logger.error(f"Error listing files in {storage_dir}: {e}")

        return sorted(files)

    def get_file_url(self, storage_path: str) -> str:
        """Get URL for serving file (for local web serving)"""
        return f"/files/{storage_path}"

    def ensure_directory(self, directory_path: str) -> bool:
        """Ensure directory exists in local storage"""
        try:
            full_path = self._get_full_path(directory_path)
            full_path.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"Error creating directory {directory_path}: {e}")
            return False

    def get_file_size(self, storage_path: str) -> Optional[int]:
        """Get file size in bytes"""
        try:
            full_path = self._get_full_path(storage_path)
            if full_path.exists() and full_path.is_file():
                return full_path.stat().st_size
            return None
        except Exception as e:
            logger.error(f"Error getting file size for {storage_path}: {e}")
            return None

    def move_file(self, source_path: str, destination_path: str) -> bool:
        """Move file from one location to another"""
        try:
            source = self._get_full_path(source_path)
            destination = self._get_full_path(destination_path)

            if not source.exists():
                logger.warning(f"Source file not found: {source}")
                return False

            # Ensure destination directory exists
            destination.parent.mkdir(parents=True, exist_ok=True)

            # Move file
            shutil.move(str(source), str(destination))
            logger.info(f"File moved from {source} to {destination}")
            return True

        except Exception as e:
            logger.error(f"Error moving file from {source_path} to {destination_path}: {e}")
            return False

    def copy_file(self, source_path: str, destination_path: str) -> bool:
        """Copy file from one location to another"""
        try:
            source = self._get_full_path(source_path)
            destination = self._get_full_path(destination_path)

            if not source.exists():
                logger.warning(f"Source file not found: {source}")
                return False

            # Ensure destination directory exists
            destination.parent.mkdir(parents=True, exist_ok=True)

            # Copy file
            shutil.copy2(source, destination)
            logger.info(f"File copied from {source} to {destination}")
            return True

        except Exception as e:
            logger.error(f"Error copying file from {source_path} to {destination_path}: {e}")
            return False

    def cleanup_temp_files(self, older_than_hours: int = 24) -> int:
        """Clean up temporary files older than specified hours"""
        import time

        cleaned_count = 0
        cutoff_time = time.time() - (older_than_hours * 3600)

        try:
            for file_path in self.temp_path.rglob("*"):
                if file_path.is_file():
                    if file_path.stat().st_mtime < cutoff_time:
                        file_path.unlink()
                        cleaned_count += 1

            logger.info(f"Cleaned up {cleaned_count} temporary files")
            return cleaned_count

        except Exception as e:
            logger.error(f"Error during temp file cleanup: {e}")
            return cleaned_count

    def _get_full_path(self, storage_path: str) -> Path:
        """Convert storage path to full filesystem path"""
        storage_path = storage_path.lstrip('/')  # Remove leading slash if present

        # Determine which storage directory to use based on path
        if storage_path.startswith('uploads/') or '/uploads/' in storage_path:
            return self.upload_path / storage_path.replace('uploads/', '', 1)
        elif storage_path.startswith('results/') or '/results/' in storage_path:
            return self.results_path / storage_path.replace('results/', '', 1)
        elif storage_path.startswith('temp/') or '/temp/' in storage_path:
            return self.temp_path / storage_path.replace('temp/', '', 1)
        else:
            # Default to upload path if no prefix specified
            return self.upload_path / storage_path

    def get_storage_info(self) -> dict:
        """Get storage information and stats"""
        try:
            info = {
                'type': 'local',
                'upload_path': str(self.upload_path.absolute()),
                'results_path': str(self.results_path.absolute()),
                'temp_path': str(self.temp_path.absolute()),
                'total_files': 0,
                'total_size_mb': 0.0
            }

            # Calculate stats
            total_size = 0
            total_files = 0

            for storage_dir in [self.upload_path, self.results_path, self.temp_path]:
                for file_path in storage_dir.rglob("*"):
                    if file_path.is_file():
                        total_files += 1
                        total_size += file_path.stat().st_size

            info['total_files'] = total_files
            info['total_size_mb'] = round(total_size / (1024 * 1024), 2)

            return info

        except Exception as e:
            logger.error(f"Error getting storage info: {e}")
            return {'type': 'local', 'error': str(e)}
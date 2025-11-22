"""
Storage module for BuildTrace
Handles both GCS and local storage
"""

from .storage_service import StorageService, storage_service

__all__ = ['StorageService', 'storage_service']


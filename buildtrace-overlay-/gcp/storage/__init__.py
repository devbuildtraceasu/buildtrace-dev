"""
Storage module for BuildTrace GCP integration

Contains:
- storage_service.py: Google Cloud Storage service with local fallback
"""

from .storage_service import CloudStorageService, storage_service

__all__ = ['CloudStorageService', 'storage_service']
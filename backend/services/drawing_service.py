"""Drawing upload service encapsulates validation and persistence logic."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Optional

from sqlalchemy import func
from werkzeug.utils import secure_filename

from config import config
from gcp.database import get_db_session
from gcp.database.models import Drawing, DrawingVersion, Project, Session, User
from gcp.storage.storage_service import storage_service, StorageService

class DrawingUploadError(Exception):
    """Raised when a drawing upload cannot be processed."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


@dataclass
class DrawingUploadResult:
    """Represents the persisted drawing version metadata."""

    drawing_version_id: str
    drawing_name: str
    version_number: int
    project_id: str
    storage_path: str
    file_size: int


class DrawingUploadService:
    """Service responsible for validating and persisting drawing uploads."""

    def __init__(
        self,
        storage_service_instance: Optional[StorageService] = None,
        session_factory: Optional[Callable] = None,
        logger_: Optional[logging.Logger] = None,
    ) -> None:
        # Use global singleton storage_service by default to avoid multiple initializations
        self.storage = storage_service_instance or storage_service
        self.session_factory = session_factory or get_db_session
        self.logger = logger_ or logging.getLogger(self.__class__.__name__)

    def handle_upload(
        self,
        *,
        file_bytes: bytes,
        filename: str,
        content_type: Optional[str],
        project_id: str,
        user_id: Optional[str],
        is_revision: bool,
    ) -> DrawingUploadResult:
        """Validate an upload request, persist metadata, and store the file."""
        if not file_bytes:
            raise DrawingUploadError('file required', status_code=400)
        if not filename:
            raise DrawingUploadError('filename required', status_code=400)
        if not project_id:
            raise DrawingUploadError('project_id required', status_code=400)
        if not self._allowed_file(filename):
            allowed = ', '.join(sorted(config.ALLOWED_EXTENSIONS))
            raise DrawingUploadError(f'Invalid file type. Allowed: {allowed}', status_code=400)

        clean_name = secure_filename(filename) or f'drawing-{uuid.uuid4()}'
        drawing_name = self._extract_drawing_name(clean_name)
        storage_key = f"drawings/{project_id}/{uuid.uuid4()}/{clean_name}"
        self.logger.debug(
            "Uploading drawing to storage", extra={
                'project_id': project_id,
                'storage_key': storage_key,
                'drawing_name': drawing_name,
            }
        )
        storage_path = self.storage.upload_file(file_bytes, storage_key, content_type=content_type)

        with self.session_factory() as db:
            project = db.query(Project).filter_by(id=project_id).first()
            if not project:
                raise DrawingUploadError('Project not found', status_code=404)

            session = self._create_session(db, project, user_id)
            drawing = self._create_drawing(
                db,
                session_id=session.id,
                drawing_name=drawing_name,
                clean_name=clean_name,
                original_filename=filename,
                storage_path=storage_path,
                is_revision=is_revision,
            )
            version_number = self._get_next_version_number(db, project_id, drawing_name)

            drawing_version = DrawingVersion(
                id=str(uuid.uuid4()),
                project_id=project_id,
                drawing_name=drawing_name,
                version_number=version_number,
                drawing_id=drawing.id,
                upload_date=datetime.utcnow(),
                ocr_status='pending',
                file_size=len(file_bytes),
            )
            db.add(drawing_version)
            db.flush()
            self.logger.info(
                "Persisted drawing version",
                extra={
                    'project_id': project_id,
                    'drawing_version_id': drawing_version.id,
                    'version_number': version_number,
                }
            )

            return DrawingUploadResult(
                drawing_version_id=drawing_version.id,
                drawing_name=drawing_name,
                version_number=version_number,
                project_id=project_id,
                storage_path=storage_path,
                file_size=len(file_bytes),
            )

    def _create_session(self, db, project: Project, user_id: Optional[str]) -> Session:
        final_user_id = self._ensure_user_exists(db, user_id, project)

        session = Session(
            id=str(uuid.uuid4()),
            user_id=final_user_id,
            project_id=project.id,
            session_type='comparison',
            status='active',
            session_metadata={'source': 'async_api'},
        )
        db.add(session)
        db.flush()
        self.logger.debug(
            "Created session for upload",
            extra={'project_id': project.id, 'session_id': session.id, 'user_id': final_user_id},
        )
        return session

    def _ensure_user_exists(self, db, user_id: Optional[str], project: Project) -> str:
        """Ensure uploads reference a valid user row."""
        if user_id:
            existing = db.query(User).filter_by(id=user_id).first()
            if existing:
                return existing.id
            return self._create_placeholder_user(db, user_id, project.id)

        if getattr(project, 'user_id', None):
            owner = db.query(User).filter_by(id=project.user_id).first()
            if owner:
                return owner.id

        return self._create_placeholder_user(db, 'system', project.id)

    def _create_placeholder_user(self, db, candidate_id: str, project_id: str) -> str:
        placeholder_email = f"{candidate_id}@system.local"
        user = User(
            id=candidate_id,
            email=placeholder_email,
            name='System User',
            is_active=True,
        )
        db.add(user)
        db.flush()
        self.logger.warning(
            "Auto-created fallback user",
            extra={'user_id': candidate_id, 'project_id': project_id},
        )
        return candidate_id

    def _create_drawing(
        self,
        db,
        *,
        session_id: str,
        drawing_name: str,
        clean_name: str,
        original_filename: str,
        storage_path: str,
        is_revision: bool,
    ) -> Drawing:
        drawing = Drawing(
            id=str(uuid.uuid4()),
            session_id=session_id,
            drawing_type='new' if is_revision else 'old',
            filename=clean_name,
            original_filename=original_filename,
            storage_path=storage_path,
            drawing_name=drawing_name,
            page_number=1,
            processed_at=datetime.utcnow(),
        )
        db.add(drawing)
        db.flush()
        self.logger.debug(
            "Created drawing record",
            extra={'drawing_id': drawing.id, 'session_id': session_id},
        )
        return drawing

    def _get_next_version_number(self, db, project_id: str, drawing_name: str) -> int:
        max_version = (
            db.query(func.max(DrawingVersion.version_number))
            .filter_by(project_id=project_id, drawing_name=drawing_name)
            .scalar()
        )
        next_version = (max_version or 0) + 1
        self.logger.debug(
            "Computed next version number",
            extra={'project_id': project_id, 'drawing_name': drawing_name, 'version': next_version},
        )
        return next_version

    @staticmethod
    def _extract_drawing_name(filename: str) -> str:
        return filename.rsplit('.', 1)[0]

    @staticmethod
    def _allowed_file(filename: str) -> bool:
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS


__all__ = ['DrawingUploadService', 'DrawingUploadError', 'DrawingUploadResult']

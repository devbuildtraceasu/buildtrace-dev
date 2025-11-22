"""OCR pipeline for BuildTrace.

This module intentionally keeps the OCR implementation lightweight so it can run in
local environments without GPU/large dependencies while still exercising the data
path and logging required by the architecture plan.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from typing import Dict, Optional

from gcp.database import get_db_session
from gcp.database.models import DrawingVersion
from gcp.storage import StorageService

logger = logging.getLogger(__name__)


class OCRPipeline:
    """Extracts lightweight text + metadata fingerprints for a drawing version."""

    def __init__(
        self,
        storage_service: Optional[StorageService] = None,
        session_factory=None,
    ) -> None:
        self.storage = storage_service or StorageService()
        self.session_factory = session_factory or get_db_session

    def run(self, drawing_version_id: str) -> Dict:
        """Process a drawing version and persist an OCR artifact."""
        logger.info("Starting OCR pipeline", extra={"drawing_version_id": drawing_version_id})

        with self.session_factory() as db:
            drawing_version = db.query(DrawingVersion).filter_by(id=drawing_version_id).first()
            if not drawing_version:
                raise ValueError(f"DrawingVersion {drawing_version_id} not found")

            drawing = drawing_version.drawing
            if not drawing or not drawing.storage_path:
                raise ValueError(f"Drawing storage missing for version {drawing_version_id}")

            file_bytes = self.storage.download_file(drawing.storage_path)
            fingerprint = hashlib.sha256(file_bytes).hexdigest()
            text_stub = f"Drawing {drawing_version.drawing_name} hash {fingerprint[:12]}"

            ocr_payload = {
                "drawing_version_id": drawing_version_id,
                "drawing_name": drawing_version.drawing_name,
                "hash": fingerprint,
                "byte_length": len(file_bytes),
                "generated_at": datetime.utcnow().isoformat(),
                "text_excerpt": text_stub,
            }

            result_ref = self.storage.upload_ocr_result(drawing_version_id, ocr_payload)
            drawing_version.ocr_status = "completed"
            drawing_version.ocr_result_ref = result_ref
            drawing_version.ocr_completed_at = datetime.utcnow()

            logger.info(
                "OCR pipeline completed",
                extra={
                    "drawing_version_id": drawing_version_id,
                    "result_ref": result_ref,
                    "byte_length": len(file_bytes),
                },
            )

            return {
                "drawing_version_id": drawing_version_id,
                "result_ref": result_ref,
                "hash": fingerprint,
            }


__all__ = ["OCRPipeline"]

"""Diff pipeline implementation for BuildTrace."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Optional

from gcp.database import get_db_session
from gcp.database.models import DiffResult, DrawingVersion, Job
from gcp.storage import StorageService

logger = logging.getLogger(__name__)


class DiffPipeline:
    """Generates machine overlays by comparing OCR fingerprints."""

    def __init__(
        self,
        storage_service: Optional[StorageService] = None,
        session_factory=None,
    ) -> None:
        self.storage = storage_service or StorageService()
        self.session_factory = session_factory or get_db_session

    def run(self, job_id: str, old_version_id: str, new_version_id: str) -> Dict:
        logger.info(
            "Starting diff pipeline",
            extra={"job_id": job_id, "old_version_id": old_version_id, "new_version_id": new_version_id},
        )

        with self.session_factory() as db:
            job = db.query(Job).filter_by(id=job_id).first()
            if not job:
                raise ValueError(f"Job {job_id} not found")

            old_version = db.query(DrawingVersion).filter_by(id=old_version_id).first()
            new_version = db.query(DrawingVersion).filter_by(id=new_version_id).first()
            if not old_version or not new_version:
                raise ValueError("Drawing versions missing for diff computation")
            if not old_version.ocr_result_ref or not new_version.ocr_result_ref:
                raise ValueError("OCR must complete before running diff")

            old_payload = json.loads(self.storage.download_file(old_version.ocr_result_ref).decode("utf-8"))
            new_payload = json.loads(self.storage.download_file(new_version.ocr_result_ref).decode("utf-8"))

            changes = []
            if old_payload.get("hash") != new_payload.get("hash"):
                changes.append(
                    {
                        "field": "hash",
                        "before": old_payload.get("hash"),
                        "after": new_payload.get("hash"),
                    }
                )

            if old_payload.get("byte_length") != new_payload.get("byte_length"):
                changes.append(
                    {
                        "field": "byte_length",
                        "before": old_payload.get("byte_length"),
                        "after": new_payload.get("byte_length"),
                    }
                )

            diff_payload = {
                "job_id": job_id,
                "old_version_id": old_version_id,
                "new_version_id": new_version_id,
                "changes": changes,
                "generated_at": datetime.utcnow().isoformat(),
            }

            diff_result_id = str(uuid.uuid4())
            diff_ref = self.storage.upload_diff_result(diff_result_id, diff_payload)
            diff_result = DiffResult(
                id=diff_result_id,
                job_id=job_id,
                old_drawing_version_id=old_version_id,
                new_drawing_version_id=new_version_id,
                machine_generated_overlay_ref=diff_ref,
                changes_detected=bool(changes),
                change_count=len(changes),
                alignment_score=1.0,
                created_at=datetime.utcnow(),
                created_by=job.created_by,
                metadata={"auto_generated": True},
            )
            db.add(diff_result)

            logger.info(
                "Diff pipeline completed",
                extra={
                    "job_id": job_id,
                    "diff_result_id": diff_result_id,
                    "change_count": len(changes),
                },
            )

            return {
                "diff_result_id": diff_result_id,
                "result_ref": diff_ref,
                "change_count": len(changes),
            }


__all__ = ["DiffPipeline"]

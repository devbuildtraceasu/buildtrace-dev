"""OCR worker consumes Pub/Sub style messages and runs the OCR pipeline."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, Optional

from gcp.database import get_db_session
from gcp.database.models import JobStage
from processing import OCRPipeline
from services.orchestrator import OrchestratorService

logger = logging.getLogger(__name__)


class OCRWorker:
    """Worker entrypoint for OCR tasks."""

    def __init__(
        self,
        pipeline: Optional[OCRPipeline] = None,
        orchestrator: Optional[OrchestratorService] = None,
        session_factory=None,
    ) -> None:
        self.pipeline = pipeline or OCRPipeline()
        self.orchestrator = orchestrator or OrchestratorService()
        self.session_factory = session_factory or get_db_session

    def process_message(self, message: Dict) -> Dict:
        """Process an OCR task message."""
        job_id = message.get("job_id")
        drawing_version_id = message.get("drawing_version_id")
        if not job_id or not drawing_version_id:
            raise ValueError("OCR worker requires job_id and drawing_version_id")

        logger.info(
            "Processing OCR message",
            extra={"job_id": job_id, "drawing_version_id": drawing_version_id, "metadata": message.get("metadata")},
        )

        try:
            result = self.pipeline.run(drawing_version_id)
            with self.session_factory() as db:
                stage = (
                    db.query(JobStage)
                    .filter_by(job_id=job_id, stage="ocr", drawing_version_id=drawing_version_id)
                    .first()
                )
                if stage:
                    stage.status = "completed"
                    stage.completed_at = datetime.utcnow()
                    stage.result_ref = result.get("result_ref")

            self.orchestrator.on_ocr_complete(job_id, drawing_version_id)
            return result

        except Exception as exc:
            logger.exception(
                "OCR worker failed",
                extra={"job_id": job_id, "drawing_version_id": drawing_version_id},
            )
            with self.session_factory() as db:
                stage = (
                    db.query(JobStage)
                    .filter_by(job_id=job_id, stage="ocr", drawing_version_id=drawing_version_id)
                    .first()
                )
                if stage:
                    stage.status = "failed"
                    stage.error_message = str(exc)
                    stage.completed_at = datetime.utcnow()
                    stage.retry_count = (stage.retry_count or 0) + 1
            raise


__all__ = ["OCRWorker"]

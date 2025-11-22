"""Diff worker that consumes orchestrator messages."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, Optional

from gcp.database import get_db_session
from gcp.database.models import JobStage
from processing import DiffPipeline
from services.orchestrator import OrchestratorService

logger = logging.getLogger(__name__)


class DiffWorker:
    """Worker entrypoint for diff tasks."""

    def __init__(
        self,
        pipeline: Optional[DiffPipeline] = None,
        orchestrator: Optional[OrchestratorService] = None,
        session_factory=None,
    ) -> None:
        self.pipeline = pipeline or DiffPipeline()
        self.orchestrator = orchestrator or OrchestratorService()
        self.session_factory = session_factory or get_db_session

    def process_message(self, message: Dict) -> Dict:
        job_id = message.get("job_id")
        old_version_id = message.get("old_drawing_version_id")
        new_version_id = message.get("new_drawing_version_id")
        if not all([job_id, old_version_id, new_version_id]):
            raise ValueError("Diff worker requires job_id, old_drawing_version_id, and new_drawing_version_id")

        logger.info(
            "Processing diff message",
            extra={"job_id": job_id, "old_version_id": old_version_id, "new_version_id": new_version_id},
        )

        try:
            result = self.pipeline.run(job_id, old_version_id, new_version_id)
            with self.session_factory() as db:
                stage = db.query(JobStage).filter_by(job_id=job_id, stage="diff").first()
                if stage:
                    stage.status = "completed"
                    stage.completed_at = datetime.utcnow()
                    stage.result_ref = result.get("result_ref")

            self.orchestrator.on_diff_complete(job_id, result["diff_result_id"])
            return result

        except Exception as exc:
            logger.exception("Diff worker failed", extra={"job_id": job_id})
            with self.session_factory() as db:
                stage = db.query(JobStage).filter_by(job_id=job_id, stage="diff").first()
                if stage:
                    stage.status = "failed"
                    stage.error_message = str(exc)
                    stage.completed_at = datetime.utcnow()
                    stage.retry_count = (stage.retry_count or 0) + 1
            raise


__all__ = ["DiffWorker"]

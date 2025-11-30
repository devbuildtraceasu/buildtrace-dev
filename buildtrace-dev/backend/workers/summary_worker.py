"""Summary worker implementation."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, Optional

from sqlalchemy.orm.attributes import flag_modified

from gcp.database import get_db_session
from gcp.database.models import JobStage
from processing import SummaryPipeline
from services.orchestrator import OrchestratorService

logger = logging.getLogger(__name__)


class SummaryWorker:
    """Worker entrypoint for summary generation tasks."""

    def __init__(
        self,
        pipeline: Optional[SummaryPipeline] = None,
        orchestrator: Optional[OrchestratorService] = None,
        session_factory=None,
    ) -> None:
        self.pipeline = pipeline or SummaryPipeline()
        self.orchestrator = orchestrator or OrchestratorService()
        self.session_factory = session_factory or get_db_session

    def process_message(self, message: Dict) -> Dict:
        job_id = message.get("job_id")
        diff_result_id = message.get("diff_result_id")
        overlay_ref = message.get("overlay_ref")
        metadata = message.get("metadata")
        if not job_id or not diff_result_id:
            raise ValueError("Summary worker requires job_id and diff_result_id")

        logger.info(
            "Processing summary message",
            extra={"job_id": job_id, "diff_result_id": diff_result_id, "overlay_ref": overlay_ref},
        )

        try:
            overlay_id = metadata.get('overlay_id') if metadata else None
            result = self.pipeline.run(
                job_id,
                diff_result_id,
                overlay_ref=overlay_ref,
                metadata=metadata,
                overlay_id=overlay_id,
            )
            should_mark_complete = False
            with self.session_factory() as db:
                stage = db.query(JobStage).filter_by(job_id=job_id, stage="summary").first()
                if stage:
                    stage_meta = stage.stage_metadata or {}
                    expected = stage_meta.get('expected_summaries', 1)
                    completed = stage_meta.get('completed_summaries', 0) + 1
                    stage_meta['completed_summaries'] = completed
                    stage.stage_metadata = stage_meta
                    # Explicitly mark JSON column as modified for SQLAlchemy to detect
                    flag_modified(stage, 'stage_metadata')
                    
                    logger.info(
                        "Updated summary stage progress",
                        extra={"job_id": job_id, "completed": completed, "expected": expected}
                    )

                    if completed >= expected:
                        stage.status = "completed"
                        stage.completed_at = datetime.utcnow()
                        stage.result_ref = result.get("summary_id")
                        should_mark_complete = True
                        logger.info(f"All summaries complete for job {job_id}")
                db.commit()

            if should_mark_complete:
                self.orchestrator.on_summary_complete(job_id)
            return result

        except Exception as exc:
            logger.exception("Summary worker failed", extra={"job_id": job_id})
            with self.session_factory() as db:
                stage = db.query(JobStage).filter_by(job_id=job_id, stage="summary").first()
                if stage:
                    stage.status = "failed"
                    stage.error_message = str(exc)
                    stage.completed_at = datetime.utcnow()
                    stage.retry_count = (stage.retry_count or 0) + 1
            raise


__all__ = ["SummaryWorker"]

"""Diff worker that consumes orchestrator messages."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, Optional, List
import json

from gcp.database import get_db_session
from gcp.database.models import JobStage, DiffResult
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
    
    # =========================================================================
    # STREAMING MODE: Process single page
    # =========================================================================
    
    def process_streaming_message(self, message: Dict) -> Dict:
        """
        Process diff for a single page (streaming mode).
        
        Message format:
        {
            'job_id': str,
            'page_number': int,
            'old_version_id': str,
            'new_version_id': str,
            'old_page_gcs': str,
            'new_page_gcs': str,
            'drawing_name': str,
            'metadata': {...}
        }
        """
        job_id = message.get("job_id")
        page_number = message.get("page_number")
        old_page_gcs = message.get("old_page_gcs")
        new_page_gcs = message.get("new_page_gcs")
        old_version_id = message.get("old_version_id")
        new_version_id = message.get("new_version_id")
        drawing_name = message.get("drawing_name", f"Page_{page_number:03d}")
        metadata = message.get("metadata", {})
        
        if not job_id or not page_number:
            raise ValueError("Streaming diff requires job_id and page_number")
        
        logger.info(
            "Processing streaming diff for page",
            extra={
                "job_id": job_id,
                "page_number": page_number,
                "drawing_name": drawing_name
            }
        )
        
        try:
            # Update stage to in_progress
            with self.session_factory() as db:
                stage = db.query(JobStage).filter_by(
                    job_id=job_id,
                    stage="diff",
                    page_number=page_number
                ).first()
                if stage:
                    stage.status = "in_progress"
                    stage.started_at = datetime.utcnow()
                    db.commit()
            
            # Run diff on this single page pair
            diff_result = self.pipeline.run_page(
                job_id=job_id,
                page_number=page_number,
                old_page_gcs=old_page_gcs,
                new_page_gcs=new_page_gcs,
                old_version_id=old_version_id,
                new_version_id=new_version_id,
                drawing_name=drawing_name,
                metadata=metadata
            )
            
            diff_result_id = diff_result.get("diff_result_id")
            overlay_ref = diff_result.get("overlay_ref")
            
            # Update stage to completed
            with self.session_factory() as db:
                stage = db.query(JobStage).filter_by(
                    job_id=job_id,
                    stage="diff",
                    page_number=page_number
                ).first()
                if stage:
                    stage.status = "completed"
                    stage.completed_at = datetime.utcnow()
                    stage.result_ref = diff_result_id
                    db.commit()
            
            # Immediately chain to summary for this page
            self.orchestrator.on_page_diff_complete(
                job_id=job_id,
                page_number=page_number,
                diff_result_id=diff_result_id,
                overlay_ref=overlay_ref,
                drawing_name=drawing_name
            )
            
            return {
                "job_id": job_id,
                "page_number": page_number,
                "diff_result_id": diff_result_id,
                "overlay_ref": overlay_ref,
                "status": "completed"
            }
            
        except Exception as exc:
            logger.exception(
                "Streaming diff failed",
                extra={"job_id": job_id, "page_number": page_number}
            )
            with self.session_factory() as db:
                stage = db.query(JobStage).filter_by(
                    job_id=job_id,
                    stage="diff",
                    page_number=page_number
                ).first()
                if stage:
                    stage.status = "failed"
                    stage.error_message = str(exc)
                    stage.completed_at = datetime.utcnow()
                    stage.retry_count = (stage.retry_count or 0) + 1
                    db.commit()
            raise
    
    # =========================================================================
    # LEGACY MODE: Process all pages for a job
    # =========================================================================

    def process_message(self, message: Dict) -> Dict:
        """Process a diff task message - auto-detects streaming vs legacy mode."""
        # Check if this is a streaming message - streaming data may be in metadata
        metadata = message.get("metadata", {})
        
        # Streaming messages have page_number in metadata with page GCS paths
        if metadata.get("page_number") and (metadata.get("old_page_gcs") or metadata.get("new_page_gcs")):
            logger.info("Detected streaming diff message (in metadata), routing to streaming handler")
            return self.process_streaming_message(metadata)
        
        # Also check top-level for direct streaming messages
        if message.get("page_number") and (message.get("old_page_gcs") or message.get("new_page_gcs")):
            logger.info("Detected streaming diff message (top-level), routing to streaming handler")
            return self.process_streaming_message(message)
        
        # Legacy batch mode
        job_id = message.get("job_id")
        old_version_id = message.get("old_drawing_version_id")
        new_version_id = message.get("new_drawing_version_id")
        if not all([job_id, old_version_id, new_version_id]):
            raise ValueError("Diff worker requires job_id, old_drawing_version_id, and new_drawing_version_id (legacy) or page_number with page GCS paths (streaming)")

        logger.info(
            "Processing diff message",
            extra={"job_id": job_id, "old_version_id": old_version_id, "new_version_id": new_version_id},
        )

        try:
            result_bundle = self.pipeline.run(job_id, old_version_id, new_version_id)
            diff_results: List[Dict] = result_bundle.get("diff_results", [])
            if not diff_results:
                raise ValueError("Diff pipeline produced no results")

            diff_result_ids = [entry["diff_result_id"] for entry in diff_results]

            with self.session_factory() as db:
                stage = db.query(JobStage).filter_by(job_id=job_id, stage="diff").first()
                if stage:
                    stage.status = "completed"
                    stage.completed_at = datetime.utcnow()
                    stage.result_ref = json.dumps(diff_result_ids)

            self.orchestrator.on_diff_complete(job_id, diff_results)
            return result_bundle

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

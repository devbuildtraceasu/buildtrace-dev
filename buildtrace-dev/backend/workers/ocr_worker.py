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
    
    # =========================================================================
    # STREAMING MODE: Process single page from pre-extracted PNG
    # =========================================================================
    
    def process_streaming_message(self, message: Dict) -> Dict:
        """
        Process OCR for a single page (streaming mode).
        
        Message format:
        {
            'job_id': str,
            'page_number': int,
            'old_page_gcs': str,  # GCS path to old page PNG
            'new_page_gcs': str,  # GCS path to new page PNG
            'old_version_id': str,
            'new_version_id': str,
            'drawing_name': str,
            'metadata': {...}
        }
        """
        job_id = message.get("job_id")
        page_number = message.get("page_number")
        old_page_gcs = message.get("old_page_gcs")
        new_page_gcs = message.get("new_page_gcs")
        drawing_name = message.get("drawing_name", f"Page_{page_number:03d}")
        
        if not job_id or not page_number:
            raise ValueError("Streaming OCR requires job_id and page_number")
        
        logger.info(
            "Processing streaming OCR for page",
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
                    stage="ocr",
                    page_number=page_number
                ).first()
                if stage:
                    stage.status = "in_progress"
                    stage.started_at = datetime.utcnow()
                    db.commit()
            
            # Run OCR on both page images
            old_ocr_result = self.pipeline.run_page(old_page_gcs, f"old_page_{page_number}")
            new_ocr_result = self.pipeline.run_page(new_page_gcs, f"new_page_{page_number}")
            
            old_ocr_ref = old_ocr_result.get("result_ref", "")
            new_ocr_ref = new_ocr_result.get("result_ref", "")
            
            # Update stage to completed
            with self.session_factory() as db:
                stage = db.query(JobStage).filter_by(
                    job_id=job_id,
                    stage="ocr",
                    page_number=page_number
                ).first()
                if stage:
                    stage.status = "completed"
                    stage.completed_at = datetime.utcnow()
                    stage.result_ref = f"{old_ocr_ref}|{new_ocr_ref}"
                    db.commit()
            
            # Immediately chain to diff for this page
            self.orchestrator.on_page_ocr_complete(
                job_id=job_id,
                page_number=page_number,
                old_ocr_ref=old_ocr_ref,
                new_ocr_ref=new_ocr_ref,
                drawing_name=drawing_name
            )
            
            return {
                "job_id": job_id,
                "page_number": page_number,
                "old_ocr_ref": old_ocr_ref,
                "new_ocr_ref": new_ocr_ref,
                "status": "completed"
            }
            
        except Exception as exc:
            logger.exception(
                "Streaming OCR failed",
                extra={"job_id": job_id, "page_number": page_number}
            )
            with self.session_factory() as db:
                stage = db.query(JobStage).filter_by(
                    job_id=job_id,
                    stage="ocr",
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
    # LEGACY MODE: Process entire PDF for a drawing version
    # =========================================================================

    def process_message(self, message: Dict) -> Dict:
        """Process an OCR task message - auto-detects streaming vs legacy mode."""
        # Check if this is a streaming message - streaming data may be in metadata
        metadata = message.get("metadata", {})
        
        # Streaming messages have page_number in metadata with page GCS paths
        if metadata.get("page_number") and (metadata.get("old_page_gcs") or metadata.get("new_page_gcs")):
            logger.info("Detected streaming OCR message (in metadata), routing to streaming handler")
            # Pass the metadata as the message since it contains the streaming data
            return self.process_streaming_message(metadata)
        
        # Also check top-level for direct streaming messages
        if message.get("page_number") and (message.get("old_page_gcs") or message.get("new_page_gcs")):
            logger.info("Detected streaming OCR message (top-level), routing to streaming handler")
            return self.process_streaming_message(message)
        
        # Legacy batch mode
        job_id = message.get("job_id")
        drawing_version_id = message.get("drawing_version_id")
        if not job_id or not drawing_version_id:
            raise ValueError("OCR worker requires job_id and drawing_version_id (legacy) or page_number with page GCS paths (streaming)")

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

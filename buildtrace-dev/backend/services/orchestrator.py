"""
Orchestrator Service for BuildTrace
Manages job creation and stage progression with per-page streaming support.
"""

import uuid
import logging
import threading
from datetime import datetime
from typing import Optional, List, Dict

from sqlalchemy.orm.attributes import flag_modified

from gcp.database import get_db_session
from gcp.database.models import Job, JobStage, DrawingVersion, DiffResult
from gcp.pubsub import PubSubPublisher
from config import config

logger = logging.getLogger(__name__)


def _run_in_background(func, *args, **kwargs):
    """Run a function in a background thread"""
    thread = threading.Thread(target=func, args=args, kwargs=kwargs, daemon=True)
    thread.start()
    return thread


class OrchestratorService:
    """Orchestrates job creation and stage progression with streaming support."""
    
    def __init__(self):
        self.pubsub = PubSubPublisher() if config.USE_PUBSUB else None
        # Initialize workers to None first to avoid circular dependency
        self.ocr_worker = None
        self.diff_worker = None
        self.summary_worker = None
        
        # Import workers for synchronous processing fallback
        if not config.USE_PUBSUB:
            try:
                from workers.ocr_worker import OCRWorker
                from workers.diff_worker import DiffWorker
                from workers.summary_worker import SummaryWorker
                # Pass self as orchestrator to avoid circular dependency
                self.ocr_worker = OCRWorker(orchestrator=self)
                self.diff_worker = DiffWorker(orchestrator=self)
                self.summary_worker = SummaryWorker(orchestrator=self)
                logger.info("Synchronous processing fallback enabled (Pub/Sub disabled)")
            except ImportError as e:
                logger.warning(f"Workers not available for synchronous processing: {e}")
    
    # =========================================================================
    # STREAMING PIPELINE: Per-page processing for immediate results
    # =========================================================================
    
    def create_streaming_job(
        self,
        old_version_id: str,
        new_drawing_version_id: str,
        project_id: str,
        user_id: str,
        old_pdf_gcs_path: str,
        new_pdf_gcs_path: str,
    ) -> str:
        """
        Create a streaming comparison job that processes pages independently.
        
        Each page flows through OCR → Diff → Summary immediately,
        allowing users to see results as soon as each page completes.
        
        Returns:
            str: The job ID
        """
        from services.page_extractor import get_page_extractor
        
        extractor = get_page_extractor()
        job_id = str(uuid.uuid4())
        
        logger.info(
            "Creating streaming job",
            extra={"job_id": job_id, "project_id": project_id}
        )
        
        # Extract pages from both PDFs
        old_result = extractor.extract_pages(old_pdf_gcs_path, job_id, 'old')
        new_result = extractor.extract_pages(new_pdf_gcs_path, job_id, 'new')
        
        # Use the larger page count (they should match, but handle edge cases)
        total_pages = max(old_result.total_pages, new_result.total_pages)
        
        with get_db_session() as db:
            # Create job record
            job = Job(
                id=job_id,
                project_id=project_id,
                old_drawing_version_id=old_version_id,
                new_drawing_version_id=new_drawing_version_id,
                total_pages=total_pages,
                status='in_progress',
                started_at=datetime.utcnow(),
                created_by=user_id
            )
            db.add(job)
            
            # Create per-page stages for OCR (one per page, both versions processed together)
            for page_num in range(1, total_pages + 1):
                # Get drawing names for this page
                old_page = next((p for p in old_result.pages if p.page_number == page_num), None)
                new_page = next((p for p in new_result.pages if p.page_number == page_num), None)
                
                drawing_name = new_page.drawing_name if new_page else f"Page_{page_num:03d}"
                
                # OCR stage for this page (processes both old and new)
                ocr_stage = JobStage(
                    id=str(uuid.uuid4()),
                    job_id=job_id,
                    stage='ocr',
                    page_number=page_num,
                    status='pending',
                    stage_metadata={
                        'drawing_name': drawing_name,
                        'old_page_gcs': old_page.gcs_path if old_page else None,
                        'new_page_gcs': new_page.gcs_path if new_page else None,
                    }
                )
                db.add(ocr_stage)
            
            db.commit()
            
            logger.info(
                f"Created streaming job with {total_pages} pages",
                extra={"job_id": job_id, "total_pages": total_pages}
            )
        
        # Publish OCR tasks for each page
        if self.pubsub:
            for page_num in range(1, total_pages + 1):
                old_page = next((p for p in old_result.pages if p.page_number == page_num), None)
                new_page = next((p for p in new_result.pages if p.page_number == page_num), None)
                
                message = {
                    'job_id': job_id,
                    'page_number': page_num,
                    'old_page_gcs': old_page.gcs_path if old_page else None,
                    'new_page_gcs': new_page.gcs_path if new_page else None,
                    'old_version_id': old_version_id,
                    'new_version_id': new_drawing_version_id,
                    'drawing_name': new_page.drawing_name if new_page else f"Page_{page_num:03d}",
                    'metadata': {
                        'project_id': project_id,
                        'total_pages': total_pages,
                    }
                }
                
                self.pubsub.publish_ocr_task(
                    job_id=job_id,
                    drawing_version_id=f"{old_version_id}:{new_drawing_version_id}",
                    metadata=message
                )
        elif self.ocr_worker:
            # Synchronous fallback - run in background thread
            messages = []
            for page_num in range(1, total_pages + 1):
                old_page = next((p for p in old_result.pages if p.page_number == page_num), None)
                new_page = next((p for p in new_result.pages if p.page_number == page_num), None)
                
                messages.append({
                    'job_id': job_id,
                    'page_number': page_num,
                    'old_page_gcs': old_page.gcs_path if old_page else None,
                    'new_page_gcs': new_page.gcs_path if new_page else None,
                    'old_version_id': old_version_id,
                    'new_version_id': new_drawing_version_id,
                    'drawing_name': new_page.drawing_name if new_page else f"Page_{page_num:03d}",
                    'metadata': {
                        'project_id': project_id,
                        'total_pages': total_pages,
                    }
                })
            
            # Run all pages in background thread
            _run_in_background(self._process_streaming_pages_sync, job_id, messages)
            logger.info(f"Background streaming processing started for job {job_id}")
        
        return job_id
    
    def _process_streaming_pages_sync(self, job_id: str, messages: List[Dict]):
        """Process streaming pages synchronously in background thread"""
        try:
            logger.info(f"Background streaming processing starting for job {job_id} with {len(messages)} pages")
            
            for message in messages:
                page_num = message.get('page_number', 0)
                try:
                    logger.info(f"Processing streaming page {page_num} for job {job_id}")
                    self.ocr_worker.process_streaming_message(message)
                except Exception as e:
                    logger.error(f"Streaming OCR failed for page {page_num}: {e}", exc_info=True)
            
            logger.info(f"Background streaming processing completed for job {job_id}")
        except Exception as e:
            logger.error(f"Background streaming processing failed for job {job_id}: {e}", exc_info=True)
            try:
                with get_db_session() as db:
                    job = db.query(Job).filter_by(id=job_id).first()
                    if job:
                        job.status = 'failed'
                        job.error_message = str(e)
                        db.commit()
            except Exception as db_err:
                logger.error(f"Failed to update job status: {db_err}")
    
    def on_page_ocr_complete(
        self,
        job_id: str,
        page_number: int,
        old_ocr_ref: str,
        new_ocr_ref: str,
        drawing_name: str,
    ):
        """
        Called when OCR completes for a specific page.
        Immediately triggers diff for this page (no waiting for other pages).
        """
        logger.info(
            "Page OCR complete, triggering diff",
            extra={"job_id": job_id, "page_number": page_number, "drawing_name": drawing_name}
        )
        
        with get_db_session() as db:
            # Update OCR stage status
            ocr_stage = db.query(JobStage).filter_by(
                job_id=job_id,
                stage='ocr',
                page_number=page_number
            ).first()
            
            if ocr_stage:
                ocr_stage.status = 'completed'
                ocr_stage.completed_at = datetime.utcnow()
                ocr_stage.result_ref = f"{old_ocr_ref}|{new_ocr_ref}"
            
            # Create diff stage for this page
            diff_stage = JobStage(
                id=str(uuid.uuid4()),
                job_id=job_id,
                stage='diff',
                page_number=page_number,
                status='in_progress',
                started_at=datetime.utcnow(),
                stage_metadata={'drawing_name': drawing_name}
            )
            db.add(diff_stage)
            
            job = db.query(Job).filter_by(id=job_id).first()
            old_version_id = job.old_drawing_version_id
            new_version_id = job.new_drawing_version_id
            project_id = job.project_id
            total_pages = job.total_pages
            
            # Get page GCS paths from OCR stage metadata
            stage_meta = ocr_stage.stage_metadata or {}
            old_page_gcs = stage_meta.get('old_page_gcs')
            new_page_gcs = stage_meta.get('new_page_gcs')
            
            db.commit()
        
        # Publish diff task for this page
        message = {
            'job_id': job_id,
            'page_number': page_number,
            'old_version_id': old_version_id,
            'new_version_id': new_version_id,
            'old_page_gcs': old_page_gcs,
            'new_page_gcs': new_page_gcs,
            'old_ocr_ref': old_ocr_ref,
            'new_ocr_ref': new_ocr_ref,
            'drawing_name': drawing_name,
            'metadata': {
                'project_id': project_id,
                'total_pages': total_pages,
            }
        }
        
        if self.pubsub:
            self.pubsub.publish_diff_task(
                job_id=job_id,
                old_version_id=old_version_id,
                new_version_id=new_version_id,
                metadata=message
            )
        elif self.diff_worker:
            try:
                self.diff_worker.process_streaming_message(message)
            except Exception as e:
                logger.error(f"Streaming diff failed for page {page_number}: {e}")
                self._mark_page_stage_failed(job_id, 'diff', page_number, str(e))
    
    def on_page_diff_complete(
        self,
        job_id: str,
        page_number: int,
        diff_result_id: str,
        overlay_ref: str,
        drawing_name: str,
    ):
        """
        Called when diff completes for a specific page.
        Immediately triggers summary for this page (no waiting for other pages).
        """
        logger.info(
            "Page diff complete, triggering summary",
            extra={"job_id": job_id, "page_number": page_number, "diff_result_id": diff_result_id}
        )
        
        with get_db_session() as db:
            # Update diff stage status
            diff_stage = db.query(JobStage).filter_by(
                job_id=job_id,
                stage='diff',
                page_number=page_number
            ).first()
            
            if diff_stage:
                diff_stage.status = 'completed'
                diff_stage.completed_at = datetime.utcnow()
                diff_stage.result_ref = diff_result_id
            
            # Create summary stage for this page
            summary_stage = JobStage(
                id=str(uuid.uuid4()),
                job_id=job_id,
                stage='summary',
                page_number=page_number,
                status='in_progress',
                started_at=datetime.utcnow(),
                stage_metadata={'drawing_name': drawing_name, 'diff_result_id': diff_result_id}
            )
            db.add(summary_stage)
            
            job = db.query(Job).filter_by(id=job_id).first()
            project_id = job.project_id
            total_pages = job.total_pages
            
            db.commit()
        
        # Publish summary task for this page
        message = {
            'job_id': job_id,
            'page_number': page_number,
            'diff_result_id': diff_result_id,
            'overlay_ref': overlay_ref,
            'drawing_name': drawing_name,
            'metadata': {
                'project_id': project_id,
                'total_pages': total_pages,
            }
        }
        
        if self.pubsub:
            self.pubsub.publish_summary_task(
                job_id=job_id,
                diff_result_id=diff_result_id,
                overlay_ref=overlay_ref,
                metadata=message
            )
        elif self.summary_worker:
            try:
                self.summary_worker.process_message(message)
            except Exception as e:
                logger.error(f"Streaming summary failed for page {page_number}: {e}")
                self._mark_page_stage_failed(job_id, 'summary', page_number, str(e))
    
    def on_page_summary_complete(self, job_id: str, page_number: int, summary_id: str):
        """
        Called when summary completes for a specific page.
        Checks if all pages are done and marks job complete if so.
        """
        logger.info(
            "Page summary complete",
            extra={"job_id": job_id, "page_number": page_number, "summary_id": summary_id}
        )
        
        with get_db_session() as db:
            # Update summary stage status
            summary_stage = db.query(JobStage).filter_by(
                job_id=job_id,
                stage='summary',
                page_number=page_number
            ).first()
            
            if summary_stage:
                summary_stage.status = 'completed'
                summary_stage.completed_at = datetime.utcnow()
                summary_stage.result_ref = summary_id
            
            # Check if all pages have completed summaries
            job = db.query(Job).filter_by(id=job_id).first()
            if not job:
                return
            
            completed_summaries = db.query(JobStage).filter_by(
                job_id=job_id,
                stage='summary',
                status='completed'
            ).count()
            
            if completed_summaries >= job.total_pages:
                job.status = 'completed'
                job.completed_at = datetime.utcnow()
                logger.info(f"All {job.total_pages} pages complete. Job {job_id} finished!")
            
            db.commit()
    
    def _mark_page_stage_failed(self, job_id: str, stage: str, page_number: int, error: str):
        """Mark a specific page's stage as failed."""
        with get_db_session() as db:
            stage_record = db.query(JobStage).filter_by(
                job_id=job_id,
                stage=stage,
                page_number=page_number
            ).first()
            
            if stage_record:
                stage_record.status = 'failed'
                stage_record.error_message = error
                stage_record.completed_at = datetime.utcnow()
                stage_record.retry_count = (stage_record.retry_count or 0) + 1
            
            db.commit()
    
    # =========================================================================
    # LEGACY: Batch processing (kept for backward compatibility)
    # =========================================================================
    
    def create_comparison_job(
        self,
        old_version_id: str,
        new_drawing_version_id: str,
        project_id: str,
        user_id: str
    ) -> str:
        """Create a new comparison job and enqueue OCR tasks (legacy batch mode)

        Returns:
            str: The job ID
        """
        with get_db_session() as db:
            # Create job record
            job = Job(
                id=str(uuid.uuid4()),
                project_id=project_id,
                old_drawing_version_id=old_version_id,
                new_drawing_version_id=new_drawing_version_id,
                status='created',
                created_by=user_id
            )
            db.add(job)
            db.flush()  # Get job.id
            
            # Create job stages (legacy: one stage per type)
            ocr_stage_old = JobStage(
                id=str(uuid.uuid4()),
                job_id=job.id,
                stage='ocr',
                drawing_version_id=old_version_id,
                status='pending'
            )
            ocr_stage_new = JobStage(
                id=str(uuid.uuid4()),
                job_id=job.id,
                stage='ocr',
                drawing_version_id=new_drawing_version_id,
                status='pending'
            )
            diff_stage = JobStage(
                id=str(uuid.uuid4()),
                job_id=job.id,
                stage='diff',
                status='pending'
            )
            summary_stage = JobStage(
                id=str(uuid.uuid4()),
                job_id=job.id,
                stage='summary',
                status='pending'
            )
            
            db.add_all([ocr_stage_old, ocr_stage_new, diff_stage, summary_stage])
            db.commit()
            
            # Publish OCR tasks if Pub/Sub is enabled
            if self.pubsub:
                old_version = db.query(DrawingVersion).filter_by(id=old_version_id).first()
                new_version = db.query(DrawingVersion).filter_by(id=new_drawing_version_id).first()
                
                if old_version and new_version:
                    try:
                        self.pubsub.publish_ocr_task(
                            job_id=job.id,
                            drawing_version_id=old_version_id,
                            metadata={
                                'project_id': project_id,
                                'storage_path': old_version.drawing.storage_path if old_version.drawing else None
                            }
                        )
                        
                        self.pubsub.publish_ocr_task(
                            job_id=job.id,
                            drawing_version_id=new_drawing_version_id,
                            metadata={
                                'project_id': project_id,
                                'storage_path': new_version.drawing.storage_path if new_version.drawing else None
                            }
                        )
                        
                        # Update job status
                        job.status = 'in_progress'
                        job.started_at = datetime.utcnow()
                        db.commit()
                        
                        logger.info(f"Created job {job.id} and published OCR tasks")
                    except Exception as e:
                        logger.error(f"Failed to publish OCR tasks: {e}")
            else:
                # Synchronous processing fallback - run in background thread
                logger.info("Pub/Sub not enabled - processing in background thread")
                job.status = 'in_progress'
                job.started_at = datetime.utcnow()
                db.commit()
                
                if self.ocr_worker:
                    # Run processing in background thread so upload returns immediately
                    _run_in_background(
                        self._process_job_sync,
                        job.id,
                        old_version_id,
                        new_drawing_version_id,
                        project_id
                    )
                    logger.info(f"Background processing started for job {job.id}")
                else:
                    logger.warning("Synchronous processing not available - workers not initialized")

            # Extract job_id before session closes to avoid DetachedInstanceError
            job_id = job.id

        return job_id
    
    def _process_job_sync(
        self,
        job_id: str,
        old_version_id: str,
        new_drawing_version_id: str,
        project_id: str
    ):
        """Process job synchronously in background thread"""
        try:
            logger.info(f"Background processing starting for job {job_id}")
            
            # Process OCR for old version
            logger.info(f"Processing OCR for old version {old_version_id}")
            self.ocr_worker.process_message({
                'job_id': job_id,
                'drawing_version_id': old_version_id,
                'metadata': {'project_id': project_id}
            })
            
            # Process OCR for new version
            logger.info(f"Processing OCR for new version {new_drawing_version_id}")
            self.ocr_worker.process_message({
                'job_id': job_id,
                'drawing_version_id': new_drawing_version_id,
                'metadata': {'project_id': project_id}
            })
            
            logger.info(f"Background processing completed for job {job_id}")
        except Exception as e:
            logger.error(f"Background processing failed for job {job_id}: {e}", exc_info=True)
            try:
                with get_db_session() as db:
                    job = db.query(Job).filter_by(id=job_id).first()
                    if job:
                        job.status = 'failed'
                        job.error_message = str(e)
                        db.commit()
            except Exception as db_err:
                logger.error(f"Failed to update job status: {db_err}")
    
    def on_ocr_complete(self, job_id: str, drawing_version_id: str):
        """Called when OCR stage completes - check if ready for diff (legacy)"""
        with get_db_session() as db:
            job = db.query(Job).filter_by(id=job_id).first()
            if not job:
                logger.error(f"Job {job_id} not found")
                return
            
            ocr_stages = db.query(JobStage).filter_by(
                job_id=job_id,
                stage='ocr'
            ).all()
            
            # Check if both OCR stages are complete
            if all(stage.status == 'completed' for stage in ocr_stages):
                # Update diff stage and publish diff task
                diff_stage = db.query(JobStage).filter_by(
                    job_id=job_id,
                    stage='diff'
                ).first()
                
                if diff_stage and diff_stage.status == 'pending':
                    diff_stage.status = 'in_progress'
                    diff_stage.started_at = datetime.utcnow()
                    
                    if self.pubsub:
                        try:
                            self.pubsub.publish_diff_task(
                                job_id=job_id,
                                old_version_id=job.old_drawing_version_id,
                                new_version_id=job.new_drawing_version_id,
                                metadata={'project_id': job.project_id}
                            )
                            logger.info(f"Published diff task for job {job_id}")
                        except Exception as e:
                            logger.error(f"Failed to publish diff task: {e}")
                            diff_stage.status = 'failed'
                            diff_stage.error_message = str(e)
                    elif self.diff_worker:
                        # Synchronous processing fallback
                        try:
                            logger.info(f"Processing diff synchronously for job {job_id}")
                            result = self.diff_worker.process_message({
                                'job_id': job_id,
                                'old_drawing_version_id': job.old_drawing_version_id,
                                'new_drawing_version_id': job.new_drawing_version_id,
                                'metadata': {'project_id': job.project_id}
                            })
                            logger.info(f"Diff processing completed for job {job_id}")
                        except Exception as e:
                            logger.error(f"Synchronous diff processing failed: {e}", exc_info=True)
                            diff_stage.status = 'failed'
                            diff_stage.error_message = str(e)
                    
                    db.commit()
            else:
                logger.info(f"Job {job_id}: Waiting for other OCR stage to complete")
    
    def on_diff_complete(self, job_id: str, diff_results: List[Dict]):
        """Called when diff stage completes - enqueue summary tasks for each page (legacy)."""
        if not diff_results:
            logger.warning(f"No diff results provided for job {job_id}")
            return

        project_id = None
        with get_db_session() as db:
            diff_stage = db.query(JobStage).filter_by(
                job_id=job_id,
                stage='diff'
            ).first()
            
            if diff_stage:
                diff_stage.status = 'completed'
                diff_stage.completed_at = datetime.utcnow()
                if diff_stage.job:
                    project_id = diff_stage.job.project_id
            
            summary_stage = db.query(JobStage).filter_by(
                job_id=job_id,
                stage='summary'
            ).first()
            
            if summary_stage:
                summary_stage.status = 'in_progress'
                summary_stage.started_at = summary_stage.started_at or datetime.utcnow()
                stage_meta = summary_stage.stage_metadata or {}
                stage_meta['expected_summaries'] = len(diff_results)
                stage_meta['completed_summaries'] = stage_meta.get('completed_summaries', 0)
                summary_stage.stage_metadata = stage_meta
                flag_modified(summary_stage, 'stage_metadata')
            
            db.commit()

        for diff_entry in diff_results:
            diff_result_id = diff_entry.get("diff_result_id")
            overlay_ref = diff_entry.get("overlay_ref")
            metadata = {
                'project_id': project_id,
                'page_number': diff_entry.get("page_number"),
                'total_pages': diff_entry.get("total_pages"),
                'drawing_name': diff_entry.get("drawing_name"),
            }
            
            if self.pubsub:
                try:
                    self.pubsub.publish_summary_task(
                        job_id=job_id,
                        diff_result_id=diff_result_id,
                        overlay_ref=overlay_ref,
                        metadata=metadata,
                    )
                    logger.info(
                        "Published summary task for page",
                        extra={
                            "job_id": job_id,
                            "diff_result_id": diff_result_id,
                            "page_number": diff_entry.get("page_number"),
                        },
                    )
                except Exception as e:
                    logger.error(f"Failed to publish summary task for {diff_result_id}: {e}")
                    self._mark_summary_stage_failed(job_id, str(e))
                    break
            elif self.summary_worker:
                try:
                    logger.info(
                        "Processing summary synchronously for page",
                        extra={"job_id": job_id, "diff_result_id": diff_result_id},
                    )
                    self.summary_worker.process_message(
                        {
                            'job_id': job_id,
                            'diff_result_id': diff_result_id,
                            'overlay_ref': overlay_ref,
                            'metadata': metadata,
                        }
                    )
                except Exception as e:
                    logger.error(f"Synchronous summary processing failed: {e}", exc_info=True)
                    self._mark_summary_stage_failed(job_id, str(e))
                    break
    
    def on_summary_complete(self, job_id: str):
        """Called when summary stage completes - mark job complete (legacy)"""
        with get_db_session() as db:
            job = db.query(Job).filter_by(id=job_id).first()
            if job:
                job.status = 'completed'
                job.completed_at = datetime.utcnow()
                db.commit()
                logger.info(f"Job {job_id} completed")

    def _mark_summary_stage_failed(self, job_id: str, error_message: str):
        """Helper to mark summary stage as failed (legacy)."""
        with get_db_session() as db:
            stage = db.query(JobStage).filter_by(job_id=job_id, stage='summary').first()
            if stage:
                stage.status = 'failed'
                stage.error_message = error_message
                stage.completed_at = datetime.utcnow()
            job = db.query(Job).filter_by(id=job_id).first()
            if job:
                job.status = 'failed'
                job.error_message = error_message
                job.completed_at = datetime.utcnow()
            db.commit()
    
    def trigger_summary_regeneration(self, diff_result_id: str, overlay_id: Optional[str] = None):
        """Trigger summary regeneration with optional manual overlay"""
        with get_db_session() as db:
            from gcp.database.models import ManualOverlay
            
            diff_result = db.query(DiffResult).filter_by(id=diff_result_id).first()
            if not diff_result:
                raise ValueError(f"Diff result {diff_result_id} not found")
            
            job = diff_result.job
            
            # Create new summary stage
            summary_stage = JobStage(
                id=str(uuid.uuid4()),
                job_id=job.id,
                stage='summary',
                page_number=diff_result.page_number,
                status='in_progress',
                started_at=datetime.utcnow()
            )
            db.add(summary_stage)
            
            # Get overlay reference - use manual overlay if provided, otherwise use machine-generated
            overlay_ref = None
            if overlay_id:
                overlay = db.query(ManualOverlay).filter_by(id=overlay_id).first()
                if overlay:
                    overlay_ref = overlay.overlay_ref
            
            # Fall back to machine-generated overlay from diff_metadata
            if not overlay_ref and diff_result.diff_metadata:
                overlay_ref = diff_result.diff_metadata.get('overlay_image_ref')
            
            metadata = {
                'project_id': job.project_id,
                'page_number': diff_result.page_number,
                'use_manual_overlay': overlay_id is not None,
                'overlay_id': overlay_id,
            }

            if self.pubsub:
                try:
                    self.pubsub.publish_summary_task(
                        job_id=job.id,
                        diff_result_id=diff_result_id,
                        overlay_ref=overlay_ref,
                        metadata=metadata,
                    )
                    logger.info(f"Published summary regeneration task for diff {diff_result_id}")
                except Exception as e:
                    logger.error(f"Failed to publish summary task: {e}")
                    summary_stage.status = 'failed'
                    summary_stage.error_message = str(e)
            elif self.summary_worker:
                try:
                    self.summary_worker.process_message({
                        'job_id': job.id,
                        'diff_result_id': diff_result_id,
                        'overlay_ref': overlay_ref,
                        'metadata': metadata,
                    })
                except Exception as exc:
                    logger.error(f"Synchronous summary regeneration failed: {exc}")
                    summary_stage.status = 'failed'
                    summary_stage.error_message = str(exc)

            db.commit()
            return summary_stage

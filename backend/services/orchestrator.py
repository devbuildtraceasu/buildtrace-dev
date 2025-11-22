"""
Orchestrator Service for BuildTrace
Manages job creation and stage progression
"""

import uuid
import logging
from datetime import datetime
from typing import Optional
from gcp.database import get_db_session
from gcp.database.models import Job, JobStage, DrawingVersion
from gcp.pubsub import PubSubPublisher
from config import config

logger = logging.getLogger(__name__)

class OrchestratorService:
    """Orchestrates job creation and stage progression"""
    
    def __init__(self):
        self.pubsub = PubSubPublisher() if config.USE_PUBSUB else None
        # Import workers for synchronous processing fallback
        if not config.USE_PUBSUB:
            try:
                from workers.ocr_worker import OCRWorker
                from workers.diff_worker import DiffWorker
                from workers.summary_worker import SummaryWorker
                self.ocr_worker = OCRWorker()
                self.diff_worker = DiffWorker()
                self.summary_worker = SummaryWorker()
                logger.info("Synchronous processing fallback enabled (Pub/Sub disabled)")
            except ImportError as e:
                logger.warning(f"Workers not available for synchronous processing: {e}")
                self.ocr_worker = None
                self.diff_worker = None
                self.summary_worker = None
        else:
            self.ocr_worker = None
            self.diff_worker = None
            self.summary_worker = None
    
    def create_comparison_job(
        self, 
        old_version_id: str, 
        new_drawing_version_id: str,
        project_id: str,
        user_id: str
    ) -> Job:
        """Create a new comparison job and enqueue OCR tasks"""
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
            
            # Create job stages
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
                        # Job is still created, but tasks weren't published
                        # Workers can poll for pending stages or we can retry
            else:
                # Synchronous processing fallback for development
                logger.info("Pub/Sub not enabled - processing synchronously")
                if self.ocr_worker:
                    try:
                        job.status = 'in_progress'
                        job.started_at = datetime.utcnow()
                        db.commit()
                        
                        # Process OCR tasks synchronously
                        logger.info(f"Processing OCR for old version {old_version_id}")
                        self.ocr_worker.process_message({
                            'job_id': job.id,
                            'drawing_version_id': old_version_id,
                            'metadata': {'project_id': project_id}
                        })
                        
                        logger.info(f"Processing OCR for new version {new_drawing_version_id}")
                        self.ocr_worker.process_message({
                            'job_id': job.id,
                            'drawing_version_id': new_drawing_version_id,
                            'metadata': {'project_id': project_id}
                        })
                        
                        logger.info(f"Job {job.id} processed synchronously")
                    except Exception as e:
                        logger.error(f"Synchronous processing failed: {e}", exc_info=True)
                        job.status = 'failed'
                        job.error_message = str(e)
                        db.commit()
                else:
                    logger.warning("Synchronous processing not available - workers not initialized")
            
            return job
    
    def on_ocr_complete(self, job_id: str, drawing_version_id: str):
        """Called when OCR stage completes - check if ready for diff"""
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
    
    def on_diff_complete(self, job_id: str, diff_result_id: str):
        """Called when diff stage completes - enqueue summary"""
        with get_db_session() as db:
            diff_stage = db.query(JobStage).filter_by(
                job_id=job_id,
                stage='diff'
            ).first()
            
            if diff_stage:
                diff_stage.status = 'completed'
                diff_stage.completed_at = datetime.utcnow()
            
            summary_stage = db.query(JobStage).filter_by(
                job_id=job_id,
                stage='summary'
            ).first()
            
            if summary_stage and summary_stage.status == 'pending':
                summary_stage.status = 'in_progress'
                summary_stage.started_at = datetime.utcnow()
                
                if self.pubsub:
                    try:
                        self.pubsub.publish_summary_task(
                            job_id=job_id,
                            diff_result_id=diff_result_id,
                            metadata={'project_id': diff_stage.job.project_id}
                        )
                        logger.info(f"Published summary task for job {job_id}")
                    except Exception as e:
                        logger.error(f"Failed to publish summary task: {e}")
                        summary_stage.status = 'failed'
                        summary_stage.error_message = str(e)
                elif self.summary_worker:
                    # Synchronous processing fallback
                    try:
                        logger.info(f"Processing summary synchronously for job {job_id}")
                        result = self.summary_worker.process_message({
                            'job_id': job_id,
                            'diff_result_id': diff_result_id,
                            'overlay_ref': None,
                            'metadata': {'project_id': diff_stage.job.project_id}
                        })
                        logger.info(f"Summary processing completed for job {job_id}")
                    except Exception as e:
                        logger.error(f"Synchronous summary processing failed: {e}", exc_info=True)
                        summary_stage.status = 'failed'
                        summary_stage.error_message = str(e)
                
                db.commit()
    
    def on_summary_complete(self, job_id: str):
        """Called when summary stage completes - mark job complete"""
        with get_db_session() as db:
            job = db.query(Job).filter_by(id=job_id).first()
            if job:
                job.status = 'completed'
                job.completed_at = datetime.utcnow()
                db.commit()
                logger.info(f"Job {job_id} completed")
    
    def trigger_summary_regeneration(self, diff_result_id: str, overlay_id: Optional[str] = None):
        """Trigger summary regeneration with optional manual overlay"""
        with get_db_session() as db:
            from gcp.database.models import DiffResult, ManualOverlay
            
            diff_result = db.query(DiffResult).filter_by(id=diff_result_id).first()
            if not diff_result:
                raise ValueError(f"Diff result {diff_result_id} not found")
            
            job = diff_result.job
            
            # Create new summary stage
            summary_stage = JobStage(
                id=str(uuid.uuid4()),
                job_id=job.id,
                stage='summary',
                status='in_progress',
                started_at=datetime.utcnow()
            )
            db.add(summary_stage)
            
            # Get overlay reference if provided
            overlay_ref = None
            if overlay_id:
                overlay = db.query(ManualOverlay).filter_by(id=overlay_id).first()
                if overlay:
                    overlay_ref = overlay.overlay_ref
            
            metadata = {
                'project_id': job.project_id,
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

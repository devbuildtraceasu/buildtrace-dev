#!/usr/bin/env python3
"""
Background Job Processor for BuildTrace
Handles heavy image processing tasks asynchronously
"""

import os
import sys
import time
import logging
from datetime import datetime
from gcp.database import get_db_session
from gcp.database.models import Session, Drawing, ProcessingJob
from complete_drawing_pipeline import complete_drawing_pipeline
from gcp.storage import storage_service

def store_processing_results(session_id, results, db):
    """Store processing results in the database"""
    try:
        from gcp.database.models import Session, Drawing, Comparison, AnalysisResult

        # Get session and drawings
        session = db.query(Session).filter_by(id=session_id).first()
        if not session:
            raise Exception(f"Session {session_id} not found")

        drawings = db.query(Drawing).filter_by(session_id=session_id).all()
        old_drawing = next((d for d in drawings if d.drawing_type == 'old'), None)
        new_drawing = next((d for d in drawings if d.drawing_type == 'new'), None)

        if not old_drawing or not new_drawing:
            raise Exception("Required drawings not found")

        # Process comparison results
        comparison_results = results.get('comparison_results', {})
        analysis_results = results.get('analysis_results', [])

        # Handle different result structures
        overlays_created = comparison_results.get('successful_overlays', 0)
        if overlays_created > 0:
            # Create comparison records based on analysis results
            for i, analysis_data in enumerate(analysis_results):
                if isinstance(analysis_data, dict):
                    drawing_name = analysis_data.get('drawing_name', f'Drawing {i+1}')

                    # Check if comparison already exists
                    existing_comparison = db.query(Comparison).filter_by(
                        session_id=session_id,
                        drawing_name=drawing_name
                    ).first()

                    if existing_comparison:
                        continue  # Skip if already exists

                    # Create comparison record
                    comparison = Comparison(
                        session_id=session_id,
                        old_drawing_id=old_drawing.id,
                        new_drawing_id=new_drawing.id,
                        drawing_name=drawing_name,
                        changes_detected=bool(analysis_data.get('critical_change'))
                    )
                    db.add(comparison)
                    db.flush()  # Get the ID

                    # Add analysis result
                    # Parse changes_found if it's a string
                    changes_found = analysis_data.get('changes_found', [])
                    if isinstance(changes_found, str):
                        # Try to extract bullet points from summary
                        changes_found = [line.strip('- •') for line in changes_found.split('\n') if line.strip().startswith(('-', '•'))]

                    analysis_result = AnalysisResult(
                        comparison_id=comparison.id,
                        drawing_name=drawing_name,
                        critical_change=analysis_data.get('critical_change', ''),
                        analysis_summary=analysis_data.get('analysis_summary', ''),
                        changes_found=changes_found if changes_found else None,
                        recommendations=analysis_data.get('recommendations', None),
                        success=analysis_data.get('success', True)
                    )
                    db.add(analysis_result)

        db.commit()
        logger.info(f"✅ Stored {len(analysis_results)} comparison results in database")

    except Exception as e:
        logger.error(f"❌ Error storing processing results: {e}")
        db.rollback()
        raise

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class JobProcessor:
    def __init__(self):
        self.running = True

    def process_jobs(self):
        """Main job processing loop"""
        logger.info("Starting job processor...")

        while self.running:
            try:
                with get_db_session() as db:
                    # Get next pending job
                    job = db.query(ProcessingJob).filter_by(
                        status='pending'
                    ).order_by(ProcessingJob.created_at).first()

                    if job:
                        self.process_job(job, db)
                    else:
                        time.sleep(5)  # Wait 5 seconds if no jobs

            except Exception as e:
                logger.error(f"Error in job processing loop: {e}")
                time.sleep(10)

    def process_job(self, job, db):
        """Process a single job"""
        try:
            logger.info(f"Processing job {job.id} for session {job.session_id}")

            # Update job status
            job.status = 'processing'
            job.started_at = datetime.utcnow()
            db.commit()

            # Get session and drawings
            session = db.query(Session).filter_by(id=job.session_id).first()
            if not session:
                raise Exception(f"Session {job.session_id} not found")

            drawings = db.query(Drawing).filter_by(session_id=job.session_id).all()
            old_drawing = next((d for d in drawings if d.drawing_type == 'old'), None)
            new_drawing = next((d for d in drawings if d.drawing_type == 'new'), None)

            if not old_drawing or not new_drawing:
                raise Exception("Required drawings not found")

            # Download files to temporary directory
            import tempfile
            with tempfile.TemporaryDirectory() as temp_dir:
                old_temp_path = os.path.join(temp_dir, old_drawing.filename)
                new_temp_path = os.path.join(temp_dir, new_drawing.filename)

                # Download from cloud storage
                storage_service.download_to_filename(old_drawing.storage_path, old_temp_path)
                storage_service.download_to_filename(new_drawing.storage_path, new_temp_path)

                # Process files
                logger.info("Starting drawing comparison pipeline...")
                results = complete_drawing_pipeline(
                    old_pdf_path=old_temp_path,
                    new_pdf_path=new_temp_path,
                    dpi=300,
                    debug=False,
                    skip_ai_analysis=False
                )

                # Store results
                if results['success']:
                    # Store analysis results in database
                    store_processing_results(job.session_id, results, db)

                    # Update session with processing time
                    session.total_time = results.get('summary', {}).get('total_time', 0.0)

                    job.status = 'completed'
                    job.completed_at = datetime.utcnow()
                    job.result = {'success': True, 'message': 'Processing completed successfully'}

                    session.status = 'completed'
                    logger.info(f"Job {job.id} completed successfully")
                else:
                    raise Exception(f"Pipeline failed: {results.get('error', 'Unknown error')}")

        except Exception as e:
            logger.error(f"Job {job.id} failed: {e}")
            job.status = 'failed'
            job.completed_at = datetime.utcnow()
            job.result = {'success': False, 'error': str(e)}

            if 'session' in locals():
                session.status = 'error'

        finally:
            db.commit()

if __name__ == "__main__":
    processor = JobProcessor()
    processor.process_jobs()
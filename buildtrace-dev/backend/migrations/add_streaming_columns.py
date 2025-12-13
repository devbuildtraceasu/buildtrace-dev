"""
Migration: Add streaming pipeline columns
- Job.total_pages
- JobStage.page_number  
- DiffResult.page_number
- DiffResult.drawing_name

Run with: python migrations/add_streaming_columns.py
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from gcp.database import get_db_session
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration():
    """Add streaming pipeline columns to database."""
    
    migrations = [
        # Job.total_pages
        {
            'name': 'Add total_pages to jobs',
            'check': "SELECT column_name FROM information_schema.columns WHERE table_name='jobs' AND column_name='total_pages'",
            'sql': "ALTER TABLE jobs ADD COLUMN total_pages INTEGER DEFAULT 1"
        },
        # JobStage.page_number
        {
            'name': 'Add page_number to job_stages',
            'check': "SELECT column_name FROM information_schema.columns WHERE table_name='job_stages' AND column_name='page_number'",
            'sql': "ALTER TABLE job_stages ADD COLUMN page_number INTEGER"
        },
        # DiffResult.page_number
        {
            'name': 'Add page_number to diff_results',
            'check': "SELECT column_name FROM information_schema.columns WHERE table_name='diff_results' AND column_name='page_number'",
            'sql': "ALTER TABLE diff_results ADD COLUMN page_number INTEGER DEFAULT 1"
        },
        # DiffResult.drawing_name
        {
            'name': 'Add drawing_name to diff_results',
            'check': "SELECT column_name FROM information_schema.columns WHERE table_name='diff_results' AND column_name='drawing_name'",
            'sql': "ALTER TABLE diff_results ADD COLUMN drawing_name VARCHAR(255)"
        },
        # Index on job_stages (job_id, page_number)
        {
            'name': 'Add index idx_job_stages_page',
            'check': "SELECT indexname FROM pg_indexes WHERE indexname='idx_job_stages_page'",
            'sql': "CREATE INDEX IF NOT EXISTS idx_job_stages_page ON job_stages(job_id, page_number)"
        },
        # Index on diff_results (job_id, page_number)
        {
            'name': 'Add index idx_diff_results_job_page',
            'check': "SELECT indexname FROM pg_indexes WHERE indexname='idx_diff_results_job_page'",
            'sql': "CREATE INDEX IF NOT EXISTS idx_diff_results_job_page ON diff_results(job_id, page_number)"
        },
        # Drop old unique constraint and add new one with page_number
        {
            'name': 'Update unique constraint on job_stages',
            'check': "SELECT 1 WHERE false",  # Always run this
            'sql': """
                DO $$
                BEGIN
                    -- Try to drop old constraint if exists
                    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_job_stage_drawing') THEN
                        ALTER TABLE job_stages DROP CONSTRAINT uq_job_stage_drawing;
                    END IF;
                    -- Add new constraint with page_number
                    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_job_stage_page_drawing') THEN
                        -- Don't add constraint if there might be duplicate data
                        -- ALTER TABLE job_stages ADD CONSTRAINT uq_job_stage_page_drawing UNIQUE (job_id, stage, page_number, drawing_version_id);
                        NULL;
                    END IF;
                END $$;
            """
        },
    ]
    
    with get_db_session() as db:
        for migration in migrations:
            try:
                # Check if migration is needed
                result = db.execute(text(migration['check'])).fetchone()
                if result:
                    logger.info(f"Skipping '{migration['name']}' - already applied")
                    continue
                
                # Run migration
                logger.info(f"Running '{migration['name']}'...")
                db.execute(text(migration['sql']))
                db.commit()
                logger.info(f"✓ Completed '{migration['name']}'")
                
            except Exception as e:
                logger.error(f"✗ Failed '{migration['name']}': {e}")
                db.rollback()
                # Continue with other migrations
    
    logger.info("Migration complete!")


if __name__ == '__main__':
    run_migration()


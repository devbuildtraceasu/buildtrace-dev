#!/usr/bin/env python3
"""
Run database migrations
This script checks and applies any pending schema changes
"""

import logging
from sqlalchemy import create_engine, text
from config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migrations():
    """Run all pending database migrations"""

    if not config.USE_DATABASE:
        logger.info("Database not configured, skipping migrations")
        return

    # Build database URL
    if config.ENVIRONMENT == 'production':
        db_url = f"postgresql+psycopg2://{config.DB_USER}:{config.DB_PASS}@/{config.DB_NAME}?host=/cloudsql/{config.INSTANCE_CONNECTION_NAME}"
    else:
        db_url = f"postgresql+psycopg2://{config.DB_USER}:{config.DB_PASS}@localhost:5432/{config.DB_NAME}"

    logger.info(f"Connecting to database: {config.DB_NAME}")

    try:
        engine = create_engine(db_url, echo=False)

        with engine.connect() as conn:
            # Migration 1: Add stage_metadata column to job_stages if it doesn't exist
            logger.info("Checking for stage_metadata column in job_stages...")

            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='job_stages'
                AND column_name='stage_metadata'
            """))

            if not result.fetchone():
                logger.info("Adding stage_metadata column to job_stages table...")
                conn.execute(text("""
                    ALTER TABLE job_stages
                    ADD COLUMN stage_metadata JSONB
                """))
                conn.commit()
                logger.info("✓ Successfully added stage_metadata column")
            else:
                logger.info("✓ Column stage_metadata already exists")

            # Migration 2: Add total_pages column to jobs if it doesn't exist
            logger.info("Checking for total_pages column in jobs...")
            
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='jobs'
                AND column_name='total_pages'
            """))
            
            if not result.fetchone():
                logger.info("Adding total_pages column to jobs table...")
                conn.execute(text("""
                    ALTER TABLE jobs
                    ADD COLUMN total_pages INTEGER
                """))
                conn.commit()
                logger.info("✓ Successfully added total_pages column to jobs")
            else:
                logger.info("✓ Column total_pages already exists in jobs")

            # Migration 3: Add page_number column to job_stages if it doesn't exist
            logger.info("Checking for page_number column in job_stages...")
            
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='job_stages'
                AND column_name='page_number'
            """))
            
            if not result.fetchone():
                logger.info("Adding page_number column to job_stages table...")
                conn.execute(text("""
                    ALTER TABLE job_stages
                    ADD COLUMN page_number INTEGER
                """))
                conn.commit()
                logger.info("✓ Successfully added page_number column to job_stages")
            else:
                logger.info("✓ Column page_number already exists in job_stages")

            # Migration 4: Add page_number column to diff_results if it doesn't exist
            logger.info("Checking for page_number column in diff_results...")
            
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='diff_results'
                AND column_name='page_number'
            """))
            
            if not result.fetchone():
                logger.info("Adding page_number column to diff_results table...")
                conn.execute(text("""
                    ALTER TABLE diff_results
                    ADD COLUMN page_number INTEGER
                """))
                conn.commit()
                logger.info("✓ Successfully added page_number column to diff_results")
            else:
                logger.info("✓ Column page_number already exists in diff_results")

            # Migration 5: Add drawing_name column to diff_results if it doesn't exist
            logger.info("Checking for drawing_name column in diff_results...")
            
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='diff_results'
                AND column_name='drawing_name'
            """))
            
            if not result.fetchone():
                logger.info("Adding drawing_name column to diff_results table...")
                conn.execute(text("""
                    ALTER TABLE diff_results
                    ADD COLUMN drawing_name VARCHAR(255)
                """))
                conn.commit()
                logger.info("✓ Successfully added drawing_name column to diff_results")
            else:
                logger.info("✓ Column drawing_name already exists in diff_results")

        engine.dispose()
        logger.info("✓ All migrations completed successfully")

    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    run_migrations()

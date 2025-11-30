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

            # Add more migrations here as needed

        engine.dispose()
        logger.info("✓ All migrations completed successfully")

    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    run_migrations()

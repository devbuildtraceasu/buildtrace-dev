#!/usr/bin/env python3
"""
Database Migration Runner
Manually adds session_id column to analysis_results table
"""

import os
import sys
from sqlalchemy import create_engine, text
import logging

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    """Run the session_id migration"""

    # Production database connection
    db_user = "buildtrace_user"
    db_pass = "BuildTrace2024SecurePassword"
    db_name = "buildtrace_db"
    instance_connection_name = "buildtrace:us-central1:buildtrace-postgres"

    # Cloud SQL Unix socket connection (same as production)
    database_url = f"postgresql://{db_user}:{db_pass}@/{db_name}?host=/cloudsql/{instance_connection_name}"

    try:
        engine = create_engine(database_url, pool_pre_ping=True)
        logger.info("Connected to Cloud SQL database")

        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()

            try:
                # Check if column exists
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM information_schema.columns
                    WHERE table_name = 'analysis_results'
                    AND column_name = 'session_id'
                """))
                column_exists = result.fetchone()[0] > 0

                if column_exists:
                    logger.info("✅ session_id column already exists")
                    return True

                logger.info("Adding session_id column to analysis_results table...")

                # Add the column
                conn.execute(text("""
                    ALTER TABLE analysis_results
                    ADD COLUMN session_id VARCHAR(36)
                """))
                logger.info("✅ Added session_id column")

                # Update existing records
                result = conn.execute(text("""
                    UPDATE analysis_results
                    SET session_id = c.session_id
                    FROM comparisons c
                    WHERE analysis_results.comparison_id = c.id
                """))
                logger.info(f"✅ Updated {result.rowcount} existing records")

                # Add foreign key constraint
                conn.execute(text("""
                    ALTER TABLE analysis_results
                    ADD CONSTRAINT fk_analysis_results_session_id
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                """))
                logger.info("✅ Added foreign key constraint")

                # Make column NOT NULL
                conn.execute(text("""
                    ALTER TABLE analysis_results
                    ALTER COLUMN session_id SET NOT NULL
                """))
                logger.info("✅ Set session_id as NOT NULL")

                # Commit transaction
                trans.commit()
                logger.info("🎉 Migration completed successfully!")
                return True

            except Exception as e:
                trans.rollback()
                logger.error(f"❌ Migration failed: {str(e)}")
                return False

    except Exception as e:
        logger.error(f"❌ Database connection failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
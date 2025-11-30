#!/usr/bin/env python3
"""
Database Migration with Cloud SQL Python Connector
Adds session_id column to analysis_results table
"""

import os
import sys
from google.cloud.sql.connector import Connector
import sqlalchemy
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    """Run the session_id migration using Cloud SQL Connector"""

    # Cloud SQL connection details
    project_id = "buildtrace"
    region = "us-central1"
    instance_name = "buildtrace-postgres"
    db_user = "buildtrace_user"
    db_pass = "BuildTrace2024SecurePassword"
    db_name = "buildtrace_db"

    instance_connection_name = f"{project_id}:{region}:{instance_name}"

    try:
        # Initialize Cloud SQL Connector
        connector = Connector()

        # Create connection function
        def getconn():
            conn = connector.connect(
                instance_connection_name,
                "pg8000",
                user=db_user,
                password=db_pass,
                db=db_name
            )
            return conn

        # Create SQLAlchemy engine
        engine = sqlalchemy.create_engine(
            "postgresql+pg8000://",
            creator=getconn,
        )

        logger.info("✅ Connected to Cloud SQL via Cloud SQL Connector")

        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()

            try:
                # Check if column exists
                result = conn.execute(sqlalchemy.text("""
                    SELECT COUNT(*) FROM information_schema.columns
                    WHERE table_name = 'analysis_results'
                    AND column_name = 'session_id'
                """))
                column_exists = result.fetchone()[0] > 0

                if column_exists:
                    logger.info("✅ session_id column already exists")
                    trans.rollback()
                    return True

                logger.info("🔧 Adding session_id column to analysis_results table...")

                # Add the column
                conn.execute(sqlalchemy.text("""
                    ALTER TABLE analysis_results
                    ADD COLUMN session_id VARCHAR(36)
                """))
                logger.info("✅ Added session_id column")

                # Update existing records
                result = conn.execute(sqlalchemy.text("""
                    UPDATE analysis_results
                    SET session_id = c.session_id
                    FROM comparisons c
                    WHERE analysis_results.comparison_id = c.id
                """))
                logger.info(f"✅ Updated {result.rowcount} existing records")

                # Add foreign key constraint
                conn.execute(sqlalchemy.text("""
                    ALTER TABLE analysis_results
                    ADD CONSTRAINT fk_analysis_results_session_id
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                """))
                logger.info("✅ Added foreign key constraint")

                # Make column NOT NULL
                conn.execute(sqlalchemy.text("""
                    ALTER TABLE analysis_results
                    ALTER COLUMN session_id SET NOT NULL
                """))
                logger.info("✅ Set session_id as NOT NULL")

                # Commit transaction
                trans.commit()
                logger.info("🎉 Migration completed successfully!")

                # Verify the migration
                result = conn.execute(sqlalchemy.text("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = 'analysis_results'
                    ORDER BY ordinal_position
                """))

                logger.info("📋 Current analysis_results table structure:")
                for row in result:
                    nullable = "NULL" if row[2] == 'YES' else "NOT NULL"
                    logger.info(f"  {row[0]:<20} {row[1]:<15} {nullable}")

                return True

            except Exception as e:
                trans.rollback()
                logger.error(f"❌ Migration failed: {str(e)}")
                return False

        # Close the connector
        connector.close()

    except Exception as e:
        logger.error(f"❌ Database connection failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
#!/usr/bin/env python3
"""
Migration script to add stage_metadata column to job_stages table
This fixes the schema mismatch causing 500 errors when querying job stages
"""

import os
import sys
from sqlalchemy import create_engine, text
from config import config

def add_stage_metadata_column():
    """Add stage_metadata column to job_stages table"""

    # Build database URL
    if config.USE_DATABASE:
        db_url = f"postgresql://{config.DB_USER}:{config.DB_PASS}@/{config.DB_NAME}?host=/cloudsql/{config.INSTANCE_CONNECTION_NAME}"
    else:
        print("Database not configured")
        sys.exit(1)

    print(f"Connecting to database: {config.DB_NAME}")
    print(f"Instance: {config.INSTANCE_CONNECTION_NAME}")

    engine = create_engine(db_url)

    try:
        with engine.connect() as conn:
            # Check if column already exists
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='job_stages'
                AND column_name='stage_metadata'
            """))

            if result.fetchone():
                print("✓ Column 'stage_metadata' already exists")
                return

            # Add the column
            print("Adding stage_metadata column to job_stages table...")
            conn.execute(text("""
                ALTER TABLE job_stages
                ADD COLUMN stage_metadata JSONB
            """))
            conn.commit()

            print("✓ Successfully added stage_metadata column")

    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)
    finally:
        engine.dispose()

if __name__ == "__main__":
    add_stage_metadata_column()

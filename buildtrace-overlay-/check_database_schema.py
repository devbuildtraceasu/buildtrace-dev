#!/usr/bin/env python3
"""
Check Database Schema Script
Connects to the Cloud SQL database and shows the current table structure
"""

import os
import sys
from sqlalchemy import create_engine, text, inspect
import logging

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_database_schema():
    """Check the current database schema"""

    if not config.USE_DATABASE:
        logger.error("Database is not enabled. Set USE_DATABASE=true in your environment.")
        return False

    try:
        # Create engine using the same config as the app
        engine = create_engine(
            config.DATABASE_URL,
            pool_pre_ping=True
        )

        logger.info(f"Connecting to database: {config.DATABASE_URL}")

        # Get inspector
        inspector = inspect(engine)

        # List all tables
        tables = inspector.get_table_names()
        logger.info(f"📋 Found {len(tables)} tables:")
        for table in sorted(tables):
            logger.info(f"  ✓ {table}")

        # Check specific tables we care about
        tables_to_check = ['sessions', 'drawings', 'comparisons', 'analysis_results']

        for table_name in tables_to_check:
            if table_name in tables:
                logger.info(f"\n🔍 {table_name.upper()} TABLE STRUCTURE:")
                columns = inspector.get_columns(table_name)
                for col in columns:
                    nullable = "NULL" if col['nullable'] else "NOT NULL"
                    logger.info(f"  {col['name']:<20} {str(col['type']):<20} {nullable}")
            else:
                logger.warning(f"❌ Table '{table_name}' does not exist")

        # Check if session_id exists in analysis_results
        if 'analysis_results' in tables:
            columns = inspector.get_columns('analysis_results')
            column_names = [col['name'] for col in columns]

            if 'session_id' in column_names:
                logger.info("✅ analysis_results.session_id column EXISTS")
            else:
                logger.warning("❌ analysis_results.session_id column MISSING")
                logger.info("📝 Available columns:", column_names)

        return True

    except Exception as e:
        logger.error(f"❌ Database check failed: {str(e)}")
        return False

if __name__ == "__main__":
    # Set environment for production database
    os.environ['ENVIRONMENT'] = 'production'
    os.environ['USE_DATABASE'] = 'true'

    success = check_database_schema()
    sys.exit(0 if success else 1)
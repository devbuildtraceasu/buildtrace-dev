#!/usr/bin/env python3
"""
Database Migration Script
Updates the GCP Cloud SQL database schema with new tables and columns
"""

import os
import sys
from sqlalchemy import create_engine, text
import logging

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import config
from gcp.database.models import Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_database():
    """Run database migration to update schema"""

    # Check if we're using database
    if not config.USE_DATABASE:
        logger.error("Database is not enabled. Set USE_DATABASE=true in your environment.")
        return False

    try:
        # Create engine using the same config as the app
        engine = create_engine(
            config.DATABASE_URL,
            pool_pre_ping=True,
            echo=True  # Show SQL commands
        )

        logger.info(f"Connecting to database: {config.DATABASE_URL}")

        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            logger.info(f"Connected to PostgreSQL: {version}")

        # Create/update all tables
        logger.info("Creating/updating database tables...")
        Base.metadata.create_all(bind=engine)

        # Verify tables were created
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result.fetchall()]

            logger.info("Database tables:")
            for table in tables:
                logger.info(f"  ✓ {table}")

        logger.info("✅ Database migration completed successfully!")
        return True

    except Exception as e:
        logger.error(f"❌ Database migration failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = migrate_database()
    sys.exit(0 if success else 1)
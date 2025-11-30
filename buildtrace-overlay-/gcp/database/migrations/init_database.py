#!/usr/bin/env python3
"""Initialize database schema and create tables"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables before importing database
from dotenv import load_dotenv
load_dotenv()

from gcp.database import db_manager
from gcp.database.models import Base
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_database():
    """Initialize database with all tables"""
    try:
        logger.info("Starting database initialization...")

        # Create all tables
        Base.metadata.create_all(bind=db_manager.engine)
        logger.info("All tables created successfully")

        # Test connection
        from sqlalchemy import text
        with db_manager.get_session() as session:
            result = session.execute(text("SELECT 1"))
            logger.info("Database connection test successful")

        return True

    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        return False

def drop_all_tables():
    """Drop all tables (USE WITH CAUTION!)"""
    try:
        response = input("Are you sure you want to drop all tables? This cannot be undone! (yes/no): ")
        if response.lower() != 'yes':
            logger.info("Operation cancelled")
            return False

        logger.info("Dropping all tables...")
        Base.metadata.drop_all(bind=db_manager.engine)
        logger.info("All tables dropped successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to drop tables: {str(e)}")
        return False

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Database initialization script')
    parser.add_argument('--drop', action='store_true', help='Drop all tables before creating')
    parser.add_argument('--reset', action='store_true', help='Drop and recreate all tables')
    args = parser.parse_args()

    if args.drop:
        drop_all_tables()
    elif args.reset:
        if drop_all_tables():
            init_database()
    else:
        init_database()
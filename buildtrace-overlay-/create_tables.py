#!/usr/bin/env python3
"""
Database table creation script for BuildTrace
Creates all tables defined in models.py
"""

import os
import sys
from gcp.database.models import Base
from gcp.database.database import db_manager

def create_tables():
    """Create all database tables"""
    print("Creating database tables...")

    try:
        # Initialize database manager
        db_manager.initialize()

        # Create all tables
        db_manager.create_tables()

        print("✅ Database tables created successfully!")

        # List created tables
        with db_manager.get_session() as session:
            from sqlalchemy import text
            result = session.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
            tables = [row[0] for row in result]

            print(f"\n📋 Created tables ({len(tables)}):")
            for table in sorted(tables):
                print(f"  - {table}")

    except Exception as e:
        print(f"❌ Error creating tables: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    # Set environment variables for Cloud SQL proxy connection
    os.environ['ENVIRONMENT'] = 'development'
    os.environ['USE_DATABASE'] = 'true'
    os.environ['USE_CLOUD_SQL_AUTH_PROXY'] = 'true'
    os.environ['DB_USER'] = 'buildtrace_user'
    os.environ['DB_NAME'] = 'buildtrace_db'
    os.environ['DB_PASS'] = 'BuildTrace2024SecurePassword'
    os.environ['DB_HOST'] = '127.0.0.1'
    os.environ['DB_PORT'] = '5432'

    create_tables()
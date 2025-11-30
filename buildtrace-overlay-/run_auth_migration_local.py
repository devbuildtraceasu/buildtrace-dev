#!/usr/bin/env python3
"""
Database migration script to add authentication columns and tables
This version uses Cloud SQL Python Connector for local execution
"""

import os
import sys
from google.cloud.sql.connector import Connector
import sqlalchemy
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    """Run the authentication migration using Cloud SQL Connector"""

    # Cloud SQL connection details
    project_id = "buildtrace"
    region = "us-central1"
    instance_name = "buildtrace-postgres"
    instance_connection_name = f"{project_id}:{region}:{instance_name}"

    db_user = "buildtrace_user"
    db_name = "buildtrace_db"
    db_pass = os.getenv('DB_PASS', '')

    print("🔄 Running authentication migration...")
    print(f"Instance: {instance_connection_name}")
    print(f"Database: {db_name}")
    print(f"User: {db_user}")

    # Initialize Connector object
    connector = Connector()

    try:
        # Create connection to Cloud SQL
        def getconn():
            conn = connector.connect(
                instance_connection_name,
                "pg8000",
                user=db_user,
                password=db_pass,
                db=db_name,
            )
            return conn

        # Create SQLAlchemy engine
        engine = sqlalchemy.create_engine(
            "postgresql+pg8000://",
            creator=getconn,
        )

        print("✅ Connected to Cloud SQL via Cloud SQL Connector")

        # Migration SQL statements
        migration_statements = [
            # Add authentication columns to users table
            """ALTER TABLE users
            ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255),
            ADD COLUMN IF NOT EXISTS last_login TIMESTAMP,
            ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE""",

            # Create project_users junction table
            """CREATE TABLE IF NOT EXISTS project_users (
                id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
                project_id VARCHAR(36) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                role VARCHAR(50) DEFAULT 'member',
                invited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                joined_at TIMESTAMP,
                invited_by VARCHAR(36) REFERENCES users(id),
                CONSTRAINT unique_project_user UNIQUE (project_id, user_id)
            )""",

            # Create indexes
            "CREATE INDEX IF NOT EXISTS idx_project_users_project_id ON project_users(project_id)",
            "CREATE INDEX IF NOT EXISTS idx_project_users_user_id ON project_users(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_project_users_role ON project_users(role)",

            # Migrate existing data
            """INSERT INTO project_users (project_id, user_id, role, joined_at, invited_by)
            SELECT p.id, p.user_id, 'owner', p.created_at, p.user_id
            FROM projects p
            WHERE p.user_id IS NOT NULL
            ON CONFLICT (project_id, user_id) DO NOTHING""",

            # Add session columns
            """ALTER TABLE sessions
            ADD COLUMN IF NOT EXISTS user_id VARCHAR(36) REFERENCES users(id),
            ADD COLUMN IF NOT EXISTS project_id VARCHAR(36) REFERENCES projects(id)""",

            # Create session indexes
            "CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_sessions_project_id ON sessions(project_id)"
        ]

        # Execute migration statements
        with engine.connect() as conn:
            for i, statement in enumerate(migration_statements, 1):
                print(f"Executing statement {i}/{len(migration_statements)}: {statement[:60]}...")
                try:
                    conn.execute(text(statement))
                    conn.commit()
                    print(f"✅ Statement {i} completed")
                except Exception as e:
                    if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                        print(f"⚠️ Statement {i}: {e} (skipping)")
                    else:
                        print(f"❌ Statement {i} failed: {e}")
                        raise

        print("\n🎉 Authentication migration completed successfully!")
        print("📋 Migration summary:")
        print("   ✅ Added authentication columns to users table")
        print("   ✅ Created project_users junction table")
        print("   ✅ Added indexes for performance")
        print("   ✅ Migrated existing project ownership data")
        print("   ✅ Added session user/project columns")

    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        sys.exit(1)
    finally:
        # Close the connector
        connector.close()

if __name__ == "__main__":
    print("🔄 Running authentication migration with Cloud SQL Connector...")
    run_migration()
#!/usr/bin/env python3
"""
Database migration script to add authentication columns and tables
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

def run_migration():
    """Run the authentication migration"""

    # Load environment variables
    load_dotenv()

    # Force production mode and database usage for migration
    os.environ['ENVIRONMENT'] = 'production'
    os.environ['USE_DATABASE'] = 'true'

    # Import after setting environment
    from config import Config
    prod_config = Config()

    # Force Cloud SQL connection
    if prod_config.INSTANCE_CONNECTION_NAME:
        database_url = f"postgresql://{prod_config.DB_USER}:{prod_config.DB_PASS}@/{prod_config.DB_NAME}?host=/cloudsql/{prod_config.INSTANCE_CONNECTION_NAME}"
    else:
        database_url = prod_config.DATABASE_URL

    print(f"Environment: {prod_config.ENVIRONMENT}")
    print(f"USE_DATABASE: {prod_config.USE_DATABASE}")

    # Connect to database
    if not prod_config.USE_DATABASE:
        print("ERROR: Database is not enabled in production configuration")
        sys.exit(1)

    print(f"Connecting to database: {database_url[:50]}...")

    try:
        engine = create_engine(database_url)

        # Read the migration SQL
        migration_sql = """
-- Migration: Add authentication columns to users table and create project_users table

-- Add authentication columns to users table
ALTER TABLE users
ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255),
ADD COLUMN IF NOT EXISTS last_login TIMESTAMP,
ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE;

-- Create project_users junction table if it doesn't exist
CREATE TABLE IF NOT EXISTS project_users (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    project_id VARCHAR(36) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) DEFAULT 'member',
    invited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    joined_at TIMESTAMP,
    invited_by VARCHAR(36) REFERENCES users(id),
    CONSTRAINT unique_project_user UNIQUE (project_id, user_id)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_project_users_project_id ON project_users(project_id);
CREATE INDEX IF NOT EXISTS idx_project_users_user_id ON project_users(user_id);
CREATE INDEX IF NOT EXISTS idx_project_users_role ON project_users(role);

-- Migrate existing data: add all existing users as owners of all their projects
INSERT INTO project_users (project_id, user_id, role, joined_at, invited_by)
SELECT p.id, p.user_id, 'owner', p.created_at, p.user_id
FROM projects p
WHERE p.user_id IS NOT NULL
ON CONFLICT (project_id, user_id) DO NOTHING;

-- Add session user_id and project_id columns if they don't exist
ALTER TABLE sessions
ADD COLUMN IF NOT EXISTS user_id VARCHAR(36) REFERENCES users(id),
ADD COLUMN IF NOT EXISTS project_id VARCHAR(36) REFERENCES projects(id);

-- Create indexes for sessions
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_project_id ON sessions(project_id);
"""

        with engine.connect() as conn:
            print("Starting migration...")

            # Execute each statement
            statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip()]

            for i, statement in enumerate(statements, 1):
                if statement.startswith('--') or not statement:
                    continue

                print(f"Executing statement {i}/{len(statements)}: {statement[:80]}...")
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

            print("\n🎉 Migration completed successfully!")

    except SQLAlchemyError as e:
        print(f"❌ Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("🔄 Running authentication migration...")
    run_migration()
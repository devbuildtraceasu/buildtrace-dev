#!/usr/bin/env python3
"""
Add a migration endpoint to the Flask app that can be called to run the database migration
"""

from app import app
from gcp.database import get_db_session
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

@app.route('/admin/migrate-auth', methods=['POST'])
def migrate_auth():
    """Run authentication migration - admin endpoint"""

    try:
        with get_db_session() as db:
            logger.info("Starting authentication migration...")

            # Migration statements
            statements = [
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255)",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login TIMESTAMP",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE",

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

                "CREATE INDEX IF NOT EXISTS idx_project_users_project_id ON project_users(project_id)",
                "CREATE INDEX IF NOT EXISTS idx_project_users_user_id ON project_users(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_project_users_role ON project_users(role)",

                """INSERT INTO project_users (project_id, user_id, role, joined_at, invited_by)
                SELECT p.id, p.user_id, 'owner', p.created_at, p.user_id
                FROM projects p
                WHERE p.user_id IS NOT NULL
                ON CONFLICT (project_id, user_id) DO NOTHING""",

                "ALTER TABLE sessions ADD COLUMN IF NOT EXISTS user_id VARCHAR(36) REFERENCES users(id)",
                "ALTER TABLE sessions ADD COLUMN IF NOT EXISTS project_id VARCHAR(36) REFERENCES projects(id)",

                "CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_sessions_project_id ON sessions(project_id)"
            ]

            results = []

            for i, statement in enumerate(statements, 1):
                logger.info(f"Executing statement {i}/{len(statements)}: {statement[:80]}...")
                try:
                    db.execute(text(statement))
                    db.commit()
                    results.append(f"✅ Statement {i} completed")
                    logger.info(f"✅ Statement {i} completed")
                except Exception as e:
                    if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                        results.append(f"⚠️ Statement {i}: {e} (skipping)")
                        logger.warning(f"⚠️ Statement {i}: {e} (skipping)")
                    else:
                        results.append(f"❌ Statement {i} failed: {e}")
                        logger.error(f"❌ Statement {i} failed: {e}")
                        # Continue with other statements rather than failing completely

            return {
                "status": "success",
                "message": "Migration completed",
                "results": results
            }

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return {
            "status": "error",
            "message": f"Migration failed: {e}"
        }, 500

if __name__ == "__main__":
    print("Migration endpoint added to Flask app")
    print("Deploy the app and call POST /admin/migrate-auth to run migration")
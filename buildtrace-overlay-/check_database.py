#!/usr/bin/env python3

import os
import sys
from sqlalchemy import create_engine, text
from config import Config

def check_database():
    """Check database contents using the same configuration as the app"""

    # Set environment variable to enable database
    os.environ['USE_DATABASE'] = 'true'

    # Load configuration
    config = Config()

    if not config.DATABASE_URL:
        print("ERROR: DATABASE_URL is None - database not configured")
        return False

    print(f"Database URL: {config.DATABASE_URL[:50]}...")

    # Create engine
    engine = create_engine(config.DATABASE_URL)

    try:
        with engine.connect() as conn:
            # First check what tables and columns exist
            print("\nChecking database schema...")

            # Check tables
            result = conn.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result.fetchall()]
            print(f"Tables found: {tables}")

            # Check sessions table columns
            if 'sessions' in tables:
                result = conn.execute(text("""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_name = 'sessions'
                    ORDER BY ordinal_position
                """))
                columns = result.fetchall()
                print(f"\nSessions table columns:")
                for col_name, col_type in columns:
                    print(f"  {col_name}: {col_type}")

                # Try to query the sessions table with correct column names
                if columns:
                    first_col = columns[0][0]  # Use first column as ID
                    result = conn.execute(text(f"SELECT * FROM sessions LIMIT 5"))
                    rows = result.fetchall()
                    print(f"\nFirst 5 sessions:")
                    for row in rows:
                        print(f"  {row}")

                    result = conn.execute(text("SELECT COUNT(*) FROM sessions"))
                    total_count = result.fetchone()[0]
                    print(f"\nTotal sessions in database: {total_count}")
            else:
                print("Sessions table not found!")

            # Check if any Cloud Storage session IDs exist in database
            cloud_sessions = [
                'f263d60c-175f-43c2-a17a-c5b50d4b3cc6',
                'ef16ef3c-ab4d-45ef-b96a-c6fcd302aea4'
            ]

            print(f"\nChecking if Cloud Storage sessions exist in database:")
            for session_id in cloud_sessions:
                result = conn.execute(text("""
                    SELECT id, status, created_at
                    FROM sessions
                    WHERE id = :session_id
                """), {"session_id": session_id})

                row = result.fetchone()
                if row:
                    print(f"  ✅ Found: {row[0]} | {row[1]} | {row[2]}")
                else:
                    print(f"  ❌ NOT in DB: {session_id}")

            print("\nDatabase schema check complete.")

    except Exception as e:
        print(f"Database error: {e}")
        return False

    return True

if __name__ == "__main__":
    check_database()
#!/usr/bin/env python3
"""
Script to fix stuck processing sessions by marking them as failed
and adding timeout detection for future sessions.
"""

import os
import sys
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

def main():
    # Load environment variables
    load_dotenv('.env')

    # Database connection
    use_proxy = os.getenv('USE_CLOUD_SQL_AUTH_PROXY', 'false').lower() == 'true'
    db_user = os.getenv('DB_USER', 'buildtrace_user')
    db_pass = os.getenv('DB_PASS')
    db_name = os.getenv('DB_NAME', 'buildtrace_db')

    url = f'postgresql://{db_user}:{db_pass}@127.0.0.1:5432/{db_name}'

    # Known stuck session IDs
    stuck_sessions = [
        '6d5c615b-4b24-4c22-aa99-6d78f2bebe51',
        'c0aa7b52-dc6f-4bf5-9edf-4edbb9a719c8',
        'e5829648-419c-488a-a1cc-0d37ca62a6e8',
        '9d8a10db-18a4-4be9-a433-2f537b8038a9'
    ]

    try:
        print("Connecting to database...")
        engine = create_engine(url, pool_pre_ping=True)

        with engine.connect() as conn:
            print("Connected successfully!")

            # Get current time
            now = datetime.utcnow()

            for session_id in stuck_sessions:
                print(f"\n=== Processing session: {session_id} ===")

                # Check current status
                result = conn.execute(
                    text("SELECT status, created_at, updated_at FROM sessions WHERE id = :session_id"),
                    {'session_id': session_id}
                )
                session_data = result.fetchone()

                if not session_data:
                    print(f"Session {session_id} not found")
                    continue

                status, created_at, updated_at = session_data
                print(f"Current status: {status}")
                print(f"Created: {created_at}")
                print(f"Last updated: {updated_at}")

                # Calculate how long it's been stuck
                time_diff = now - created_at.replace(tzinfo=None)
                hours_stuck = time_diff.total_seconds() / 3600
                print(f"Hours stuck: {hours_stuck:.1f}")

                if status == 'processing' and hours_stuck > 1:  # Stuck for more than 1 hour
                    # Mark as failed
                    conn.execute(
                        text("UPDATE sessions SET status = 'error', updated_at = :now WHERE id = :session_id"),
                        {'session_id': session_id, 'now': now}
                    )
                    print(f"✅ Marked session as 'error' (was stuck for {hours_stuck:.1f} hours)")

                    # Check if any partial results exist
                    drawing_count = conn.execute(
                        text("SELECT COUNT(*) FROM drawings WHERE session_id = :session_id"),
                        {'session_id': session_id}
                    ).scalar()

                    comparison_count = conn.execute(
                        text("SELECT COUNT(*) FROM comparisons WHERE session_id = :session_id"),
                        {'session_id': session_id}
                    ).scalar()

                    analysis_count = conn.execute(
                        text("SELECT COUNT(*) FROM analysis_results WHERE session_id = :session_id"),
                        {'session_id': session_id}
                    ).scalar()

                    print(f"  Partial results: {drawing_count} drawings, {comparison_count} comparisons, {analysis_count} analyses")

                elif status != 'processing':
                    print(f"Session status is '{status}' - no action needed")
                else:
                    print(f"Session stuck for {hours_stuck:.1f} hours but < 1 hour threshold")

            # Commit changes
            conn.commit()
            print(f"\n✅ All changes committed!")

            # Show updated session list
            print(f"\n=== Updated session statuses ===")
            result = conn.execute(
                text("SELECT id, status, created_at FROM sessions ORDER BY created_at DESC LIMIT 10")
            )
            for row in result:
                session_id, status, created_at = row
                time_diff = now - created_at.replace(tzinfo=None)
                hours_ago = time_diff.total_seconds() / 3600
                print(f"{session_id[:8]}... | {status:12} | {hours_ago:5.1f}h ago")

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())
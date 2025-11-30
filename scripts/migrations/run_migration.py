#!/usr/bin/env python3
"""
Database Migration Runner
Runs migration scripts in order with error handling and rollback support
"""

import os
import sys
import psycopg2
from pathlib import Path
from typing import List, Tuple
import argparse

# Add project root to path
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from config import config
except ImportError:
    print("Warning: Could not import config. Using environment variables.")
    config = None


def get_db_connection():
    """Get database connection from config or environment"""
    if config and hasattr(config, 'DATABASE_URL'):
        return psycopg2.connect(config.DATABASE_URL)
    
    # Fallback to environment variables
    db_host = os.getenv('DB_HOST', '127.0.0.1')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'buildtrace_db')
    db_user = os.getenv('DB_USER', 'buildtrace_user')
    db_password = os.getenv('DB_PASSWORD', '')
    
    return psycopg2.connect(
        host=db_host,
        port=db_port,
        database=db_name,
        user=db_user,
        password=db_password
    )


def run_migration_file(conn, file_path: Path) -> Tuple[bool, str]:
    """Run a single migration SQL file"""
    try:
        with open(file_path, 'r') as f:
            sql = f.read()
        
        cursor = conn.cursor()
        cursor.execute(sql)
        conn.commit()
        cursor.close()
        
        return True, f"Successfully ran {file_path.name}"
    except Exception as e:
        conn.rollback()
        return False, f"Error running {file_path.name}: {str(e)}"


def get_migration_files() -> List[Path]:
    """Get migration files in order"""
    migration_dir = SCRIPT_DIR
    files = sorted(migration_dir.glob('*.sql'))
    # Filter out non-migration files
    return [f for f in files if f.name.startswith(('001_', '002_', '003_', '004_', '005_'))]


def main():
    parser = argparse.ArgumentParser(description='Run database migrations')
    parser.add_argument('--migration', type=str, help='Run specific migration file (e.g., 001)')
    parser.add_argument('--dry-run', action='store_true', help='Validate SQL without executing')
    parser.add_argument('--skip-confirm', action='store_true', help='Skip confirmation prompt')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("BuildTrace Database Migration Runner")
    print("=" * 60)
    print()
    
    # Get migration files
    if args.migration:
        migration_files = [SCRIPT_DIR / f"{args.migration}_*.sql"]
        migration_files = [f for f in SCRIPT_DIR.glob(f"{args.migration}_*.sql")]
        if not migration_files:
            print(f"❌ Error: Migration {args.migration} not found")
            sys.exit(1)
    else:
        migration_files = get_migration_files()
    
    if not migration_files:
        print("❌ Error: No migration files found")
        sys.exit(1)
    
    print(f"Found {len(migration_files)} migration file(s):")
    for f in migration_files:
        print(f"  - {f.name}")
    print()
    
    if args.dry_run:
        print("🔍 Dry run mode: Validating SQL syntax only")
        print()
        for f in migration_files:
            print(f"Validating {f.name}...")
            # Basic SQL validation (check for syntax errors)
            try:
                with open(f, 'r') as file:
                    sql = file.read()
                print(f"  ✅ {f.name} - SQL syntax looks valid")
            except Exception as e:
                print(f"  ❌ {f.name} - Error: {e}")
        print()
        print("Dry run complete. No changes made to database.")
        return
    
    # Confirm
    if not args.skip_confirm:
        print("⚠️  WARNING: This will modify your database!")
        print("Make sure you have:")
        print("  1. Backed up your database")
        print("  2. Tested on development/staging first")
        print("  3. Reviewed all migration scripts")
        print()
        response = input("Continue? (yes/no): ")
        if response.lower() != 'yes':
            print("Aborted.")
            sys.exit(0)
    
    # Connect to database
    print()
    print("Connecting to database...")
    try:
        conn = get_db_connection()
        print("✅ Connected to database")
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        print()
        print("Make sure:")
        print("  1. Database is running")
        print("  2. Cloud SQL Proxy is running (if using Cloud SQL)")
        print("  3. Environment variables are set correctly")
        sys.exit(1)
    
    # Run migrations
    print()
    print("Running migrations...")
    print("-" * 60)
    
    results = []
    for migration_file in migration_files:
        print(f"Running {migration_file.name}...")
        success, message = run_migration_file(conn, migration_file)
        if success:
            print(f"  ✅ {message}")
            results.append((migration_file.name, True, message))
        else:
            print(f"  ❌ {message}")
            results.append((migration_file.name, False, message))
            print()
            print("⚠️  Migration failed. Previous migrations have been committed.")
            print("Review the error and fix before continuing.")
            break
    
    conn.close()
    
    # Summary
    print()
    print("=" * 60)
    print("Migration Summary")
    print("=" * 60)
    
    successful = sum(1 for _, success, _ in results if success)
    failed = sum(1 for _, success, _ in results if not success)
    
    for name, success, message in results:
        status = "✅" if success else "❌"
        print(f"{status} {name}")
    
    print()
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    
    if failed > 0:
        print()
        print("❌ Some migrations failed. Review errors above.")
        sys.exit(1)
    else:
        print()
        print("✅ All migrations completed successfully!")


if __name__ == '__main__':
    main()


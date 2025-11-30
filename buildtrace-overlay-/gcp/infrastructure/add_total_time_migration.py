#!/usr/bin/env python3

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load environment variables
load_dotenv()

def add_total_time_column():
    """Add total_time column to sessions table"""
    # Database configuration
    DB_USER = os.getenv('DB_USER', 'buildtrace_user')
    DB_PASS = os.getenv('DB_PASS')
    DB_NAME = os.getenv('DB_NAME', 'buildtrace_db')
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '5432')

    # Create connection string
    connection_string = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

    try:
        # Create engine
        engine = create_engine(connection_string)

        # Check if column already exists
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'sessions' AND column_name = 'total_time'
            """))

            if result.fetchone():
                print("✅ total_time column already exists in sessions table")
                return

            # Add the column
            print("Adding total_time column to sessions table...")
            conn.execute(text("ALTER TABLE sessions ADD COLUMN total_time FLOAT"))
            conn.commit()
            print("✅ Successfully added total_time column to sessions table")

    except Exception as e:
        print(f"❌ Error adding total_time column: {e}")
        raise

if __name__ == "__main__":
    add_total_time_column()
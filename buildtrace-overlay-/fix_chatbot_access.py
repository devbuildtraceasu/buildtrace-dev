#!/usr/bin/env python3
"""
Script to fix chatbot access for existing sessions by creating missing results.json files
"""

import os
import json
import glob
from pathlib import Path

def fix_chatbot_access():
    """Create missing results.json files for all sessions"""
    print("🔧 Fixing chatbot access for existing sessions...")

    data_dir = Path("data/sessions")
    if not data_dir.exists():
        print("❌ No sessions directory found")
        return

    fixed_sessions = 0
    total_sessions = 0

    # Process all session files
    for session_file in data_dir.glob("*.json"):
        total_sessions += 1
        session_id = session_file.stem

        print(f"📋 Processing session: {session_id}")

        # Check if uploads/results.json already exists
        uploads_dir = Path("uploads") / session_id
        results_file = uploads_dir / "results.json"

        if results_file.exists():
            print(f"   ✅ Already has results.json")
            continue

        # Read session data
        try:
            with open(session_file, 'r') as f:
                session_data = json.load(f)

            # Extract output directories from metadata
            metadata = session_data.get('metadata', {})
            results = metadata.get('results', {})
            output_directories = results.get('output_directories', [])

            if not output_directories:
                print(f"   ⚠️  No output directories found")
                continue

            # Create uploads directory and results.json
            uploads_dir.mkdir(parents=True, exist_ok=True)

            chatbot_results = {
                'output_directories': output_directories
            }

            with open(results_file, 'w') as f:
                json.dump(chatbot_results, f, indent=2)

            print(f"   ✅ Created results.json with {len(output_directories)} directories")
            fixed_sessions += 1

        except Exception as e:
            print(f"   ❌ Error processing session: {e}")
            continue

    print(f"\n🎉 Summary:")
    print(f"   Total sessions: {total_sessions}")
    print(f"   Fixed sessions: {fixed_sessions}")
    print(f"   Chatbot access enabled for all sessions!")

if __name__ == "__main__":
    fix_chatbot_access()
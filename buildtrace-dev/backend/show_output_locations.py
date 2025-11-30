#!/usr/bin/env python3
"""
Show where all outputs are saved in local dev mode
"""

import os
from pathlib import Path
from config import config
from utils.local_output_manager import LocalOutputManager

print("=" * 80)
print("OUTPUT LOCATIONS IN LOCAL DEV MODE")
print("=" * 80)
print()

# Show config paths
print("📁 CONFIGURATION PATHS:")
local_output = getattr(config, 'LOCAL_OUTPUT_PATH', 'outputs')
local_upload = getattr(config, 'LOCAL_UPLOAD_PATH', 'uploads')
local_results = getattr(config, 'LOCAL_RESULTS_PATH', 'results')
local_temp = getattr(config, 'LOCAL_TEMP_PATH', 'temp')
print(f"  LOCAL_OUTPUT_PATH: {local_output}")
print(f"  LOCAL_UPLOAD_PATH: {local_upload}")
print(f"  LOCAL_RESULTS_PATH: {local_results}")
print(f"  LOCAL_TEMP_PATH: {local_temp}")
print()

# Show absolute paths
base_dir = Path.cwd()
print("📂 ABSOLUTE PATHS (from backend directory):")
print(f"  Outputs:     {base_dir / local_output}")
print(f"  Uploads:     {base_dir / local_upload}")
print(f"  Results:     {base_dir / local_results}")
print(f"  Temp:        {base_dir / local_temp}")
print()

# Initialize output manager and show structure
print("📋 LOCAL OUTPUT MANAGER STRUCTURE:")
output_manager = LocalOutputManager()
print(f"  Base Path: {output_manager.base_path}")
print()

# Show directory structure
print("🗂️  OUTPUT MANAGER DIRECTORY STRUCTURE:")
for subdir in ['sessions', 'jobs', 'logs', 'temp']:
    dir_path = output_manager.base_path / subdir
    print(f"  {subdir}/")
    if dir_path.exists():
        print(f"    ✓ Exists: {dir_path}")
    else:
        print(f"    ✗ Not created yet (will be created on first use)")
print()

# Show what gets saved where
print("💾 WHAT GETS SAVED WHERE:")
print()
print("  Drawing Comparison Outputs:")
print("    - Overlay images: {base}/sessions/{session_id}/overlays/")
print("    - PNG files:      {base}/sessions/{session_id}/pngs/")
print()
print("  Change Analysis Outputs:")
print("    - Analysis JSON:  {base}/sessions/{session_id}/json/")
print("    - Summary JSON:   {base}/sessions/{session_id}/json/")
print()
print("  OCR Pipeline Outputs:")
print("    - OCR results:    {base}/sessions/{session_id}/ocr_results/")
print()
print("  Diff Pipeline Outputs:")
print("    - Diff results:   {base}/sessions/{session_id}/diff_results/")
print()
print("  Summary Pipeline Outputs:")
print("    - Summaries:      {base}/sessions/{session_id}/summaries/")
print()
print("  Processing Logs:")
print("    - Log files:      {base}/sessions/{session_id}/logs/")
print()

# Show example session structure
print("📊 EXAMPLE SESSION STRUCTURE:")
example_session = "example-session-123"
session_path = output_manager.get_session_path(example_session)
print(f"  Session ID: {example_session}")
print(f"  Path: {session_path}")
print()
print("  Directory structure:")
print("    sessions/")
print("      {session_id}/")
print("        overlays/          # Overlay images (*_overlay.png)")
print("        pngs/              # PNG conversions")
print("        ocr_results/      # OCR JSON files")
print("        diff_results/     # Diff JSON files")
print("        summaries/        # Summary JSON files")
print("        json/             # General JSON (change analysis, etc.)")
print("        files/             # Generic files")
print("        logs/             # Processing logs")
print()

# Check if directories exist
print("🔍 CURRENT STATE:")
outputs_dir = base_dir / local_output
if outputs_dir.exists():
    print(f"  ✓ Outputs directory exists: {outputs_dir}")
    subdirs = [d for d in outputs_dir.iterdir() if d.is_dir()]
    if subdirs:
        print(f"  ✓ Found {len(subdirs)} subdirectories:")
        for subdir in subdirs[:10]:  # Show first 10
            print(f"    - {subdir.name}/")
    else:
        print("  ℹ No subdirectories yet (will be created on first use)")
else:
    print(f"  ✗ Outputs directory doesn't exist yet (will be created on first use)")
print()

print("=" * 80)
print("NOTE: All paths are relative to the backend directory")
print("=" * 80)


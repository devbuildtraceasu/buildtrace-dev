#!/usr/bin/env python3

import os
import json
import re
from dotenv import load_dotenv
from gcp.database import get_db_session
from gcp.database.models import Session, Drawing, Comparison, AnalysisResult

# Load environment variables
load_dotenv()

def fix_session_data(session_id):
    """Fix session data by creating missing database records from results.json"""

    # Load results.json
    results_file = f"uploads/sessions/{session_id}/results.json"
    if not os.path.exists(results_file):
        print(f"❌ Results file not found: {results_file}")
        return

    with open(results_file, 'r') as f:
        results = json.load(f)

    print(f"Processing session {session_id}...")

    try:
        with get_db_session() as db:
            # Get existing session
            session = db.query(Session).filter_by(id=session_id).first()
            if not session:
                print(f"❌ Session {session_id} not found in database")
                return

            # Update total_time if missing
            if not session.total_time and 'summary' in results:
                session.total_time = results['summary'].get('total_time', 0)
                print(f"✅ Updated session total_time: {session.total_time}")

            # Get drawings
            old_drawing = db.query(Drawing).filter_by(session_id=session_id, drawing_type='old').first()
            new_drawing = db.query(Drawing).filter_by(session_id=session_id, drawing_type='new').first()

            if not old_drawing or not new_drawing:
                print(f"❌ Drawings not found for session {session_id}")
                return

            # Process analysis results
            analysis_results = results.get('analysis_results', [])
            for i, analysis in enumerate(analysis_results):
                if isinstance(analysis, str):
                    # Parse string representation
                    drawing_match = re.search(r"drawing_name='([^']*)'", analysis)
                    drawing_name = drawing_match.group(1) if drawing_match else f'Drawing {i+1}'

                    critical_match = re.search(r"critical_change='([^']*)'", analysis)
                    critical_change = critical_match.group(1) if critical_match else ''

                    # For summary, handle multi-line content
                    summary_match = re.search(r"analysis_summary='([^']*(?:\\'[^']*)*)'", analysis, re.DOTALL)
                    if not summary_match:
                        summary_match = re.search(r"analysis_summary=\"([^\"]*(?:\\\"[^\"]*)*?)\"", analysis, re.DOTALL)
                    summary = summary_match.group(1) if summary_match else 'Analysis completed'

                    # Check if comparison already exists
                    existing_comparison = db.query(Comparison).filter_by(
                        session_id=session_id,
                        drawing_name=drawing_name
                    ).first()

                    if not existing_comparison:
                        # Create comparison record
                        comparison = Comparison(
                            session_id=session_id,
                            old_drawing_id=old_drawing.id,
                            new_drawing_id=new_drawing.id,
                            drawing_name=drawing_name,
                            changes_detected=bool(critical_change)
                        )
                        db.add(comparison)
                        db.commit()
                        print(f"✅ Created comparison for {drawing_name}")

                        # Create analysis result
                        analysis_result = AnalysisResult(
                            comparison_id=comparison.id,
                            drawing_name=drawing_name,
                            critical_change=critical_change,
                            analysis_summary=summary,
                            success=True
                        )
                        db.add(analysis_result)
                        db.commit()
                        print(f"✅ Created analysis result for {drawing_name}")

                        # Add image paths if overlay files exist
                        possible_paths = [
                            f"new_A-101_new_overlays/{drawing_name}_overlay_results",
                            f"uploads/sessions/{session_id}/results/{drawing_name}",
                        ]

                        for overlay_dir in possible_paths:
                            if os.path.exists(overlay_dir):
                                for file_name in os.listdir(overlay_dir):
                                    if file_name.endswith('.png'):
                                        local_file_path = os.path.join(overlay_dir, file_name)
                                        if file_name.endswith('_overlay.png'):
                                            comparison.overlay_path = local_file_path
                                        elif file_name.endswith('_old.png'):
                                            comparison.old_image_path = local_file_path
                                        elif file_name.endswith('_new.png'):
                                            comparison.new_image_path = local_file_path
                                break

                        db.commit()
                        print(f"✅ Updated image paths for {drawing_name}")
                    else:
                        print(f"⚠️  Comparison already exists for {drawing_name}")

            print(f"✅ Session {session_id} data fixed successfully!")

    except Exception as e:
        print(f"❌ Error fixing session data: {e}")

if __name__ == "__main__":
    # Fix the recent session
    session_id = "993d613c-66b7-4fde-b3ce-380de35f48a8"
    fix_session_data(session_id)
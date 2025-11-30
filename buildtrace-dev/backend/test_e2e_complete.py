#!/usr/bin/env python3
"""
Complete End-to-End Test

Tests the full workflow:
1. Drawing Comparison (PDF → PNG → Overlay)
2. Change Analysis with Bounding Box Guidance
3. Output Management
4. API Endpoints (if running)
"""

import os
import sys
import logging
import json
from pathlib import Path
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from processing.drawing_comparison import compare_pdf_drawing_sets
from processing.change_analyzer import ChangeAnalyzer
from processing.complete_pipeline import complete_drawing_pipeline
from utils.local_output_manager import LocalOutputManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class E2ETestResults:
    """Track end-to-end test results"""
    
    def __init__(self):
        self.results = {
            'test_start': datetime.now().isoformat(),
            'steps': {},
            'overall_success': False,
            'outputs': {}
        }
    
    def record_step(self, step_name: str, success: bool, details: dict = None):
        """Record a test step"""
        self.results['steps'][step_name] = {
            'success': success,
            'timestamp': datetime.now().isoformat(),
            'details': details or {}
        }
    
    def save(self, output_path: str):
        """Save results to JSON"""
        self.results['test_end'] = datetime.now().isoformat()
        self.results['overall_success'] = all(
            step['success'] for step in self.results['steps'].values()
        )
        
        with open(output_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        logger.info(f"Test results saved to: {output_path}")


def find_test_pdfs():
    """Find A-111 test PDFs"""
    possible_locations = [
        Path("uploads/drawings/test-project-a111") / "9efc6ebb-876e-4d71-9a38-357b4788020c",
        Path("/Users/ashishrajshekhar/Desktop/Job_interview_tasks/Job_trial/testing/A-111"),
    ]
    
    old_pdf = None
    new_pdf = None
    
    for base_path in possible_locations:
        old_path = base_path / "A-111_old.pdf"
        new_path = base_path / "A-111_new.pdf"
        
        if old_path.exists() and new_path.exists():
            old_pdf = str(old_path)
            new_pdf = str(new_path)
            break
    
    return old_pdf, new_pdf


def test_drawing_comparison(test_results: E2ETestResults, old_pdf: str, new_pdf: str, output_manager: LocalOutputManager):
    """Test drawing comparison pipeline"""
    logger.info("=" * 80)
    logger.info("TEST 1: Drawing Comparison Pipeline")
    logger.info("=" * 80)
    
    try:
        results = compare_pdf_drawing_sets(
            old_pdf_path=old_pdf,
            new_pdf_path=new_pdf,
            dpi=300,
            debug=False,
            output_manager=output_manager
        )
        
        success = results['successful_overlays'] > 0
        
        test_results.record_step('drawing_comparison', success, {
            'matches_found': results['matches_found'],
            'successful_overlays': results['successful_overlays'],
            'failed_overlays': results.get('failed_overlays', 0),
            'output_folders': results.get('output_folders', [])
        })
        
        if success:
            logger.info(f"✓ Drawing comparison successful: {results['successful_overlays']} overlays created")
            return results
        else:
            logger.error("✗ Drawing comparison failed: No overlays created")
            return None
            
    except Exception as e:
        logger.error(f"✗ Drawing comparison failed: {e}", exc_info=True)
        test_results.record_step('drawing_comparison', False, {'error': str(e)})
        return None


def test_change_analyzer(test_results: E2ETestResults, overlay_folder: str, output_manager: LocalOutputManager):
    """Test change analyzer with bounding box guidance"""
    logger.info("=" * 80)
    logger.info("TEST 2: Change Analyzer with Bounding Box Guidance")
    logger.info("=" * 80)
    
    try:
        analyzer = ChangeAnalyzer()
        logger.info(f"✓ Using model: {analyzer.model_name}")
        
        result = analyzer.analyze_overlay_folder(
            overlay_folder,
            output_manager=output_manager
        )
        
        if result.success:
            # Check for spatial location information
            spatial_keywords = [
                'location', 'region', 'quadrant', 'section', 'legend', 
                'note', 'title block', 'grid', 'near', 'adjacent', 
                'main floor plan', 'northwest', 'northeast', 'southwest', 'southeast'
            ]
            
            spatial_changes = [c for c in result.changes_found if any(
                keyword in c.lower() for keyword in spatial_keywords
            )]
            
            spatial_ratio = len(spatial_changes) / len(result.changes_found) if result.changes_found else 0
            
            test_results.record_step('change_analyzer', True, {
                'drawing_name': result.drawing_name,
                'changes_found': len(result.changes_found),
                'recommendations': len(result.recommendations),
                'has_critical_change': bool(result.critical_change),
                'spatial_changes': len(spatial_changes),
                'spatial_ratio': spatial_ratio,
                'analysis_length': len(result.analysis_summary)
            })
            
            logger.info(f"✓ Change analysis successful")
            logger.info(f"  Changes found: {len(result.changes_found)}")
            logger.info(f"  Spatial location info: {len(spatial_changes)}/{len(result.changes_found)} ({spatial_ratio*100:.1f}%)")
            logger.info(f"  Recommendations: {len(result.recommendations)}")
            
            if spatial_ratio > 0.5:
                logger.info("  ✓ Good spatial location coverage")
            elif spatial_ratio > 0:
                logger.warning("  ⚠ Some spatial location info, but could be improved")
            else:
                logger.warning("  ⚠ No spatial location information detected")
            
            return result
        else:
            logger.error(f"✗ Change analysis failed: {result.error_message}")
            test_results.record_step('change_analyzer', False, {'error': result.error_message})
            return None
            
    except Exception as e:
        logger.error(f"✗ Change analysis failed: {e}", exc_info=True)
        test_results.record_step('change_analyzer', False, {'error': str(e)})
        return None


def test_complete_pipeline(test_results: E2ETestResults, old_pdf: str, new_pdf: str, output_manager: LocalOutputManager):
    """Test complete pipeline (comparison + analysis)"""
    logger.info("=" * 80)
    logger.info("TEST 3: Complete Pipeline (Comparison + Analysis)")
    logger.info("=" * 80)
    
    try:
        results = complete_drawing_pipeline(
            old_pdf_path=old_pdf,
            new_pdf_path=new_pdf,
            dpi=300,
            debug=False,
            skip_ai_analysis=False,
            output_manager=output_manager
        )
        
        success = results.get('success', False) and results['summary']['overlays_created'] > 0
        
        test_results.record_step('complete_pipeline', success, {
            'overlays_created': results['summary']['overlays_created'],
            'analyses_completed': results['summary']['analyses_completed'],
            'total_time': results['summary']['total_time'],
            'output_directories': results.get('output_directories', [])
        })
        
        if success:
            logger.info(f"✓ Complete pipeline successful")
            logger.info(f"  Overlays: {results['summary']['overlays_created']}")
            logger.info(f"  Analyses: {results['summary']['analyses_completed']}")
            logger.info(f"  Time: {results['summary']['total_time']:.1f}s")
            return results
        else:
            logger.error("✗ Complete pipeline failed")
            return None
            
    except Exception as e:
        logger.error(f"✗ Complete pipeline failed: {e}", exc_info=True)
        test_results.record_step('complete_pipeline', False, {'error': str(e)})
        return None


def test_output_management(test_results: E2ETestResults, output_manager: LocalOutputManager):
    """Test output management"""
    logger.info("=" * 80)
    logger.info("TEST 4: Output Management")
    logger.info("=" * 80)
    
    try:
        test_session = "e2e-test-session"
        session_path = output_manager.get_session_path(test_session)
        
        # Test saving files
        test_data = {"test": "data", "timestamp": datetime.now().isoformat()}
        json_path = output_manager.save_json(test_data, "test.json", session_id=test_session)
        
        # List files
        files = output_manager.list_session_files(test_session)
        
        test_results.record_step('output_management', True, {
            'session_path': str(session_path),
            'json_saved': json_path,
            'files_found': sum(len(v) for v in files.values())
        })
        
        logger.info(f"✓ Output management working")
        logger.info(f"  Session path: {session_path}")
        logger.info(f"  Files saved: {sum(len(v) for v in files.values())}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Output management failed: {e}", exc_info=True)
        test_results.record_step('output_management', False, {'error': str(e)})
        return False


def main():
    """Run complete end-to-end test"""
    
    logger.info("=" * 80)
    logger.info("BUILTRACE END-TO-END TEST")
    logger.info("=" * 80)
    logger.info("")
    
    test_results = E2ETestResults()
    output_manager = LocalOutputManager()
    
    # Find test PDFs
    logger.info("Looking for test PDFs...")
    old_pdf, new_pdf = find_test_pdfs()
    
    if not old_pdf or not new_pdf:
        logger.error("Could not find A-111 test PDFs")
        logger.info("Searched in:")
        logger.info("  - uploads/drawings/test-project-a111/")
        logger.info("  - /Users/ashishrajshekhar/Desktop/Job_interview_tasks/Job_trial/testing/A-111/")
        return False
    
    logger.info(f"✓ Found old PDF: {old_pdf}")
    logger.info(f"✓ Found new PDF: {new_pdf}")
    logger.info("")
    
    # Test 1: Drawing Comparison
    comparison_results = test_drawing_comparison(test_results, old_pdf, new_pdf, output_manager)
    if not comparison_results:
        logger.error("Drawing comparison failed, cannot continue")
        test_results.save("outputs/temp/logs/e2e_test_results.json")
        return False
    
    logger.info("")
    
    # Find overlay folder (check multiple possible names)
    new_pdf_name = Path(new_pdf).stem.replace("_new", "").replace("_old", "")
    possible_overlay_dirs = [
        Path(f"{new_pdf_name}_overlays"),
        Path(f"{Path(new_pdf).stem}_overlays"),  # e.g., A-111_new_overlays
        Path("A-111_new_overlays"),  # Direct check
    ]
    
    base_overlay_dir = None
    for overlay_dir in possible_overlay_dirs:
        if overlay_dir.exists():
            base_overlay_dir = overlay_dir
            break
    
    if not base_overlay_dir:
        logger.error(f"No overlay directory found. Checked: {possible_overlay_dirs}")
        test_results.save("outputs/temp/logs/e2e_test_results.json")
        return False
    
    overlay_folders = [f for f in base_overlay_dir.iterdir() 
                      if f.is_dir() and "_overlay_results" in f.name]
    
    if not overlay_folders:
        logger.error(f"No overlay folder found in {base_overlay_dir}")
        test_results.save("outputs/temp/logs/e2e_test_results.json")
        return False
    
    overlay_folder = str(overlay_folders[0])
    logger.info(f"✓ Using overlay folder: {overlay_folder}")
    logger.info("")
    
    # Test 2: Change Analyzer
    analysis_result = test_change_analyzer(test_results, overlay_folder, output_manager)
    logger.info("")
    
    # Test 3: Complete Pipeline
    complete_result = test_complete_pipeline(test_results, old_pdf, new_pdf, output_manager)
    logger.info("")
    
    # Test 4: Output Management
    output_test = test_output_management(test_results, output_manager)
    logger.info("")
    
    # Save results
    results_path = output_manager.save_processing_log(
        test_results.results,
        session_id="e2e-test"
    )
    test_results.save("outputs/temp/logs/e2e_test_results.json")
    
    # Summary
    logger.info("=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)
    
    all_success = all(step['success'] for step in test_results.results['steps'].values())
    
    for step_name, step_data in test_results.results['steps'].items():
        status = "✓" if step_data['success'] else "✗"
        logger.info(f"{status} {step_name}: {step_data['success']}")
    
    logger.info("")
    logger.info(f"Overall: {'✓ SUCCESS' if all_success else '✗ FAILED'}")
    logger.info(f"Results saved to: {results_path}")
    logger.info("=" * 80)
    
    return all_success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)


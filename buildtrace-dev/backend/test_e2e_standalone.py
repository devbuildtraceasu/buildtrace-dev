#!/usr/bin/env python3
"""
Standalone End-to-End Test for BuildTrace (No Database Required)

Tests the complete workflow without database:
1. Find test PDFs
2. Create overlays (drawing comparison)
3. Analyze changes with enhanced bounding box guidance
4. Verify all outputs are saved correctly
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import Dict, Optional

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from processing.drawing_comparison import compare_pdf_drawing_sets
from processing.change_analyzer import ChangeAnalyzer
from processing.complete_pipeline import complete_drawing_pipeline
from utils.local_output_manager import LocalOutputManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StandaloneE2ETester:
    """Standalone end-to-end test (no database)"""
    
    def __init__(self):
        self.output_manager = LocalOutputManager()
        self.results = {
            'success': False,
            'steps': {},
            'outputs': {},
            'errors': []
        }
    
    def find_test_pdfs(self) -> tuple[Optional[str], Optional[str]]:
        """Find test PDF files"""
        possible_locations = [
            Path("uploads/drawings/test-project-a111") / "9efc6ebb-876e-4d71-9a38-357b4788020c",
            Path("/Users/ashishrajshekhar/Desktop/Job_interview_tasks/Job_trial/testing/A-111"),
            Path("testrun/A-111"),
        ]
        
        for base_path in possible_locations:
            old_path = base_path / "A-111_old.pdf"
            new_path = base_path / "A-111_new.pdf"
            
            if old_path.exists() and new_path.exists():
                logger.info(f"✓ Found PDFs in: {base_path}")
                return str(old_path), str(new_path)
        
        return None, None
    
    def test_step(self, step_name: str, func, *args, **kwargs):
        """Execute a test step with error handling"""
        logger.info("=" * 80)
        logger.info(f"STEP: {step_name}")
        logger.info("=" * 80)
        
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            
            self.results['steps'][step_name] = {
                'success': True,
                'duration': duration,
                'result': result
            }
            logger.info(f"✓ {step_name} completed in {duration:.2f}s")
            return result
        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)
            
            self.results['steps'][step_name] = {
                'success': False,
                'duration': duration,
                'error': error_msg
            }
            self.results['errors'].append(f"{step_name}: {error_msg}")
            logger.error(f"✗ {step_name} failed: {error_msg}", exc_info=True)
            return None
    
    def test_drawing_comparison(self, old_pdf: str, new_pdf: str) -> Dict:
        """Test drawing comparison and overlay creation"""
        logger.info("Creating overlays from PDFs...")
        comparison_result = compare_pdf_drawing_sets(
            old_pdf_path=old_pdf,
            new_pdf_path=new_pdf,
            dpi=300,
            debug=False,
            output_manager=self.output_manager
        )
        return comparison_result
    
    def test_change_analysis(self, overlay_folder: str) -> Optional[Dict]:
        """Test change analysis with bounding box guidance"""
        logger.info(f"Analyzing changes in {overlay_folder}...")
        try:
            analyzer = ChangeAnalyzer()
            result = analyzer.analyze_overlay_folder(
                overlay_folder,
                output_manager=self.output_manager
            )
            if result.success:
                return result.to_dict()
            else:
                logger.error(f"Analysis failed: {result.error_message}")
                return None
        except Exception as e:
            logger.error(f"Failed to initialize analyzer: {e}")
            return None
    
    def test_complete_pipeline(self, old_pdf: str, new_pdf: str) -> Dict:
        """Test complete pipeline (comparison + analysis)"""
        logger.info("Running complete pipeline...")
        pipeline_result = complete_drawing_pipeline(
            old_pdf_path=old_pdf,
            new_pdf_path=new_pdf,
            dpi=300,
            debug=False,
            skip_ai_analysis=False,
            output_manager=self.output_manager
        )
        return pipeline_result
    
    def collect_outputs(self):
        """Collect all output locations"""
        logger.info("Collecting output locations...")
        
        outputs = {
            'base_output_path': str(self.output_manager.base_path),
            'sessions': [],
            'overlay_directories': []
        }
        
        # List all sessions
        sessions_dir = self.output_manager.base_path / 'sessions'
        if sessions_dir.exists():
            for session_dir in sessions_dir.iterdir():
                if session_dir.is_dir():
                    session_files = self.output_manager.list_session_files(session_dir.name)
                    outputs['sessions'].append({
                        'session_id': session_dir.name,
                        'files': session_files
                    })
        
        # Find overlay directories in working directory
        cwd = Path.cwd()
        overlay_dirs = list(cwd.glob("*_overlays"))
        for overlay_dir in overlay_dirs:
            if overlay_dir.is_dir():
                overlay_results = list(overlay_dir.glob("*_overlay_results"))
                outputs['overlay_directories'].append({
                    'directory': str(overlay_dir),
                    'overlay_folders': [str(f) for f in overlay_results]
                })
        
        self.results['outputs'] = outputs
        return outputs
    
    def run_full_test(self):
        """Run complete end-to-end test"""
        logger.info("=" * 80)
        logger.info("BUILTRACE STANDALONE END-TO-END TEST")
        logger.info("=" * 80)
        logger.info("Testing features migrated from buildtrace-overlay-")
        logger.info("")
        
        # Step 1: Find test PDFs
        old_pdf, new_pdf = self.test_step("Find Test PDFs", self.find_test_pdfs)
        if not old_pdf or not new_pdf:
            logger.error("Cannot proceed without test PDFs")
            return self.results
        
        # Step 2: Drawing Comparison
        comparison_result = self.test_step("Drawing Comparison", self.test_drawing_comparison, old_pdf, new_pdf)
        if not comparison_result:
            return self.results
        
        logger.info(f"  Created {comparison_result.get('successful_overlays', 0)} overlays")
        logger.info("")
        
        # Step 3: Change Analysis (if overlays created)
        analysis_result = None
        if comparison_result.get('output_folders'):
            overlay_folder = comparison_result['output_folders'][0]
            analysis_result = self.test_step("Change Analysis", self.test_change_analysis, overlay_folder)
            
            if analysis_result:
                logger.info(f"  Found {len(analysis_result.get('changes_found', []))} changes")
                
                # Check for spatial location information
                changes = analysis_result.get('changes_found', [])
                spatial_keywords = [
                    'location', 'region', 'quadrant', 'section', 'legend', 
                    'note', 'title block', 'grid', 'near', 'adjacent', 
                    'main floor plan', 'northwest', 'northeast'
                ]
                spatial_changes = [c for c in changes if any(
                    keyword in c.lower() for keyword in spatial_keywords
                )]
                
                logger.info(f"  Changes with spatial info: {len(spatial_changes)}/{len(changes)}")
        else:
            logger.warning("No overlay folders created, skipping change analysis")
        
        # Step 4: Complete Pipeline Test
        logger.info("")
        logger.info("Testing complete pipeline (comparison + analysis)...")
        pipeline_result = self.test_step("Complete Pipeline", self.test_complete_pipeline, old_pdf, new_pdf)
        
        # Step 5: Collect Outputs
        outputs = self.test_step("Collect Outputs", self.collect_outputs)
        
        # Final Summary
        logger.info("")
        logger.info("=" * 80)
        logger.info("TEST SUMMARY")
        logger.info("=" * 80)
        
        successful_steps = sum(1 for s in self.results['steps'].values() if s.get('success'))
        total_steps = len(self.results['steps'])
        
        logger.info(f"Steps completed: {successful_steps}/{total_steps}")
        logger.info("")
        
        for step_name, step_result in self.results['steps'].items():
            status = "✓" if step_result.get('success') else "✗"
            duration = step_result.get('duration', 0)
            logger.info(f"{status} {step_name}: {duration:.2f}s")
        
        logger.info("")
        
        if outputs:
            logger.info("Output Locations:")
            logger.info(f"  Base: {outputs.get('base_output_path')}")
            logger.info(f"  Sessions: {len(outputs.get('sessions', []))}")
            logger.info(f"  Overlay Directories: {len(outputs.get('overlay_directories', []))}")
            
            for overlay_dir in outputs.get('overlay_directories', []):
                logger.info(f"    - {overlay_dir['directory']}")
                logger.info(f"      Overlay folders: {len(overlay_dir.get('overlay_folders', []))}")
        
        logger.info("")
        
        if self.results['errors']:
            logger.error("Errors encountered:")
            for error in self.results['errors']:
                logger.error(f"  - {error}")
        else:
            logger.info("✓ All steps completed successfully!")
        
        self.results['success'] = successful_steps == total_steps
        
        logger.info("=" * 80)
        
        return self.results


def main():
    """Main entry point"""
    tester = StandaloneE2ETester()
    results = tester.run_full_test()
    
    # Save results
    output_manager = LocalOutputManager()
    output_manager.save_json(
        results,
        "e2e_standalone_test_results.json",
        subfolder="logs"
    )
    
    logger.info(f"Test results saved to: {output_manager.base_path}/logs/e2e_standalone_test_results.json")
    
    return 0 if results['success'] else 1


if __name__ == "__main__":
    sys.exit(main())


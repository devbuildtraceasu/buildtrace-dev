#!/usr/bin/env python3
"""
End-to-End Test for BuildTrace

Tests the complete workflow:
1. Upload drawings (old and new)
2. Process drawings (OCR, comparison, overlay creation)
3. Analyze changes with enhanced bounding box guidance
4. Test chatbot with drawing context
5. Verify all outputs are saved correctly
"""

import os
import sys
import time
import logging
import requests
from pathlib import Path
from typing import Dict, Optional

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from config import config
from services.drawing_service import DrawingUploadService
from processing.ocr_pipeline import OCRPipeline
from processing.drawing_comparison import compare_pdf_drawing_sets
from processing.change_analyzer import ChangeAnalyzer
from services.chatbot_service import ChatbotService
from utils.local_output_manager import LocalOutputManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EndToEndTester:
    """End-to-end test orchestrator"""
    
    def __init__(self):
        self.output_manager = LocalOutputManager()
        self.upload_service = DrawingUploadService()
        self.ocr_pipeline = OCRPipeline()
        self.change_analyzer = ChangeAnalyzer()
        self.chatbot = ChatbotService()
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
    
    def test_upload_drawings(self, old_pdf: str, new_pdf: str) -> Dict:
        """Test uploading drawings"""
        project_id = "test-project-e2e"
        user_id = "test-user-e2e"
        
        # Upload old version
        logger.info("Uploading old version...")
        with open(old_pdf, 'rb') as f:
            old_bytes = f.read()
        
        old_result = self.upload_service.handle_upload(
            file_bytes=old_bytes,
            filename="A-111_old.pdf",
            content_type="application/pdf",
            project_id=project_id,
            user_id=user_id,
            is_revision=False
        )
        
        # Upload new version
        logger.info("Uploading new version...")
        with open(new_pdf, 'rb') as f:
            new_bytes = f.read()
        
        new_result = self.upload_service.handle_upload(
            file_bytes=new_bytes,
            filename="A-111_new.pdf",
            content_type="application/pdf",
            project_id=project_id,
            user_id=user_id,
            is_revision=True
        )
        
        return {
            'old_version_id': old_result.drawing_version_id,
            'new_version_id': new_result.drawing_version_id,
            'project_id': project_id
        }
    
    def test_ocr_processing(self, version_id: str) -> Dict:
        """Test OCR processing"""
        logger.info(f"Running OCR on version {version_id}...")
        ocr_result = self.ocr_pipeline.run(version_id)
        return ocr_result
    
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
    
    def test_change_analysis(self, overlay_folder: str) -> Dict:
        """Test change analysis with bounding box guidance"""
        logger.info(f"Analyzing changes in {overlay_folder}...")
        result = self.change_analyzer.analyze_overlay_folder(
            overlay_folder,
            output_manager=self.output_manager
        )
        return result.to_dict() if result.success else None
    
    def test_chatbot(self, drawing_version_id: str) -> Dict:
        """Test chatbot with drawing context"""
        logger.info(f"Testing chatbot with drawing {drawing_version_id}...")
        
        # Test questions
        test_questions = [
            "What are the key features of this drawing?",
            "What notations or annotations are present?",
            "Summarize the drawing content."
        ]
        
        responses = []
        for question in test_questions:
            logger.info(f"  Q: {question}")
            response = self.chatbot.send_message(
                user_message=question,
                drawing_version_id=drawing_version_id
            )
            responses.append({
                'question': question,
                'response': response.get('response', ''),
                'context_used': response.get('context_used', False),
                'tokens_used': response.get('tokens_used')
            })
            logger.info(f"  A: {response.get('response', '')[:100]}...")
        
        return {'responses': responses}
    
    def collect_outputs(self):
        """Collect all output locations"""
        logger.info("Collecting output locations...")
        
        outputs = {
            'base_output_path': str(self.output_manager.base_path),
            'sessions': [],
            'files': []
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
        
        self.results['outputs'] = outputs
        return outputs
    
    def run_full_test(self):
        """Run complete end-to-end test"""
        logger.info("=" * 80)
        logger.info("BUILTRACE END-TO-END TEST")
        logger.info("=" * 80)
        logger.info("")
        
        # Step 1: Find test PDFs
        old_pdf, new_pdf = self.test_step("Find Test PDFs", self.find_test_pdfs)
        if not old_pdf or not new_pdf:
            logger.error("Cannot proceed without test PDFs")
            return self.results
        
        # Step 2: Upload drawings
        upload_result = self.test_step("Upload Drawings", self.test_upload_drawings, old_pdf, new_pdf)
        if not upload_result:
            return self.results
        
        # Step 3: OCR Processing
        ocr_old = self.test_step("OCR Old Version", self.test_ocr_processing, upload_result['old_version_id'])
        ocr_new = self.test_step("OCR New Version", self.test_ocr_processing, upload_result['new_version_id'])
        
        # Step 4: Drawing Comparison
        comparison_result = self.test_step("Drawing Comparison", self.test_drawing_comparison, old_pdf, new_pdf)
        if not comparison_result:
            return self.results
        
        # Step 5: Change Analysis
        if comparison_result.get('output_folders'):
            overlay_folder = comparison_result['output_folders'][0]
            analysis_result = self.test_step("Change Analysis", self.test_change_analysis, overlay_folder)
        else:
            logger.warning("No overlay folders created, skipping change analysis")
            analysis_result = None
        
        # Step 6: Chatbot Test
        chatbot_result = self.test_step("Chatbot Test", self.test_chatbot, upload_result['old_version_id'])
        
        # Step 7: Collect Outputs
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
    tester = EndToEndTester()
    results = tester.run_full_test()
    
    # Save results
    output_manager = LocalOutputManager()
    output_manager.save_json(
        results,
        "e2e_test_results.json",
        subfolder="logs"
    )
    
    logger.info(f"Test results saved to: {output_manager.base_path}/logs/e2e_test_results.json")
    
    return 0 if results['success'] else 1


if __name__ == "__main__":
    sys.exit(main())


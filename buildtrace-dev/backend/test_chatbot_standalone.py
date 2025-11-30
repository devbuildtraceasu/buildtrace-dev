"""
Standalone chatbot test - works without database
Directly processes A-111 PDFs and tests chatbot
"""

import sys
import os
import json
import tempfile
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from processing.ocr_pipeline import OCRPipeline
from services.chatbot_service import ChatbotService
from services.context_retriever import ContextRetriever
from gcp.storage import StorageService
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def process_pdf_directly(pdf_path: str, drawing_name: str) -> dict:
    """Process PDF: Convert to high-quality PNG first, then process for OCR"""
    logger.info(f"Processing {drawing_name}...")
    
    # Create a temporary drawing version ID
    import uuid
    temp_drawing_id = str(uuid.uuid4())
    
    # Initialize OCR pipeline
    ocr_pipeline = OCRPipeline()
    
    # Create output directory for PNGs
    base_dir = Path("/tmp/chatbot_pngs")
    base_dir.mkdir(exist_ok=True)
    png_output_dir = base_dir / drawing_name
    png_output_dir.mkdir(exist_ok=True)
    
    # Read PDF
    with open(pdf_path, 'rb') as f:
        pdf_bytes = f.read()
    
    # Save to temp file
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_pdf:
        tmp_pdf.write(pdf_bytes)
        tmp_pdf_path = tmp_pdf.name
    
    try:
        # Step 1: Extract drawing names from PDF
        from utils.drawing_extraction import extract_drawing_names
        drawing_names_data = extract_drawing_names(tmp_pdf_path)
        logger.info(f"  Found {len(drawing_names_data)} pages with drawing names")
        
        # Step 2: Convert PDF to HIGH-QUALITY PNGs first (400 DPI for better OCR)
        logger.info(f"  Converting PDF to PNG at 400 DPI (high quality)...")
        from pdf2image import convert_from_path
        from PIL import Image
        import cv2
        import numpy as np
        
        # Convert all pages at high DPI
        images = convert_from_path(tmp_pdf_path, dpi=400, fmt='PNG')
        logger.info(f"  Converted {len(images)} pages to PNG")
        
        # Save PNGs and create paths list
        png_paths = []
        for i, (pil_image, drawing_info) in enumerate(zip(images, drawing_names_data)):
            page_num = drawing_info.get('page', i + 1)
            page_drawing_name = drawing_info.get('drawing_name') or drawing_name
            
            # Save PNG with high quality
            png_filename = f"{page_drawing_name}_page{page_num}.png"
            png_path = png_output_dir / png_filename
            
            # Convert PIL to OpenCV format and save
            opencv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            cv2.imwrite(str(png_path), opencv_image, [cv2.IMWRITE_PNG_COMPRESSION, 1])  # Lossless compression
            
            png_paths.append(str(png_path))
            logger.info(f"  ✓ Saved high-quality PNG: {png_path} ({pil_image.size[0]}x{pil_image.size[1]})")
        
        # Step 3: Process each PNG for OCR
        logger.info(f"  Processing {len(png_paths)} PNGs for OCR...")
        ocr_results = []
        for i, (png_path, drawing_info) in enumerate(zip(png_paths, drawing_names_data)):
            page_num = drawing_info.get('page', i + 1)
            page_drawing_name = drawing_info.get('drawing_name') or drawing_name
            
            logger.info(f"  Processing page {page_num} from PNG: {png_path}")
            page_info = ocr_pipeline._extract_page_information(png_path, page_drawing_name, page_num)
            
            ocr_results.append({
                'drawing_name': page_drawing_name,
                'page_number': page_num,
                'extracted_info': page_info,
                'png_path': png_path,  # Keep reference to PNG
            })
        
        # Generate summary
        summary = ocr_pipeline._generate_summary(ocr_results)
        
        # Create OCR payload
        ocr_payload = {
            "drawing_version_id": temp_drawing_id,
            "drawing_name": drawing_name,
            "pages": ocr_results,
            "total_pages": len(ocr_results),
            "summary": summary,
            "png_output_dir": str(png_output_dir),  # Keep reference to PNG directory
        }
        
        logger.info(f"✓ Processing complete. PNGs saved to: {png_output_dir}")
        return ocr_payload
    
    finally:
        # Cleanup temp PDF (keep PNGs for inspection)
        if os.path.exists(tmp_pdf_path):
            os.unlink(tmp_pdf_path)

def test_chatbot_with_ocr_data(ocr_data_old: dict, ocr_data_new: dict):
    """Test chatbot with OCR data"""
    
    # Initialize chatbot
    try:
        chatbot = ChatbotService()
        logger.info("✅ Chatbot initialized\n")
    except Exception as e:
        logger.error(f"❌ Failed to initialize chatbot: {e}")
        return
    
    # Create a mock context retriever that uses our OCR data
    class MockContextRetriever:
        def __init__(self, ocr_data_old, ocr_data_new):
            self.ocr_data_old = ocr_data_old
            self.ocr_data_new = ocr_data_new
        
        def get_drawing_context(self, drawing_version_id: str) -> dict:
            # Return old or new based on a simple check
            # In real implementation, this would query database
            if 'old' in drawing_version_id.lower() or '1' in drawing_version_id:
                return self._format_context(self.ocr_data_old, 'A-111', 1)
            else:
                return self._format_context(self.ocr_data_new, 'A-111', 2)
        
        def get_multiple_drawings_context(self, drawing_version_ids: list) -> dict:
            contexts = []
            for dv_id in drawing_version_ids:
                if 'old' in dv_id.lower() or '1' in dv_id:
                    contexts.append(self._format_context(self.ocr_data_old, 'A-111', 1))
                else:
                    contexts.append(self._format_context(self.ocr_data_new, 'A-111', 2))
            return {'drawings': contexts, 'count': len(contexts)}
        
        def _format_context(self, ocr_data: dict, drawing_name: str, version: int) -> dict:
            context = {
                'drawing': {
                    'id': f'temp-{version}',
                    'drawing_name': drawing_name,
                    'version_number': version,
                },
                'summary': ocr_data.get('summary', {}),
                'pages': []
            }
            
            for page_data in ocr_data.get('pages', []):
                extracted_info = page_data.get('extracted_info', {})
                sections = extracted_info.get('sections', {})
                
                page_context = {
                    'page_number': page_data.get('page_number'),
                    'drawing_name': page_data.get('drawing_name'),
                    'key_sections': {}
                }
                
                # Map OCR section keys (numbered format) to readable names
                section_mapping = {
                    '1_title_block_and_project_identification': 'TITLE BLOCK & PROJECT IDENTIFICATION',
                    '5_revision_history_and_change_tracking': 'REVISION HISTORY & CHANGE TRACKING',
                    '6_keynotes_and_annotations': 'KEYNOTES & ANNOTATIONS',
                    '7_dimensions_and_measurements': 'DIMENSIONS & MEASUREMENTS',
                    '15_general_notes_and_disclaimers': 'GENERAL NOTES & DISCLAIMERS',
                }
                
                # Extract all sections - use actual keys from OCR
                for section_key, section_data in sections.items():
                    # Map to readable name if available
                    readable_name = section_mapping.get(section_key, section_key)
                    page_context['key_sections'][readable_name] = section_data
                
                # Also store all sections with original keys for completeness
                page_context['all_sections'] = sections
                
                context['pages'].append(page_context)
            
            return context
        
        def format_context_for_prompt(self, context: dict) -> str:
            retriever = ContextRetriever()
            return retriever.format_context_for_prompt(context)
        
        def format_multiple_context_for_prompt(self, contexts: dict) -> str:
            retriever = ContextRetriever()
            return retriever.format_multiple_context_for_prompt(contexts)
    
    # Replace chatbot's context retriever with mock
    mock_retriever = MockContextRetriever(ocr_data_old, ocr_data_new)
    chatbot.context_retriever = mock_retriever
    
    logger.info("=" * 60)
    logger.info("CHATBOT TEST - Option 1 (Simple Context Injection)")
    logger.info("=" * 60)
    logger.info("")
    
    # Test questions for old version
    logger.info("TEST 1: Questions about OLD version")
    logger.info("-" * 60)
    
    test_questions = [
        "What is this drawing about?",
        "What are the key notations on this drawing?",
        "What are the dimensions?",
        "What revision is this drawing?"
    ]
    
    # Maintain conversation history for multi-turn chat
    conversation_history = []
    
    for i, question in enumerate(test_questions, 1):
        logger.info(f"\nQ{i}: {question}")
        logger.info("-" * 60)
        
        response = chatbot.send_message(
            user_message=question,
            drawing_version_id="old-version-id",
            conversation_history=conversation_history
        )
        
        logger.info(f"Response: {response.get('response')}")
        logger.info(f"Context used: {response.get('context_used')}")
        if response.get('tokens_used'):
            logger.info(f"Tokens used: {response.get('tokens_used')}")
        
        # Add to conversation history for next turn
        conversation_history.append({"role": "user", "content": question})
        conversation_history.append({"role": "assistant", "content": response.get('response', '')})
    
    # Test with both versions
    logger.info("\n\n" + "=" * 60)
    logger.info("TEST 2: Questions about BOTH versions (comparison)")
    logger.info("-" * 60)
    
    comparison_questions = [
        "What are the differences between these two versions?",
        "What changed in the keynotes between old and new?",
        "Compare the dimensions between the two versions"
    ]
    
    # Maintain conversation history for comparison questions too
    comparison_history = []
    
    for i, question in enumerate(comparison_questions, 1):
        logger.info(f"\nQ{i}: {question}")
        logger.info("-" * 60)
        
        response = chatbot.send_message(
            user_message=question,
            drawing_version_ids=["old-version-id", "new-version-id"],
            conversation_history=comparison_history
        )
        
        logger.info(f"Response: {response.get('response')}")
        logger.info(f"Context used: {response.get('context_used')}")
        if response.get('tokens_used'):
            logger.info(f"Tokens used: {response.get('tokens_used')}")
        
        # Add to conversation history for next turn
        comparison_history.append({"role": "user", "content": question})
        comparison_history.append({"role": "assistant", "content": response.get('response', '')})

def main():
    base_path = "/Users/ashishrajshekhar/Desktop/Job_interview_tasks/Job_trial/testing/A-111"
    old_pdf = os.path.join(base_path, "A-111_old.pdf")
    new_pdf = os.path.join(base_path, "A-111_new.pdf")
    
    if not os.path.exists(old_pdf):
        logger.error(f"File not found: {old_pdf}")
        return
    
    if not os.path.exists(new_pdf):
        logger.error(f"File not found: {new_pdf}")
        return
    
    logger.info("=" * 60)
    logger.info("Processing A-111 Drawings for Chatbot Test")
    logger.info("=" * 60)
    logger.info("")
    
    # Process both PDFs
    logger.info("Step 1: Processing A-111_old.pdf...")
    ocr_data_old = process_pdf_directly(old_pdf, "A-111")
    logger.info("✓ Old version processed\n")
    
    logger.info("Step 2: Processing A-111_new.pdf...")
    ocr_data_new = process_pdf_directly(new_pdf, "A-111")
    logger.info("✓ New version processed\n")
    
    # Test chatbot
    logger.info("Step 3: Testing chatbot...")
    test_chatbot_with_ocr_data(ocr_data_old, ocr_data_new)
    
    logger.info("\n" + "=" * 60)
    logger.info("✓ Test completed!")
    logger.info("=" * 60)

if __name__ == '__main__':
    main()


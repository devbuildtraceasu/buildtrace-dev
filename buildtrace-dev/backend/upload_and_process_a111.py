"""
Script to upload A-111_old.pdf and A-111_new.pdf and run OCR on them
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.drawing_service import DrawingUploadService
from processing.ocr_pipeline import OCRPipeline
from gcp.database import get_db_session
from gcp.database.models import DrawingVersion
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # Paths to PDFs
    base_path = "/Users/ashishrajshekhar/Desktop/Job_interview_tasks/Job_trial/testing/A-111"
    old_pdf = os.path.join(base_path, "A-111_old.pdf")
    new_pdf = os.path.join(base_path, "A-111_new.pdf")
    
    if not os.path.exists(old_pdf):
        logger.error(f"File not found: {old_pdf}")
        return
    
    if not os.path.exists(new_pdf):
        logger.error(f"File not found: {new_pdf}")
        return
    
    # Project and user IDs
    project_id = "test-project-a111"
    user_id = "ash-system-0000000000001"
    
    # Initialize services
    upload_service = DrawingUploadService()
    ocr_pipeline = OCRPipeline()
    
    logger.info("=" * 60)
    logger.info("Uploading and Processing A-111 Drawings")
    logger.info("=" * 60)
    
    # Upload old version
    logger.info("\n1. Uploading A-111_old.pdf...")
    with open(old_pdf, 'rb') as f:
        old_bytes = f.read()
    
    old_result = upload_service.handle_upload(
        file_bytes=old_bytes,
        filename="A-111_old.pdf",
        content_type="application/pdf",
        project_id=project_id,
        user_id=user_id,
        is_revision=False
    )
    
    logger.info(f"✓ Old version uploaded: {old_result.drawing_version_id}")
    logger.info(f"  Drawing: {old_result.drawing_name}, Version: {old_result.version_number}")
    
    # Run OCR on old version
    logger.info("\n2. Running OCR on A-111_old...")
    try:
        ocr_result_old = ocr_pipeline.run(old_result.drawing_version_id)
        logger.info(f"✓ OCR completed for old version")
        logger.info(f"  OCR result ref: {ocr_result_old.get('ocr_result_ref', 'N/A')}")
    except Exception as e:
        logger.error(f"✗ OCR failed for old version: {e}")
        return
    
    # Upload new version (as revision)
    logger.info("\n3. Uploading A-111_new.pdf...")
    with open(new_pdf, 'rb') as f:
        new_bytes = f.read()
    
    new_result = upload_service.handle_upload(
        file_bytes=new_bytes,
        filename="A-111_new.pdf",
        content_type="application/pdf",
        project_id=project_id,
        user_id=user_id,
        is_revision=True
    )
    
    logger.info(f"✓ New version uploaded: {new_result.drawing_version_id}")
    logger.info(f"  Drawing: {new_result.drawing_name}, Version: {new_result.version_number}")
    
    # Run OCR on new version
    logger.info("\n4. Running OCR on A-111_new...")
    try:
        ocr_result_new = ocr_pipeline.run(new_result.drawing_version_id)
        logger.info(f"✓ OCR completed for new version")
        logger.info(f"  OCR result ref: {ocr_result_new.get('ocr_result_ref', 'N/A')}")
    except Exception as e:
        logger.error(f"✗ OCR failed for new version: {e}")
        return
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Old Version ID: {old_result.drawing_version_id}")
    logger.info(f"New Version ID: {new_result.drawing_version_id}")
    logger.info(f"Project ID: {project_id}")
    logger.info("\n✓ Both drawings uploaded and OCR completed!")
    logger.info("\nYou can now test the chatbot with:")
    logger.info(f"  python test_chatbot_quick.py {old_result.drawing_version_id}")
    logger.info(f"  python test_chatbot_quick.py {new_result.drawing_version_id}")

if __name__ == '__main__':
    main()


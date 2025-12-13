"""
Page Extractor Service
Extracts pages from PDFs and uploads them individually to GCS for streaming pipeline.
"""

import logging
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from gcp.storage import StorageService
from utils.pdf_parser import pdf_to_png, get_pdf_page_count
from utils.drawing_extraction import extract_drawing_names

logger = logging.getLogger(__name__)


@dataclass
class ExtractedPage:
    """Represents a single extracted page from a PDF."""
    page_number: int  # 1-indexed
    drawing_name: str
    gcs_path: str  # Path to the PNG in GCS
    local_path: Optional[str] = None  # Temp local path (for cleanup)


@dataclass
class ExtractionResult:
    """Result of page extraction for a PDF."""
    total_pages: int
    pages: List[ExtractedPage]
    pdf_gcs_path: str


class PageExtractorService:
    """
    Service to extract pages from PDFs and upload them individually.
    
    This enables streaming pipeline processing where each page can be
    processed independently through OCR → Diff → Summary stages.
    """
    
    def __init__(self, storage_service: Optional[StorageService] = None, dpi: int = 220):
        self.storage = storage_service or StorageService()
        self.dpi = dpi
    
    def extract_pages(
        self,
        pdf_gcs_path: str,
        job_id: str,
        version_type: str,  # 'old' or 'new'
    ) -> ExtractionResult:
        """
        Extract all pages from a PDF stored in GCS.
        
        Args:
            pdf_gcs_path: GCS path to the PDF file
            job_id: Job ID for organizing extracted pages
            version_type: 'old' or 'new' to indicate baseline vs revised
            
        Returns:
            ExtractionResult with list of extracted pages and their GCS paths
        """
        logger.info(
            "Starting page extraction",
            extra={
                "job_id": job_id,
                "pdf_gcs_path": pdf_gcs_path,
                "version_type": version_type
            }
        )
        
        # Download PDF to temp file
        pdf_bytes = self.storage.download_file(pdf_gcs_path)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save PDF locally
            pdf_path = Path(temp_dir) / "input.pdf"
            pdf_path.write_bytes(pdf_bytes)
            
            # Get page count and drawing names
            total_pages = get_pdf_page_count(str(pdf_path))
            drawing_info = extract_drawing_names(str(pdf_path))
            
            # Create drawing name lookup
            drawing_names = {}
            for info in drawing_info:
                page_num = info.get('page', 1)
                name = info.get('drawing_name') or f"Page_{page_num:03d}"
                drawing_names[page_num] = name
            
            # Fill in missing pages with default names
            for page_num in range(1, total_pages + 1):
                if page_num not in drawing_names:
                    drawing_names[page_num] = f"Page_{page_num:03d}"
            
            logger.info(
                f"PDF has {total_pages} pages",
                extra={"job_id": job_id, "drawing_names": drawing_names}
            )
            
            # Extract and upload each page
            extracted_pages: List[ExtractedPage] = []
            
            for page_num in range(1, total_pages + 1):
                drawing_name = drawing_names.get(page_num, f"Page_{page_num:03d}")
                
                # Convert page to PNG
                output_path = Path(temp_dir) / f"{version_type}_page_{page_num:03d}.png"
                pdf_to_png(str(pdf_path), str(output_path), self.dpi, page_num - 1)  # 0-indexed
                
                # Upload to GCS
                gcs_path = f"pages/{job_id}/{version_type}/page_{page_num:03d}.png"
                png_bytes = output_path.read_bytes()
                self.storage.upload_file(png_bytes, gcs_path, content_type="image/png")
                
                extracted_pages.append(ExtractedPage(
                    page_number=page_num,
                    drawing_name=drawing_name,
                    gcs_path=gcs_path,
                ))
                
                logger.info(
                    f"Extracted page {page_num}/{total_pages}: {drawing_name}",
                    extra={
                        "job_id": job_id,
                        "page_number": page_num,
                        "drawing_name": drawing_name,
                        "gcs_path": gcs_path
                    }
                )
            
            logger.info(
                f"Page extraction complete: {total_pages} pages",
                extra={"job_id": job_id}
            )
            
            return ExtractionResult(
                total_pages=total_pages,
                pages=extracted_pages,
                pdf_gcs_path=pdf_gcs_path
            )
    
    def extract_pages_from_bytes(
        self,
        pdf_bytes: bytes,
        job_id: str,
        version_type: str,
    ) -> ExtractionResult:
        """
        Extract pages from PDF bytes (for when PDF is already in memory).
        
        Args:
            pdf_bytes: Raw PDF bytes
            job_id: Job ID for organizing extracted pages
            version_type: 'old' or 'new'
            
        Returns:
            ExtractionResult with list of extracted pages
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save PDF locally
            pdf_path = Path(temp_dir) / "input.pdf"
            pdf_path.write_bytes(pdf_bytes)
            
            # Get page count and drawing names
            total_pages = get_pdf_page_count(str(pdf_path))
            drawing_info = extract_drawing_names(str(pdf_path))
            
            # Create drawing name lookup
            drawing_names = {}
            for info in drawing_info:
                page_num = info.get('page', 1)
                name = info.get('drawing_name') or f"Page_{page_num:03d}"
                drawing_names[page_num] = name
            
            for page_num in range(1, total_pages + 1):
                if page_num not in drawing_names:
                    drawing_names[page_num] = f"Page_{page_num:03d}"
            
            extracted_pages: List[ExtractedPage] = []
            
            for page_num in range(1, total_pages + 1):
                drawing_name = drawing_names.get(page_num, f"Page_{page_num:03d}")
                
                output_path = Path(temp_dir) / f"{version_type}_page_{page_num:03d}.png"
                pdf_to_png(str(pdf_path), str(output_path), self.dpi, page_num - 1)
                
                gcs_path = f"pages/{job_id}/{version_type}/page_{page_num:03d}.png"
                png_bytes = output_path.read_bytes()
                self.storage.upload_file(png_bytes, gcs_path, content_type="image/png")
                
                extracted_pages.append(ExtractedPage(
                    page_number=page_num,
                    drawing_name=drawing_name,
                    gcs_path=gcs_path,
                ))
            
            return ExtractionResult(
                total_pages=total_pages,
                pages=extracted_pages,
                pdf_gcs_path=""  # Not stored as full PDF in this case
            )


# Singleton instance
_page_extractor: Optional[PageExtractorService] = None


def get_page_extractor() -> PageExtractorService:
    """Get singleton page extractor instance."""
    global _page_extractor
    if _page_extractor is None:
        _page_extractor = PageExtractorService()
    return _page_extractor


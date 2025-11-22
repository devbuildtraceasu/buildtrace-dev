"""
PDF Parser Utility
Converts PDF pages to PNG images
"""

import fitz  # PyMuPDF
from pdf2image import convert_from_path
from typing import List, Optional
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

def pdf_to_png(pdf_path: str, output_dir: str, dpi: int = 300, page_num: Optional[int] = None) -> List[str]:
    """
    Convert PDF pages to PNG images
    
    Args:
        pdf_path: Path to PDF file
        output_dir: Directory to save PNG files
        dpi: Resolution for conversion
        page_num: Specific page to convert (None for all pages)
        
    Returns:
        List of paths to created PNG files
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    png_paths = []
    
    try:
        if page_num is not None:
            # Convert specific page
            pages = convert_from_path(pdf_path, dpi=dpi, first_page=page_num+1, last_page=page_num+1)
            output_file = output_path / f"page_{page_num+1}.png"
            pages[0].save(str(output_file), 'PNG')
            png_paths.append(str(output_file))
        else:
            # Convert all pages
            pages = convert_from_path(pdf_path, dpi=dpi)
            for i, page in enumerate(pages):
                output_file = output_path / f"page_{i+1}.png"
                page.save(str(output_file), 'PNG')
                png_paths.append(str(output_file))
        
        logger.info(f"Converted {len(png_paths)} pages from {pdf_path}")
        
    except Exception as e:
        logger.error(f"Error converting PDF to PNG: {e}")
        raise
    
    return png_paths

def get_pdf_page_count(pdf_path: str) -> int:
    """Get number of pages in PDF"""
    try:
        doc = fitz.open(pdf_path)
        count = len(doc)
        doc.close()
        return count
    except Exception as e:
        logger.error(f"Error getting page count: {e}")
        raise


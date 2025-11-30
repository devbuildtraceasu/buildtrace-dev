"""
PDF Parser Utility
Converts PDF pages to PNG images with drawing name support
"""

import fitz  # PyMuPDF
from pdf2image import convert_from_path
from typing import List, Optional, Dict
import logging
import os
from pathlib import Path
import cv2
import numpy as np
from utils.drawing_extraction import extract_drawing_names

logger = logging.getLogger(__name__)

def pdf_to_png(pdf_path: str, output_path: str = None, dpi: int = 300, page_number: int = 0) -> str:
    """
    Convert a PDF file to PNG image.
    
    Args:
        pdf_path: Path to the PDF file
        output_path: Output PNG path (optional, defaults to same name as PDF)
        dpi: Resolution for the conversion (default: 300)
        page_number: Which page to convert (0-indexed, default: 0 for first page)
    
    Returns:
        Path to the created PNG file
    """
    pdf_path_obj = Path(pdf_path)
    
    if not pdf_path_obj.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    # Generate output path if not provided
    if output_path is None:
        output_path = pdf_path_obj.with_suffix('.png')
    else:
        output_path = Path(output_path)
    
    try:
        # Convert PDF to images
        images = convert_from_path(pdf_path, dpi=dpi, first_page=page_number + 1, last_page=page_number + 1)
        
        if not images:
            raise ValueError(f"No pages found in PDF: {pdf_path}")
        
        # Get the first (and only) image
        pil_image = images[0]
        
        # Convert PIL image to OpenCV format (BGR)
        opencv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        
        # Save as PNG
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(output_path), opencv_image)
        
        logger.info(f"Successfully converted page {page_number + 1} to: {output_path}")
        return str(output_path)
        
    except Exception as e:
        logger.error(f"Failed to convert PDF {pdf_path}: {e}")
        raise

def process_pdf_with_drawing_names(pdf_path: str, dpi: int = 300) -> List[str]:
    """
    Process a PDF file by extracting drawing names and converting to PNG with proper naming.
    
    Args:
        pdf_path: Path to the input PDF file
        dpi: Resolution for PNG conversion (default: 300)
        
    Returns:
        List of paths to the created PNG files
        
    Example:
        Input: drawings/drawingset.pdf
        Output: drawings/drawingset/A-001.png, drawings/drawingset/A-101.png, etc.
    """
    pdf_path_obj = Path(pdf_path)
    
    if not pdf_path_obj.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path_obj}")
    
    logger.info(f"Processing PDF: {pdf_path_obj}")
    
    # Step 1: Extract drawing names from PDF pages
    logger.info("Step 1: Extracting drawing names from PDF pages...")
    drawing_info = extract_drawing_names(str(pdf_path_obj))
    
    logger.info(f"Found {len(drawing_info)} pages with drawing names")
    for info in drawing_info:
        drawing_name = info['drawing_name'] or '[not found]'
        logger.info(f"  Page {info['page']}: {drawing_name}")
    
    # Step 2: Create output directory
    pdf_name = pdf_path_obj.stem  # Get filename without extension
    output_dir = pdf_path_obj.parent / pdf_name
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Step 2: Created output directory: {output_dir}")
    
    # Step 3: Convert each page to PNG with drawing name
    logger.info("Step 3: Converting pages to PNG with drawing names...")
    png_paths = []
    
    for info in drawing_info:
        page_num = info['page'] - 1  # Convert to 0-indexed for pdf_to_png
        drawing_name = info['drawing_name']
        
        if drawing_name:
            # Use drawing name for filename
            output_filename = f"{drawing_name}.png"
            output_path = output_dir / output_filename
            
            logger.info(f"  Converting page {info['page']} ({drawing_name})...")
        else:
            # Fallback to generic page number if no drawing name found
            output_filename = f"page_{info['page']}.png"
            output_path = output_dir / output_filename

            logger.info(f"  Converting page {info['page']} (no drawing name found)...")
        
        try:
            # Convert PDF page to PNG
            pdf_to_png(str(pdf_path_obj), str(output_path), dpi, page_num)
            png_paths.append(str(output_path))
            logger.info(f"    Created: {output_filename}")
            
        except Exception as e:
            logger.error(f"    Error converting page {info['page']}: {e}")
            continue
    
    logger.info(f"Successfully converted {len(png_paths)} pages to PNG")
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


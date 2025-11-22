"""
Drawing Name Extraction Utility
Extracts drawing names (e.g., A-101, A-344-MB) from PDF pages
"""

import re
import fitz  # PyMuPDF
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
import pytesseract
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

# Regex to match drawing names
DRAWING_RE = re.compile(r"\b([A-Z]\d*)[-\s]?(\d{1,4}(?:\.\d{1,2})?|[A-Z]\d{1,4}(?:\.\d{1,2})?)([A-Z])?(?:-([A-Z0-9]{1,8}))?\b")

def extract_drawing_names(pdf_path: str) -> List[Dict[str, any]]:
    """
    Extract drawing names from all pages of a PDF
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        List of dicts with 'page' and 'drawing_name' keys
    """
    results = []
    
    try:
        doc = fitz.open(pdf_path)
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_rect = page.rect
            
            # Try text extraction first
            words = page.get_text("words")
            drawing_name = _extract_from_text(words, page_rect, page)
            
            # If not found, try OCR on bottom-right region
            if not drawing_name:
                drawing_name = _extract_from_ocr(page, page_rect)
            
            results.append({
                'page': page_num + 1,
                'drawing_name': drawing_name
            })
        
        doc.close()
        
    except Exception as e:
        logger.error(f"Error extracting drawing names: {e}")
        raise
    
    return results

def _extract_from_text(words, page_rect, page) -> Optional[str]:
    """Extract drawing name from text words"""
    candidates = []
    
    for (x0, y0, x1, y1, text, *_) in words:
        for m in DRAWING_RE.finditer(text):
            cand = _normalize_drawing_name(text, m)
            cx = 0.5 * (x0 + x1)
            cy = 0.5 * (y0 + y1)
            # Distance from bottom-right corner
            dist = ((page_rect.width - cx)**2 + (page_rect.height - cy)**2)**0.5
            candidates.append((cand, dist))
    
    if candidates:
        # Return candidate closest to bottom-right
        candidates.sort(key=lambda x: x[1])
        return candidates[0][0]
    
    return None

def _extract_from_ocr(page, page_rect) -> Optional[str]:
    """Extract drawing name using OCR on bottom-right region"""
    try:
        # Focus on bottom-right 20% of page
        margin = 0.2
        x0 = page_rect.width * (1 - margin)
        y0 = page_rect.height * (1 - margin)
        x1 = page_rect.width
        y1 = page_rect.height
        
        # Render region
        mat = fitz.Matrix(2, 2)  # 2x zoom for better OCR
        pix = page.get_pixmap(matrix=mat, clip=(x0, y0, x1, y1))
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        # OCR
        text = pytesseract.image_to_string(img)
        
        # Find drawing name in OCR text
        match = DRAWING_RE.search(text)
        if match:
            return _normalize_drawing_name(text, match)
        
    except Exception as e:
        logger.warning(f"OCR extraction failed: {e}")
    
    return None

def _normalize_drawing_name(text: str, match: re.Match) -> str:
    """Normalize drawing name while preserving format"""
    prefix = match.group(1)
    number = match.group(2)
    direct_letter = match.group(3)
    hyphen_suffix = match.group(4)
    
    # Find original separator
    start_pos = match.start()
    number_start = match.start(2)
    separator = text[start_pos + len(prefix):number_start]
    
    result = prefix + separator + number
    
    if direct_letter:
        result += direct_letter
    
    if hyphen_suffix:
        result += '-' + hyphen_suffix
    
    return result


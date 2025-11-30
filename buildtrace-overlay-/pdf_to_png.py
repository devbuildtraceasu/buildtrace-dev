#!/usr/bin/env python3
"""
PDF to PNG Converter

A utility script to convert PDF files to PNG images.
This is useful for preparing PDF drawings for the alignment tool.
"""

import argparse
import os
from pathlib import Path
from pdf2image import convert_from_path
import cv2
import numpy as np


def pdf_to_png(pdf_path: str, output_path: str = None, dpi: int = 300, page_number: int = 0):
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
    pdf_path = Path(pdf_path)
    
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    # Generate output path if not provided
    if output_path is None:
        output_path = pdf_path.with_suffix('.png')
    else:
        output_path = Path(output_path)
    
    print(f"Converting {pdf_path} to PNG...")
    print(f"DPI: {dpi}, Page: {page_number + 1}")
    
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
        cv2.imwrite(str(output_path), opencv_image)
        
        print(f"Successfully converted to: {output_path}")
        return str(output_path)
        
    except Exception as e:
        raise RuntimeError(f"Failed to convert PDF {pdf_path}: {e}")


def main():
    parser = argparse.ArgumentParser(description="Convert PDF files to PNG images")
    parser.add_argument("input", help="Input PDF file or directory containing PDFs")
    parser.add_argument("--output", "-o", help="Output PNG file or directory (optional)")
    parser.add_argument("--dpi", type=int, default=300, help="Resolution for conversion (default: 300)")
    parser.add_argument("--page", type=int, default=0, help="Page number to convert (0-indexed, default: 0)")
    parser.add_argument("--batch", action="store_true", help="Convert all PDFs in input directory")
    
    args = parser.parse_args()
    
    try:
            # Single file conversion
            pdf_to_png(args.input, args.output, args.dpi, args.page)
            
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

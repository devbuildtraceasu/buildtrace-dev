#!/usr/bin/env python3
"""
PDF to PNG Converter with Drawing Names

This script:
1. Extracts drawing names from PDF pages using extract_drawing_names()
2. Converts each page to PNG using pdf_to_png()
3. Renames PNG files using the extracted drawing names
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Optional
import argparse

from extract_drawing import extract_drawing_names
from pdf_to_png import pdf_to_png

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
    pdf_path = Path(pdf_path)
    
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    
    print(f"Processing PDF: {pdf_path}")
    
    # Step 1: Extract drawing names from PDF pages
    print("Step 1: Extracting drawing names from PDF pages...")
    drawing_info = extract_drawing_names(str(pdf_path))
    
    print(f"Found {len(drawing_info)} pages with drawing names:")
    for info in drawing_info:
        drawing_name = info['drawing_name'] or '[not found]'
        print(f"  Page {info['page']}: {drawing_name}")
    
    # Step 2: Create output directory
    pdf_name = pdf_path.stem  # Get filename without extension
    output_dir = pdf_path.parent / pdf_name
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Step 2: Created output directory: {output_dir}")
    
    # Step 3: Convert each page to PNG with drawing name
    print("Step 3: Converting pages to PNG with drawing names...")
    png_paths = []
    
    for info in drawing_info:
        page_num = info['page'] - 1  # Convert to 0-indexed for pdf_to_png
        drawing_name = info['drawing_name']
        
        if drawing_name:
            # Use drawing name for filename
            output_filename = f"{drawing_name}.png"
            output_path = output_dir / output_filename
            
            print(f"  Converting page {info['page']} ({drawing_name})...")
        else:
            # Fallback to generic page number if no drawing name found
            # Use generic pattern so old/new PDFs can match
            output_filename = f"page_{info['page']}.png"
            output_path = output_dir / output_filename

            print(f"  Converting page {info['page']} (no drawing name found)...")
        
        try:
            # Convert PDF page to PNG
            pdf_to_png(str(pdf_path), str(output_path), dpi, page_num)
            png_paths.append(str(output_path))
            print(f"    Created: {output_filename}")
            
        except Exception as e:
            print(f"    Error converting page {info['page']}: {e}")
            continue
    
    print(f"Successfully converted {len(png_paths)} pages to PNG")
    return png_paths


def main():
    """
    Command-line interface for PDF to PNG conversion with drawing names.
    """
    parser = argparse.ArgumentParser(
        description="Convert PDF pages to PNG files using extracted drawing names."
    )
    parser.add_argument("pdf_path", help="Path to the PDF file to convert.")
    parser.add_argument("--dpi", type=int, default=300, 
                       help="Resolution for PNG conversion (default: 300 DPI).")
    parser.add_argument("--list", action="store_true", 
                       help="List all created PNG files after conversion.")
    
    args = parser.parse_args()
    
    try:
        # Process PDF with drawing names
        png_paths = process_pdf_with_drawing_names(args.pdf_path, args.dpi)
        
        if args.list:
            print("\nCreated PNG files:")
            for i, png_path in enumerate(png_paths, 1):
                print(f"  {i}. {png_path}")
        
        print(f"\nConversion complete! Created {len(png_paths)} PNG files.")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

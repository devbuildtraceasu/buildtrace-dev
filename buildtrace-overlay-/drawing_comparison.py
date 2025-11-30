#!/usr/bin/env python3
"""
Drawing Comparison Module

This module provides functionality to compare drawing sets by:
1. Finding matching PNG files between old and new folders
2. Aligning and creating overlays for matching drawings
3. Organizing results in structured output folders
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import argparse

from align_drawings import AlignDrawings
from image_utils import create_overlay_image, load_image
from pdf_parser import process_pdf_with_drawing_names


def find_matching_png_files(old_folder: str, new_folder: str) -> List[Tuple[str, str, str]]:
    """
    Find matching PNG files between old and new folders based on filename.
    
    Args:
        old_folder: Path to folder containing old PNG files
        new_folder: Path to folder containing new PNG files
        
    Returns:
        List of tuples (filename, old_path, new_path) for matching files
    """
    old_path = Path(old_folder)
    new_path = Path(new_folder)
    
    if not old_path.exists():
        raise FileNotFoundError(f"Old folder not found: {old_folder}")
    if not new_path.exists():
        raise FileNotFoundError(f"New folder not found: {new_folder}")
    
    # Get all PNG files from both folders
    old_png_files = {f.stem: f for f in old_path.glob("*.png")}
    new_png_files = {f.stem: f for f in new_path.glob("*.png")}
    
    print(f"Found {len(old_png_files)} PNG files in old folder")
    print(f"Found {len(new_png_files)} PNG files in new folder")
    
    # Find matching filenames (without extension)
    common_filenames = set(old_png_files.keys()).intersection(set(new_png_files.keys()))
    
    matches = []
    for filename in sorted(common_filenames):
        old_file_path = old_png_files[filename]
        new_file_path = new_png_files[filename]
        matches.append((filename, str(old_file_path), str(new_file_path)))
        print(f"  ✓ {filename}.png")
    
    # Report unmatched files
    only_in_old = set(old_png_files.keys()) - set(new_png_files.keys())
    only_in_new = set(new_png_files.keys()) - set(old_png_files.keys())
    
    if only_in_old:
        print(f"\nFiles only in old folder ({len(only_in_old)}):")
        for filename in sorted(only_in_old):
            print(f"  - {filename}.png")
    
    if only_in_new:
        print(f"\nFiles only in new folder ({len(only_in_new)}):")
        for filename in sorted(only_in_new):
            print(f"  - {filename}.png")
    
    return matches


def create_drawing_overlay(old_image_path: str, new_image_path: str, output_folder: str, filename: str, debug: bool = False) -> Optional[str]:
    """
    Create an overlay comparison for two matching drawing images.
    
    Args:
        old_image_path: Path to old drawing image
        new_image_path: Path to new drawing image
        output_folder: Path to output folder for results
        filename: Base filename for output files
        debug: Enable debug mode for alignment
        
    Returns:
        Path to created overlay file, or None if failed
    """
    try:
        # Load images
        old_img = load_image(old_image_path)
        new_img = load_image(new_image_path)
        
        if old_img is None or new_img is None:
            print(f"  ❌ Failed to load images for {filename}")
            return None
        
        # Initialize aligner
        aligner = AlignDrawings(debug=debug)
        
        # Align images
        print(f"  Aligning {filename}...")
        aligned_old_img = aligner(old_img, new_img)
        
        # Create overlay
        print(f"  Creating overlay for {filename}...")
        overlay_img = create_overlay_image(aligned_old_img, new_img)
        
        # Save all three files (old, new, overlay) in the output folder
        output_path = Path(output_folder)
        output_path.mkdir(parents=True, exist_ok=True)
        
        import cv2
        
        # Save old image
        old_output_path = output_path / f"{filename}_old.png"
        cv2.imwrite(str(old_output_path), old_img)
        
        # Save new image
        new_output_path = output_path / f"{filename}_new.png"
        cv2.imwrite(str(new_output_path), new_img)
        
        # Save overlay
        overlay_output_path = output_path / f"{filename}_overlay.png"
        cv2.imwrite(str(overlay_output_path), overlay_img)
        
        print(f"  ✅ Created: {filename}_overlay.png")
        return str(overlay_output_path)
        
    except Exception as e:
        print(f"  ❌ Failed to process {filename}: {e}")
        return None


def compare_drawing_sets(old_folder: str, new_folder: str, output_base_name: str = "comparison_results", debug: bool = False) -> Dict:
    """
    Compare two drawing sets and create overlay results.
    
    Args:
        old_folder: Path to folder containing old PNG files
        new_folder: Path to folder containing new PNG files
        output_base_name: Base name for output folders
        debug: Enable debug mode
        
    Returns:
        Dictionary with comparison results and statistics
    """
    print("=" * 60)
    print("DRAWING SET COMPARISON")
    print("=" * 60)
    
    # Step 1: Find matching PNG files
    print("Step 1: Finding matching PNG files...")
    matches = find_matching_png_files(old_folder, new_folder)
    
    if not matches:
        print("No matching files found between the folders.")
        return {
            'matches_found': 0,
            'successful_overlays': 0,
            'failed_overlays': 0,
            'output_folders': []
        }
    
    # Step 2: Create overlays for each matching pair
    print(f"\nStep 2: Creating overlays for {len(matches)} matching files...")
    
    successful_overlays = 0
    failed_overlays = 0
    output_folders = []
    
    for filename, old_path, new_path in matches:
        print(f"\nProcessing {filename}...")
        
        # Create output folder named after the drawing
        output_folder_name = f"{filename}_overlay_results"
        output_folder = Path(output_base_name) / output_folder_name
        
        # Create overlay
        overlay_path = create_drawing_overlay(old_path, new_path, str(output_folder), filename, debug)
        
        if overlay_path:
            successful_overlays += 1
            output_folders.append(str(output_folder))
        else:
            failed_overlays += 1
    
    # Compile results
    results = {
        'matches_found': len(matches),
        'successful_overlays': successful_overlays,
        'failed_overlays': failed_overlays,
        'output_folders': output_folders,
        'matches': matches
    }
    
    print("\n" + "=" * 60)
    print("📊 COMPARISON SUMMARY")
    print("=" * 60)
    print(f"Matching files found: {results['matches_found']}")
    print(f"Successful overlays: {results['successful_overlays']}")
    print(f"Failed overlays: {results['failed_overlays']}")
    print(f"Output folders created: {len(output_folders)}")
    
    return results


def compare_pdf_drawing_sets(old_pdf_path: str, new_pdf_path: str, dpi: int = 300, debug: bool = False) -> Dict:
    """
    Complete pipeline: Convert PDFs to PNG, find matches, create overlays.
    
    This function does everything in one step:
    1. Converts both PDFs to PNG pages with drawing names
    2. Finds matching drawing names between the sets
    3. Creates alignment overlays for matching drawings
    4. Stores results in organized overlay folders
    
    Args:
        old_pdf_path: Path to old PDF file
        new_pdf_path: Path to new PDF file
        dpi: Resolution for PNG conversion
        debug: Enable debug mode for alignment
        
    Returns:
        Dictionary with complete comparison results
    """
    print("=" * 60)
    print("COMPLETE PDF DRAWING COMPARISON PIPELINE")
    print("=" * 60)
    
    # Step 1: Convert PDFs to PNG with drawing names
    print("Step 1: Converting PDFs to PNG with drawing names...")
    print(f"Processing old PDF: {old_pdf_path}")
    old_png_paths = process_pdf_with_drawing_names(old_pdf_path, dpi)
    
    print(f"Processing new PDF: {new_pdf_path}")
    new_png_paths = process_pdf_with_drawing_names(new_pdf_path, dpi)
    
    print(f"Old PDF: {len(old_png_paths)} pages converted")
    print(f"New PDF: {len(new_png_paths)} pages converted")
    
    # Step 2: Extract drawing names from PNG filenames
    print("\nStep 2: Finding matching drawings...")
    matches = []
    
    # Create filename mappings (without extension)
    old_files = {Path(p).stem: p for p in old_png_paths}
    new_files = {Path(p).stem: p for p in new_png_paths}
    
    # Find common filenames
    common_filenames = set(old_files.keys()).intersection(set(new_files.keys()))
    
    print(f"Found {len(common_filenames)} matching drawings:")
    for filename in sorted(common_filenames):
        old_path = old_files[filename]
        new_path = new_files[filename]
        matches.append((filename, old_path, new_path))
        print(f"  ✓ {filename}")
    
    # Report unmatched drawings
    only_in_old = set(old_files.keys()) - set(new_files.keys())
    only_in_new = set(new_files.keys()) - set(old_files.keys())
    
    if only_in_old:
        print(f"\nDrawings only in old PDF ({len(only_in_old)}):")
        for filename in sorted(only_in_old):
            print(f"  - {filename}")
    
    if only_in_new:
        print(f"\nDrawings only in new PDF ({len(only_in_new)}):")
        for filename in sorted(only_in_new):
            print(f"  - {filename}")
    
    if not matches:
        print("No matching drawings found between the PDFs.")
        return {
            'matches_found': 0,
            'successful_overlays': 0,
            'failed_overlays': 0,
            'output_folders': []
        }
    
    # Step 3: Create overlays for each matching pair
    print(f"\nStep 3: Creating overlays for {len(matches)} matching drawings...")
    
    # Create base output directory
    new_pdf_name = Path(new_pdf_path).stem
    base_output_dir = f"{new_pdf_name}_overlays"
    
    successful_overlays = 0
    failed_overlays = 0
    output_folders = []
    
    for filename, old_path, new_path in matches:
        print(f"\nProcessing {filename}...")
        
        # Create output folder named after the drawing
        output_folder_name = f"{filename}_overlay_results"
        output_folder = Path(base_output_dir) / output_folder_name
        
        # Create overlay
        overlay_path = create_drawing_overlay(old_path, new_path, str(output_folder), filename, debug)
        
        if overlay_path:
            successful_overlays += 1
            output_folders.append(str(output_folder))
        else:
            failed_overlays += 1
    
    # Compile results
    results = {
        'old_pdf': old_pdf_path,
        'new_pdf': new_pdf_path,
        'old_png_count': len(old_png_paths),
        'new_png_count': len(new_png_paths),
        'matches_found': len(matches),
        'successful_overlays': successful_overlays,
        'failed_overlays': failed_overlays,
        'output_folders': output_folders,
        'matches': matches,
        'only_in_old': list(only_in_old),
        'only_in_new': list(only_in_new)
    }
    
    print("\n" + "=" * 60)
    print("📊 FINAL SUMMARY")
    print("=" * 60)
    print(f"Old PDF: {old_pdf_path} ({results['old_png_count']} pages)")
    print(f"New PDF: {new_pdf_path} ({results['new_png_count']} pages)")
    print(f"Matching drawings: {results['matches_found']}")
    print(f"Successful overlays: {results['successful_overlays']}")
    print(f"Failed overlays: {results['failed_overlays']}")
    print(f"Output directory: {base_output_dir}/")
    
    return results


def main():
    """
    Command-line interface for drawing comparison.
    """
    parser = argparse.ArgumentParser(
        description="Compare two drawing sets and create overlay results.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Compare PNG folders:
  python drawing_comparison.py old_folder/ new_folder/
  
  # Compare PDF files (complete pipeline):
  python drawing_comparison.py old_drawings.pdf new_drawings.pdf --pdf-mode
  
  # With options:
  python drawing_comparison.py old_folder/ new_folder/ --output results --debug
  python drawing_comparison.py old.pdf new.pdf --pdf-mode --dpi 600 --debug
        """
    )
    
    parser.add_argument("old_path", help="Path to old folder (PNG files) or PDF file.")
    parser.add_argument("new_path", help="Path to new folder (PNG files) or PDF file.")
    parser.add_argument("--pdf-mode", action="store_true", 
                       help="Treat inputs as PDF files and run complete pipeline.")
    parser.add_argument("--output", default="comparison_results", 
                       help="Base name for output folders (default: comparison_results).")
    parser.add_argument("--dpi", type=int, default=300,
                       help="DPI for PDF conversion (default: 300, only used in PDF mode).")
    parser.add_argument("--debug", action="store_true", 
                       help="Enable debug mode for alignment process.")
    
    args = parser.parse_args()
    
    try:
        if args.pdf_mode:
            # PDF mode: Complete pipeline
            print("Running PDF comparison pipeline...")
            results = compare_pdf_drawing_sets(args.old_path, args.new_path, args.dpi, args.debug)
        else:
            # PNG folder mode: Direct comparison
            print("Running PNG folder comparison...")
            results = compare_drawing_sets(args.old_path, args.new_path, args.output, args.debug)
        
        print("\n🎉 Comparison completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Comparison failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

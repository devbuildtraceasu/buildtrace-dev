#!/usr/bin/env python3
"""
Create overlays from PDFs and test the enhanced change analyzer

This script:
1. Creates overlays from A-111 PDFs using the drawing comparison pipeline
2. Tests the enhanced change analyzer with bounding box guidance
"""

import os
import sys
import logging
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from processing.drawing_comparison import compare_pdf_drawing_sets
from processing.change_analyzer import ChangeAnalyzer
from utils.local_output_manager import LocalOutputManager

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)


def find_pdf_files():
    """Find A-111 PDF files"""
    possible_locations = [
        Path("uploads/drawings/test-project-a111") / "9efc6ebb-876e-4d71-9a38-357b4788020c",
        Path("/Users/ashishrajshekhar/Desktop/Job_interview_tasks/Job_trial/testing/A-111"),
        Path("testrun/A-111"),
    ]
    
    old_pdf = None
    new_pdf = None
    
    for base_path in possible_locations:
        old_path = base_path / "A-111_old.pdf"
        new_path = base_path / "A-111_new.pdf"
        
        if old_path.exists() and new_path.exists():
            old_pdf = str(old_path)
            new_pdf = str(new_path)
            logger.info(f"Found PDFs in: {base_path}")
            break
    
    return old_pdf, new_pdf


def main():
    """Main function to create overlays and test analyzer"""
    
    logger.info("=" * 80)
    logger.info("CREATE OVERLAYS AND TEST ENHANCED CHANGE ANALYZER")
    logger.info("=" * 80)
    logger.info("")
    
    # Step 1: Find PDF files
    logger.info("Step 1: Looking for A-111 PDF files...")
    old_pdf, new_pdf = find_pdf_files()
    
    if not old_pdf or not new_pdf:
        logger.error("Could not find A-111_old.pdf and A-111_new.pdf")
        logger.info("Searched in:")
        logger.info("  - uploads/drawings/test-project-a111/")
        logger.info("  - /Users/ashishrajshekhar/Desktop/Job_interview_tasks/Job_trial/testing/A-111/")
        logger.info("  - testrun/A-111/")
        return False
    
    logger.info(f"✓ Found old PDF: {old_pdf}")
    logger.info(f"✓ Found new PDF: {new_pdf}")
    logger.info("")
    
    # Step 2: Create overlays
    logger.info("Step 2: Creating overlays from PDFs...")
    logger.info("-" * 80)
    
    output_manager = LocalOutputManager()
    
    try:
        comparison_results = compare_pdf_drawing_sets(
            old_pdf_path=old_pdf,
            new_pdf_path=new_pdf,
            dpi=300,
            debug=False,
            output_manager=output_manager
        )
        
        if comparison_results['successful_overlays'] == 0:
            logger.error("Failed to create any overlays")
            return False
        
        logger.info(f"✓ Created {comparison_results['successful_overlays']} overlays")
        logger.info("")
        
        # Find the overlay folder
        new_pdf_name = Path(new_pdf).stem.replace("_new", "").replace("_old", "")
        base_overlay_dir = Path(f"{new_pdf_name}_overlays")
        
        if not base_overlay_dir.exists():
            logger.error(f"Overlay directory not found: {base_overlay_dir}")
            return False
        
        # Find A-111 overlay folder
        overlay_folders = [f for f in base_overlay_dir.iterdir() 
                          if f.is_dir() and "A-111" in f.name and "_overlay_results" in f.name]
        
        if not overlay_folders:
            logger.error(f"No A-111 overlay folder found in {base_overlay_dir}")
            return False
        
        overlay_folder = overlay_folders[0]
        logger.info(f"✓ Found overlay folder: {overlay_folder}")
        logger.info("")
        
    except Exception as e:
        logger.error(f"Failed to create overlays: {e}", exc_info=True)
        return False
    
    # Step 3: Test enhanced analyzer
    logger.info("Step 3: Testing enhanced change analyzer with bounding box guidance...")
    logger.info("-" * 80)
    
    try:
        analyzer = ChangeAnalyzer()
        logger.info(f"✓ Using model: {analyzer.model_name}")
        logger.info("")
        
        result = analyzer.analyze_overlay_folder(
            str(overlay_folder),
            output_manager=output_manager
        )
        
        if result.success:
            logger.info("=" * 80)
            logger.info("ANALYSIS RESULTS")
            logger.info("=" * 80)
            logger.info("")
            
            logger.info(f"Drawing: {result.drawing_name}")
            logger.info("")
            
            logger.info("Most Critical Change:")
            logger.info(f"  {result.critical_change}")
            logger.info("")
            
            logger.info(f"Changes Found ({len(result.changes_found)}):")
            for i, change in enumerate(result.changes_found, 1):
                logger.info(f"  {i}. {change}")
            logger.info("")
            
            logger.info(f"Recommendations ({len(result.recommendations)}):")
            for i, rec in enumerate(result.recommendations, 1):
                logger.info(f"  {i}. {rec}")
            logger.info("")
            
            # Check for spatial location information
            spatial_keywords = [
                'location', 'region', 'quadrant', 'section', 'legend', 
                'note', 'title block', 'grid', 'near', 'adjacent', 'main floor plan',
                'northwest', 'northeast', 'southwest', 'southeast'
            ]
            
            spatial_changes = [c for c in result.changes_found if any(
                keyword in c.lower() for keyword in spatial_keywords
            )]
            
            logger.info("=" * 80)
            logger.info("SPATIAL LOCATION ANALYSIS")
            logger.info("=" * 80)
            logger.info(f"Changes with spatial location info: {len(spatial_changes)}/{len(result.changes_found)}")
            logger.info("")
            
            if spatial_changes:
                logger.info("Changes with spatial references:")
                for i, change in enumerate(spatial_changes[:5], 1):  # Show first 5
                    logger.info(f"  {i}. {change[:150]}...")
            else:
                logger.warning("⚠ No spatial location information detected in changes")
                logger.info("This may indicate the prompt needs further refinement")
            logger.info("")
            
            # Save results
            logger.info("=" * 80)
            logger.info("SAVED OUTPUTS")
            logger.info("=" * 80)
            logger.info(f"Overlays saved to: {base_overlay_dir}")
            logger.info(f"Analysis saved to: {output_manager.base_path}/sessions/")
            logger.info("")
            
            logger.info("=" * 80)
            logger.info("✓ TEST COMPLETE")
            logger.info("=" * 80)
            
            return True
        else:
            logger.error(f"Analysis failed: {result.error_message}")
            return False
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)


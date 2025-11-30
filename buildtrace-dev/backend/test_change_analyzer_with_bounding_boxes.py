#!/usr/bin/env python3
"""
Test the enhanced change analyzer with bounding box guidance

This script tests the improved change analyzer that uses spatial location
and bounding box concepts for better change detection.
"""

import os
import sys
import logging
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from processing.change_analyzer import ChangeAnalyzer
from utils.local_output_manager import LocalOutputManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_enhanced_analyzer():
    """Test the enhanced change analyzer with bounding box guidance"""
    
    # Try multiple possible locations for overlay folder
    possible_paths = [
        Path("testrun/A-111") / "A-111_overlay_results",
        Path("testrun/A-111"),
        Path("testrun/A-101") / "A-101_overlay_results",
        Path("testrun/A-101"),
        Path("testrun/comprehensive_test"),
    ]
    
    test_overlay_path = None
    for path in possible_paths:
        if path.exists():
            # Check if it has the required PNG files
            png_files = list(path.glob("*.png"))
            has_old = any("_old" in f.name.lower() for f in png_files)
            has_new = any("_new" in f.name.lower() for f in png_files)
            has_overlay = any("_overlay" in f.name.lower() for f in png_files)
            
            if has_old and has_new and has_overlay:
                test_overlay_path = path
                logger.info(f"Found overlay folder: {path}")
                break
            elif path.is_dir() and len(png_files) > 0:
                # Might be a folder with PNGs but wrong naming
                logger.info(f"Found folder with PNGs: {path} (but may need proper naming)")
    
    if not test_overlay_path:
        logger.warning("No overlay folder found with required PNG files")
        logger.info("Searched in:")
        for path in possible_paths:
            logger.info(f"  - {path}")
        logger.info()
        logger.info("To create overlays, you can:")
        logger.info("  1. Use the drawing comparison pipeline to generate overlays")
        logger.info("  2. Or manually create a folder with:")
        logger.info("     - {drawing_name}_old.png")
        logger.info("     - {drawing_name}_new.png")
        logger.info("     - {drawing_name}_overlay.png")
        logger.info("")
        logger.info("Would you like to generate overlays from PDFs? (requires A-111_old.pdf and A-111_new.pdf)")
        return
    
    logger.info("=" * 80)
    logger.info("TESTING ENHANCED CHANGE ANALYZER WITH BOUNDING BOX GUIDANCE")
    logger.info("=" * 80)
    logger.info()
    
    try:
        # Initialize analyzer
        logger.info("Initializing Change Analyzer...")
        analyzer = ChangeAnalyzer()
        logger.info(f"✓ Using model: {analyzer.model_name}")
        logger.info()
        
        # Initialize output manager
        output_manager = LocalOutputManager()
        logger.info(f"✓ Output manager initialized: {output_manager.base_path}")
        logger.info()
        
        # Analyze overlay folder
        logger.info(f"Analyzing overlay folder: {test_overlay_path}")
        logger.info()
        
        result = analyzer.analyze_overlay_folder(
            str(test_overlay_path),
            output_manager=output_manager
        )
        
        if result.success:
            logger.info("=" * 80)
            logger.info("ANALYSIS RESULTS")
            logger.info("=" * 80)
            logger.info()
            
            logger.info(f"Drawing: {result.drawing_name}")
            logger.info()
            
            logger.info("Most Critical Change:")
            logger.info(f"  {result.critical_change}")
            logger.info()
            
            logger.info(f"Changes Found ({len(result.changes_found)}):")
            for i, change in enumerate(result.changes_found, 1):
                logger.info(f"  {i}. {change}")
            logger.info()
            
            logger.info(f"Recommendations ({len(result.recommendations)}):")
            for i, rec in enumerate(result.recommendations, 1):
                logger.info(f"  {i}. {rec}")
            logger.info()
            
            # Check for spatial location information
            spatial_changes = [c for c in result.changes_found if any(
                keyword in c.lower() for keyword in [
                    'location', 'region', 'quadrant', 'section', 'legend', 
                    'note', 'title block', 'grid', 'near', 'adjacent'
                ]
            )]
            
            logger.info("=" * 80)
            logger.info("SPATIAL LOCATION ANALYSIS")
            logger.info("=" * 80)
            logger.info(f"Changes with spatial location info: {len(spatial_changes)}/{len(result.changes_found)}")
            logger.info()
            
            if spatial_changes:
                logger.info("Changes with spatial references:")
                for i, change in enumerate(spatial_changes[:5], 1):  # Show first 5
                    logger.info(f"  {i}. {change[:100]}...")
            else:
                logger.warning("⚠ No spatial location information detected in changes")
                logger.info("This may indicate the prompt needs further refinement")
            logger.info()
            
            # Save results
            logger.info("=" * 80)
            logger.info("SAVED OUTPUTS")
            logger.info("=" * 80)
            logger.info(f"Analysis saved to: {output_manager.base_path}/sessions/")
            logger.info()
            
        else:
            logger.error(f"Analysis failed: {result.error_message}")
            return False
        
        logger.info("=" * 80)
        logger.info("✓ TEST COMPLETE")
        logger.info("=" * 80)
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = test_enhanced_analyzer()
    sys.exit(0 if success else 1)


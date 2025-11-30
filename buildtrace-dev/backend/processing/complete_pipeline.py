"""
Complete Drawing Pipeline

This module provides a single function that runs the entire drawing comparison
and analysis pipeline from PDF files to AI-generated change lists.

Adapted from buildtrace-overlay- for buildtrace-dev with Gemini support
"""

import os
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional

from processing.drawing_comparison import compare_pdf_drawing_sets
from processing.change_analyzer import ChangeAnalyzer
from utils.local_output_manager import LocalOutputManager
from config import config

logger = logging.getLogger(__name__)


def complete_drawing_pipeline(
    old_pdf_path: str, 
    new_pdf_path: str, 
    dpi: int = 300, 
    debug: bool = False, 
    skip_ai_analysis: bool = False,
    output_manager: Optional[LocalOutputManager] = None
) -> Dict:
    """
    Complete pipeline: PDF → PNG → Overlay → AI Analysis
    
    This function runs the entire workflow:
    1. Converts both PDFs to PNG pages with drawing names
    2. Finds matching drawings between old and new sets
    3. Creates alignment overlays for matching drawings
    4. Analyzes each overlay using Gemini to generate change lists
    
    Args:
        old_pdf_path: Path to old PDF file
        new_pdf_path: Path to new PDF file
        dpi: Resolution for PNG conversion (default: 300)
        debug: Enable debug mode for alignment process
        skip_ai_analysis: Skip AI analysis step (default: False)
        output_manager: Optional LocalOutputManager for saving files
        
    Returns:
        Dictionary with complete pipeline results including:
        - comparison_results: Results from drawing comparison
        - analysis_results: Results from AI analysis
        - output_directories: All generated directories
        - summary: Overall pipeline summary
    """
    logger.info("=" * 80)
    logger.info("🚀 COMPLETE DRAWING PIPELINE")
    logger.info("=" * 80)
    logger.info(f"Old PDF: {old_pdf_path}")
    logger.info(f"New PDF: {new_pdf_path}")
    logger.info(f"DPI: {dpi}")
    logger.info(f"Debug Mode: {debug}")
    logger.info(f"AI Analysis: {'Skipped' if skip_ai_analysis else 'Enabled'}")
    logger.info("=" * 80)
    
    start_time = time.time()
    
    try:
        # Step 1: PDF to PNG + Overlay Creation
        logger.info("📋 STEP 1: PDF Processing and Overlay Creation")
        logger.info("-" * 50)
        
        comparison_results = compare_pdf_drawing_sets(
            old_pdf_path=old_pdf_path,
            new_pdf_path=new_pdf_path,
            dpi=dpi,
            debug=debug,
            output_manager=output_manager
        )
        
        if comparison_results['successful_overlays'] == 0:
            logger.warning("No successful overlays created, but continuing with analysis...")
        else:
            logger.info(f"✅ Step 1 Complete: {comparison_results['successful_overlays']} overlays created")
        
        # Report any failed overlays
        if comparison_results.get('failed_overlays', 0) > 0:
            logger.warning(f"{comparison_results['failed_overlays']} overlays failed to create")
        
        # Step 2: AI Analysis (if not skipped)
        analysis_results = []
        if not skip_ai_analysis:
            logger.info(f"🤖 STEP 2: AI Analysis of {comparison_results['successful_overlays']} Overlays")
            logger.info("-" * 50)
            
            try:
                # Initialize Gemini analyzer
                analyzer = ChangeAnalyzer()
                
                # Get the base overlay directory
                new_pdf_name = Path(new_pdf_path).stem
                base_overlay_dir = f"{new_pdf_name}_overlays"
                
                if not Path(base_overlay_dir).exists():
                    logger.warning(f"Overlay directory not found: {base_overlay_dir}")
                    logger.info("Skipping AI analysis...")
                else:
                    # Analyze all overlay folders
                    analysis_results = analyzer.analyze_multiple_overlays(
                        base_overlay_dir,
                        output_manager=output_manager
                    )
                    
                    # Save results
                    saved_files = analyzer.save_results(
                        analysis_results,
                        base_overlay_dir=base_overlay_dir,
                        output_manager=output_manager
                    )
                    
                    # Report results with detailed success/failure breakdown
                    successful_analyses = sum(1 for r in analysis_results if r.success)
                    failed_analyses = sum(1 for r in analysis_results if not r.success)
                    
                    logger.info(f"✅ Step 2 Complete: {successful_analyses} AI analyses completed")
                    if failed_analyses > 0:
                        logger.warning(f"{failed_analyses} AI analyses failed")
                        # Show which ones failed
                        for result in analysis_results:
                            if not result.success:
                                logger.warning(f"❌ {result.drawing_name}: {result.error_message}")
                    logger.info(f"📁 Analysis files saved: {len(saved_files)}")
                    
            except Exception as e:
                logger.error(f"AI Analysis encountered an error: {e}", exc_info=True)
                logger.info("Continuing with pipeline completion...")
                analysis_results = []
        else:
            logger.info("⏭️  STEP 2: AI Analysis Skipped")
            analysis_results = []
        
        # Compile final results
        total_time = time.time() - start_time
        
        # Collect all output directories
        output_directories = []
        if comparison_results.get('output_folders'):
            output_directories.extend(comparison_results['output_folders'])
        
        # Add base overlay directory
        new_pdf_name = Path(new_pdf_path).stem
        base_overlay_dir = f"{new_pdf_name}_overlays"
        if Path(base_overlay_dir).exists():
            output_directories.append(base_overlay_dir)
        
        # Calculate analyses completed safely
        try:
            analyses_completed = sum(1 for r in analysis_results if r.success) if analysis_results else 0
        except (AttributeError, TypeError):
            # Fallback if analysis_results structure is unexpected
            analyses_completed = len(analysis_results) if analysis_results else 0
        
        pipeline_results = {
            'success': True,
            'comparison_results': comparison_results,
            'analysis_results': [r.to_dict() if hasattr(r, 'to_dict') else r for r in analysis_results],
            'output_directories': output_directories,
            'summary': {
                'total_time': total_time,
                'overlays_created': comparison_results['successful_overlays'],
                'analyses_completed': analyses_completed,
                'ai_analysis_skipped': skip_ai_analysis,
                'base_overlay_directory': base_overlay_dir
            }
        }
        
        # Print final summary
        logger.info("=" * 80)
        logger.info("🎉 PIPELINE COMPLETE!")
        logger.info("=" * 80)
        logger.info(f"⏱️  Total Time: {total_time:.1f} seconds")
        
        # Overlay summary
        successful_overlays = comparison_results['successful_overlays']
        failed_overlays = comparison_results.get('failed_overlays', 0)
        logger.info(f"📊 Overlays: {successful_overlays} successful, {failed_overlays} failed")
        
        # AI Analysis summary
        if not skip_ai_analysis and analysis_results:
            try:
                successful_analyses = sum(1 for r in analysis_results if r.success)
                failed_analyses = sum(1 for r in analysis_results if not r.success)
                logger.info(f"🤖 AI Analyses: {successful_analyses} successful, {failed_analyses} failed")
            except (AttributeError, TypeError):
                logger.info(f"🤖 AI Analyses: {len(analysis_results)} completed")
        elif skip_ai_analysis:
            logger.info("🤖 AI Analyses: Skipped")
        else:
            logger.info("🤖 AI Analyses: None attempted")
            
        logger.info(f"📁 Output Directory: {base_overlay_dir}/")
        
        # Overall success determination
        if successful_overlays > 0:
            logger.info("✅ Pipeline Status: SUCCESS (overlays created)")
        else:
            logger.warning("⚠️  Pipeline Status: PARTIAL (no overlays created)")
        logger.info("=" * 80)
        
        return pipeline_results
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        
        return {
            'success': False,
            'error': str(e),
            'comparison_results': None,
            'analysis_results': None,
            'output_directories': [],
            'summary': {
                'total_time': time.time() - start_time,
                'overlays_created': 0,
                'analyses_completed': 0
            }
        }


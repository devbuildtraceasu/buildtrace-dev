#!/usr/bin/env python3
"""
Complete Drawing Pipeline

This module provides a single function that runs the entire drawing comparison
and analysis pipeline from PDF files to AI-generated change lists.

Usage:
    python complete_drawing_pipeline.py old_drawings.pdf new_drawings.pdf
    python complete_drawing_pipeline.py --test
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Optional
import time

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from drawing_comparison import compare_pdf_drawing_sets
    from openai_change_analyzer import OpenAIChangeAnalyzer
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Make sure all dependencies are installed: pip install -r requirements.txt")
    sys.exit(1)


def complete_drawing_pipeline(old_pdf_path: str, new_pdf_path: str, 
                            dpi: int = 300, debug: bool = False, 
                            skip_ai_analysis: bool = False) -> Dict:
    """
    Complete pipeline: PDF → PNG → Overlay → AI Analysis
    
    This function runs the entire workflow:
    1. Converts both PDFs to PNG pages with drawing names
    2. Finds matching drawings between old and new sets
    3. Creates alignment overlays for matching drawings
    4. Analyzes each overlay using OpenAI to generate change lists
    
    Args:
        old_pdf_path: Path to old PDF file
        new_pdf_path: Path to new PDF file
        dpi: Resolution for PNG conversion (default: 300)
        debug: Enable debug mode for alignment process
        skip_ai_analysis: Skip OpenAI analysis step (default: False)
        
    Returns:
        Dictionary with complete pipeline results including:
        - comparison_results: Results from drawing comparison
        - analysis_results: Results from OpenAI analysis
        - output_directories: All generated directories
        - summary: Overall pipeline summary
    """
    print("=" * 80)
    print("🚀 COMPLETE DRAWING PIPELINE")
    print("=" * 80)
    print(f"Old PDF: {old_pdf_path}")
    print(f"New PDF: {new_pdf_path}")
    print(f"DPI: {dpi}")
    print(f"Debug Mode: {debug}")
    print(f"AI Analysis: {'Skipped' if skip_ai_analysis else 'Enabled'}")
    print("=" * 80)
    
    start_time = time.time()
    
    try:
        # Step 1: PDF to PNG + Overlay Creation
        print("\n📋 STEP 1: PDF Processing and Overlay Creation")
        print("-" * 50)
        
        comparison_results = compare_pdf_drawing_sets(
            old_pdf_path=old_pdf_path,
            new_pdf_path=new_pdf_path,
            dpi=dpi,
            debug=debug
        )
        
        if comparison_results['successful_overlays'] == 0:
            print("⚠️  No successful overlays created, but continuing with analysis...")
        else:
            print(f"✅ Step 1 Complete: {comparison_results['successful_overlays']} overlays created")
        
        # Report any failed overlays
        if comparison_results.get('failed_overlays', 0) > 0:
            print(f"⚠️  {comparison_results['failed_overlays']} overlays failed to create")
        
        # Step 2: AI Analysis (if not skipped)
        analysis_results = []
        if not skip_ai_analysis:
            print(f"\n🤖 STEP 2: AI Analysis of {comparison_results['successful_overlays']} Overlays")
            print("-" * 50)
            
            try:
                # Initialize OpenAI analyzer
                analyzer = OpenAIChangeAnalyzer()
                
                # Get the base overlay directory
                new_pdf_name = Path(new_pdf_path).stem
                base_overlay_dir = f"{new_pdf_name}_overlays"
                
                if not Path(base_overlay_dir).exists():
                    print(f"⚠️  Overlay directory not found: {base_overlay_dir}")
                    print("   Skipping AI analysis...")
                else:
                    # Analyze all overlay folders
                    analysis_results = analyzer.analyze_multiple_overlays(base_overlay_dir)
                    
                    # Save results
                    saved_files = analyzer.save_results(analysis_results)
                    
                    # Report results with detailed success/failure breakdown
                    successful_analyses = sum(1 for r in analysis_results if r.success)
                    failed_analyses = sum(1 for r in analysis_results if not r.success)
                    
                    print(f"✅ Step 2 Complete: {successful_analyses} AI analyses completed")
                    if failed_analyses > 0:
                        print(f"⚠️  {failed_analyses} AI analyses failed")
                        # Show which ones failed
                        for result in analysis_results:
                            if not result.success:
                                print(f"   ❌ {result.drawing_name}: {result.error_message}")
                    print(f"📁 Analysis files saved: {len(saved_files)}")
                    
            except Exception as e:
                print(f"⚠️  AI Analysis encountered an error: {e}")
                print("   Continuing with pipeline completion...")
                analysis_results = []
        else:
            print("\n⏭️  STEP 2: AI Analysis Skipped")
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
            'analysis_results': analysis_results,
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
        print("\n" + "=" * 80)
        print("🎉 PIPELINE COMPLETE!")
        print("=" * 80)
        print(f"⏱️  Total Time: {total_time:.1f} seconds")
        
        # Overlay summary
        successful_overlays = comparison_results['successful_overlays']
        failed_overlays = comparison_results.get('failed_overlays', 0)
        print(f"📊 Overlays: {successful_overlays} successful, {failed_overlays} failed")
        
        # AI Analysis summary
        if not skip_ai_analysis and analysis_results:
            try:
                successful_analyses = sum(1 for r in analysis_results if r.success)
                failed_analyses = sum(1 for r in analysis_results if not r.success)
                print(f"🤖 AI Analyses: {successful_analyses} successful, {failed_analyses} failed")
            except (AttributeError, TypeError):
                print(f"🤖 AI Analyses: {len(analysis_results)} completed")
        elif skip_ai_analysis:
            print("🤖 AI Analyses: Skipped")
        else:
            print("🤖 AI Analyses: None attempted")
            
        print(f"📁 Output Directory: {base_overlay_dir}/")
        
        # Overall success determination
        if successful_overlays > 0:
            print("✅ Pipeline Status: SUCCESS (overlays created)")
        else:
            print("⚠️  Pipeline Status: PARTIAL (no overlays created)")
        print("=" * 80)
        
        return pipeline_results
        
    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        
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


def main():
    """Command-line interface for the complete pipeline"""
    parser = argparse.ArgumentParser(
        description="Complete drawing comparison and analysis pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run complete pipeline
  python complete_drawing_pipeline.py old_drawings.pdf new_drawings.pdf
  
  # Run with custom settings
  python complete_drawing_pipeline.py old.pdf new.pdf --dpi 600 --debug
  
  # Skip AI analysis (overlays only)
  python complete_drawing_pipeline.py old.pdf new.pdf --skip-ai
        """
    )
    
    parser.add_argument("old_pdf", nargs="?", 
                       help="Path to old PDF file")
    parser.add_argument("new_pdf", nargs="?", 
                       help="Path to new PDF file")
    parser.add_argument("--dpi", type=int, default=300,
                       help="DPI for PDF conversion (default: 300)")
    parser.add_argument("--debug", action="store_true",
                       help="Enable debug mode for alignment process")
    parser.add_argument("--skip-ai", action="store_true",
                       help="Skip OpenAI analysis step")
    
    args = parser.parse_args()
    
    try:
        if args.old_pdf and args.new_pdf:
            old_pdf = args.old_pdf
            new_pdf = args.new_pdf
        else:
            parser.print_help()
            sys.exit(1)
        
        # Run the complete pipeline
        results = complete_drawing_pipeline(
            old_pdf_path=old_pdf,
            new_pdf_path=new_pdf,
            dpi=args.dpi,
            debug=args.debug,
            skip_ai_analysis=args.skip_ai
        )
        
        # Check if pipeline had any successful overlays
        successful_overlays = results.get('summary', {}).get('overlays_created', 0)
        if successful_overlays > 0:
            print("\n🎉 Pipeline completed with successful overlays!")
            sys.exit(0)
        else:
            print(f"\n⚠️  Pipeline completed but no overlays were created")
            if results.get('error'):
                print(f"   Error: {results['error']}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️  Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

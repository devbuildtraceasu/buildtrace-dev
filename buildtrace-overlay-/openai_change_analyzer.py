#!/usr/bin/env python3
"""
OpenAI Change Analyzer for Drawing Overlays

This module analyzes drawing overlay results using OpenAI's API to generate
comprehensive change lists for architectural modifications.

Usage:
    python openai_change_analyzer.py overlay_folder_path
    python openai_change_analyzer.py --test
"""

import os
import base64
import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import sys

try:
    from openai import OpenAI
    from dotenv import load_dotenv
except ImportError:
    print("Error: Required packages not installed. Run: pip install openai python-dotenv")
    sys.exit(1)

# Load environment variables from config.env file
load_dotenv('config.env')


@dataclass
class ChangeAnalysisResult:
    """Results from OpenAI change analysis"""
    drawing_name: str
    overlay_folder: str
    changes_found: List[str]
    critical_change: str
    analysis_summary: str
    recommendations: List[str]
    success: bool
    error_message: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'drawing_name': self.drawing_name,
            'overlay_folder': self.overlay_folder,
            'changes_found': self.changes_found,
            'critical_change': self.critical_change,
            'analysis_summary': self.analysis_summary,
            'recommendations': self.recommendations,
            'success': self.success,
            'error_message': self.error_message
        }


class OpenAIChangeAnalyzer:
    """Analyzes drawing overlays using OpenAI API to generate change lists"""
    
    def __init__(self, api_key: str = None, model: str = None):
        """
        Initialize the analyzer with OpenAI API key
        
        Args:
            api_key: OpenAI API key (if None, will try environment variable)
            model: OpenAI model to use (if None, will try environment variable, default: gpt-4o)
        """
        if api_key is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError(
                    "OpenAI API key not provided. Set it in config.env file or pass as parameter.\n"
                    "Example config.env:\n"
                    "OPENAI_API_KEY=your-api-key-here"
                )
        
        if model is None:
            model = os.getenv("OPENAI_MODEL", "gpt-4o")
        
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.system_prompt = """
You are an expert project manager at a general contractor company with access to document search and web research tools. 
Analyze the provided architectural drawings thoroughly and identify all changes between the old and new versions.
Focus on practical construction implications and cost impacts.
"""
    
    def _image_to_base64(self, image_path: str) -> str:
        """Convert PNG image to base64 string"""
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            raise ValueError(f"Failed to read image {image_path}: {e}")
    
    def _validate_overlay_folder(self, overlay_folder: str) -> Tuple[str, str, str]:
        """
        Validate that overlay folder contains required PNG files
        
        Args:
            overlay_folder: Path to overlay results folder
            
        Returns:
            Tuple of (old_png_path, new_png_path, overlay_png_path)
        """
        folder_path = Path(overlay_folder)
        if not folder_path.exists():
            raise FileNotFoundError(f"Overlay folder not found: {overlay_folder}")
        
        # Look for PNG files with expected naming pattern
        png_files = list(folder_path.glob("*.png"))
        
        old_png = None
        new_png = None
        overlay_png = None
        
        for png_file in png_files:
            filename = png_file.stem.lower()
            if "_old" in filename:
                old_png = str(png_file)
            elif "_new" in filename:
                new_png = str(png_file)
            elif "_overlay" in filename:
                overlay_png = str(png_file)
        
        if not old_png:
            raise FileNotFoundError(f"No '_old.png' file found in {overlay_folder}")
        if not new_png:
            raise FileNotFoundError(f"No '_new.png' file found in {overlay_folder}")
        if not overlay_png:
            raise FileNotFoundError(f"No '_overlay.png' file found in {overlay_folder}")
        
        return old_png, new_png, overlay_png
    
    def analyze_overlay_folder(self, overlay_folder: str) -> ChangeAnalysisResult:
        """
        Analyze a single overlay folder and generate change list
        
        Args:
            overlay_folder: Path to overlay results folder (e.g., "A-201_overlay_results")
            
        Returns:
            ChangeAnalysisResult with analysis details
        """
        try:
            # Extract drawing name from folder path
            drawing_name = Path(overlay_folder).stem.replace("_overlay_results", "")
            
            print(f"Analyzing {drawing_name} overlay folder...")
            
            # Validate and get PNG file paths
            old_png, new_png, overlay_png = self._validate_overlay_folder(overlay_folder)
            
            # Convert images to base64
            print("  Converting images to base64...")
            old_base64 = self._image_to_base64(old_png)
            new_base64 = self._image_to_base64(new_png)
            overlay_base64 = self._image_to_base64(overlay_png)
            
            print(f"  Image sizes - Old: {len(old_base64)}, New: {len(new_base64)}, Overlay: {len(overlay_base64)}")
            
            # Create analysis prompt
            analysis_prompt = f"""
Please analyze these three architectural drawings for drawing {drawing_name} and identify all changes:

1. BEFORE drawing - the original design
2. AFTER drawing - the updated design  
3. OVERLAY drawing - Red shows removed content (old only), green shows added content (new only), grey means no change

Please provide a detailed analysis including:
1. **Most Critical Change**: Identify the most significant change in terms of cost and construction impact
2. **Complete Change List**: Provide a numbered list of ALL changes found
3. **Change Format**: Use clear descriptions like "Room 101 extended by 10 feet from 200 to 300 sq ft"
4. **Construction Impact**: Assess implications for construction timeline and cost
5. **Recommendations**: Provide professional insights on construction implications

Format each change as: [Aspect] + [Action] + [Detail] + [Location/Reference]
"""
            
            # Call OpenAI API
            print("  Calling OpenAI API for analysis...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self.system_prompt
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": analysis_prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{old_base64}"
                                }
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{new_base64}"
                                }
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{overlay_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=2000,
                temperature=0.7
            )
            
            analysis_text = response.choices[0].message.content
            print(f"  Analysis completed ({len(analysis_text)} characters)")
            
            # Parse the response to extract structured information
            changes_found, critical_change, recommendations = self._parse_analysis_response(analysis_text)
            
            return ChangeAnalysisResult(
                drawing_name=drawing_name,
                overlay_folder=overlay_folder,
                changes_found=changes_found,
                critical_change=critical_change,
                analysis_summary=analysis_text,
                recommendations=recommendations,
                success=True
            )
            
        except Exception as e:
            print(f"  Error analyzing {overlay_folder}: {e}")
            return ChangeAnalysisResult(
                drawing_name=drawing_name if 'drawing_name' in locals() else "unknown",
                overlay_folder=overlay_folder,
                changes_found=[],
                critical_change="",
                analysis_summary="",
                recommendations=[],
                success=False,
                error_message=str(e)
            )
    
    def _parse_analysis_response(self, analysis_text: str) -> Tuple[List[str], str, List[str]]:
        """
        Parse OpenAI response to extract structured information
        
        Args:
            analysis_text: Raw analysis text from OpenAI
            
        Returns:
            Tuple of (changes_list, critical_change, recommendations)
        """
        changes_found = []
        critical_change = ""
        recommendations = []
        
        lines = analysis_text.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Detect sections
            if "critical change" in line.lower() or "most significant" in line.lower():
                current_section = "critical"
            elif "change list" in line.lower() or "changes found" in line.lower():
                current_section = "changes"
            elif "recommendation" in line.lower():
                current_section = "recommendations"
            
            # Extract numbered changes
            if line and (line[0].isdigit() or line.startswith("-") or line.startswith("*")):
                if current_section == "changes":
                    changes_found.append(line)
            
            # Extract critical change
            elif current_section == "critical" and line:
                critical_change = line
            
            # Extract recommendations
            elif current_section == "recommendations" and line:
                recommendations.append(line)
        
        return changes_found, critical_change, recommendations
    
    def analyze_multiple_overlays(self, base_overlay_dir: str) -> List[ChangeAnalysisResult]:
        """
        Analyze multiple overlay folders in a directory
        
        Args:
            base_overlay_dir: Base directory containing overlay result folders
            
        Returns:
            List of ChangeAnalysisResult objects
        """
        base_path = Path(base_overlay_dir)
        if not base_path.exists():
            raise FileNotFoundError(f"Base overlay directory not found: {base_overlay_dir}")
        
        # Find all overlay result folders
        overlay_folders = [f for f in base_path.iterdir() 
                          if f.is_dir() and "_overlay_results" in f.name]
        
        if not overlay_folders:
            raise FileNotFoundError(f"No overlay result folders found in {base_overlay_dir}")
        
        print(f"Found {len(overlay_folders)} overlay folders to analyze")
        
        results = []
        for overlay_folder in overlay_folders:
            result = self.analyze_overlay_folder(str(overlay_folder))
            results.append(result)
        
        return results
    
    def save_results(self, results: List[ChangeAnalysisResult], base_overlay_dir: str = None):
        """
        Save analysis results to JSON files in their respective overlay directories
        
        Args:
            results: List of ChangeAnalysisResult objects
            base_overlay_dir: Base directory containing overlay folders (optional)
        """
        saved_files = []
        
        for result in results:
            if not result.success:
                continue
                
            # Always save in the same directory as the overlay folder
            output_dir = Path(result.overlay_folder)
            
            # Create filename: change_analysis_A-101.json
            output_file = output_dir / f"change_analysis_{result.drawing_name}.json"
            
            # Prepare data for this specific drawing
            output_data = {
                "drawing_name": result.drawing_name,
                "overlay_folder": result.overlay_folder,
                "analysis_timestamp": result.analysis_summary[:100] + "..." if len(result.analysis_summary) > 100 else result.analysis_summary,
                "success": result.success,
                "changes_found": result.changes_found,
                "critical_change": result.critical_change,
                "recommendations": result.recommendations,
                "analysis_summary": result.analysis_summary
            }
            
            # Save the JSON file
            with open(output_file, 'w') as f:
                json.dump(output_data, f, indent=2)
            
            saved_files.append(str(output_file))
            print(f"  ✓ Saved analysis for {result.drawing_name} to {output_file}")
        
        # Also save a summary file if multiple results
        if len(results) > 1:
            # Save summary in the parent directory of the first overlay folder
            summary_file = Path(results[0].overlay_folder).parent / "change_analysis_summary.json"
            summary_data = {
                "summary": {
                    "total_analyzed": len(results),
                    "successful": sum(1 for r in results if r.success),
                    "failed": sum(1 for r in results if not r.success),
                    "base_directory": str(Path(results[0].overlay_folder).parent)
                },
                "individual_results": [
                    {
                        "drawing_name": r.drawing_name,
                        "overlay_folder": r.overlay_folder,
                        "success": r.success,
                        "changes_count": len(r.changes_found) if r.success else 0,
                        "json_file": f"change_analysis_{r.drawing_name}.json" if r.success else None
                    }
                    for r in results
                ]
            }
            
            with open(summary_file, 'w') as f:
                json.dump(summary_data, f, indent=2)
            
            saved_files.append(str(summary_file))
            print(f"  ✓ Saved summary to {summary_file}")
        
        return saved_files


def create_test_overlay_folder() -> str:
    """Create a test overlay folder for testing purposes"""
    test_folder = Path("test_overlay_results")
    test_folder.mkdir(exist_ok=True)
    
    # Create dummy PNG files (just empty files for testing structure)
    test_files = ["test_old.png", "test_new.png", "test_overlay.png"]
    for filename in test_files:
        file_path = test_folder / filename
        if not file_path.exists():
            # Create a minimal PNG file (1x1 pixel)
            with open(file_path, 'wb') as f:
                f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\nIDATx\x9cc```\x00\x00\x00\x04\x00\x01\xdd\x8d\xb4\x1c\x00\x00\x00\x00IEND\xaeB`\x82')
    
    print(f"Created test overlay folder: {test_folder}")
    return str(test_folder)


def main():
    """Command-line interface for the change analyzer"""
    parser = argparse.ArgumentParser(
        description="Analyze drawing overlays using OpenAI API to generate change lists",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze a single overlay folder
  python openai_change_analyzer.py A-201_overlay_results
  
  # Analyze all overlays in a directory
  python openai_change_analyzer.py test_new_overlays/
  
  # Test with dummy data
  python openai_change_analyzer.py --test
  
  # Use custom API key
  OPENAI_API_KEY=your_key python openai_change_analyzer.py overlay_folder
        """
    )
    
    parser.add_argument("overlay_path", nargs="?", 
                       help="Path to overlay folder or directory containing overlay folders")
    parser.add_argument("--test", action="store_true",
                       help="Run test with dummy data")
    parser.add_argument("--api-key", 
                       help="OpenAI API key (or set OPENAI_API_KEY environment variable)")
    parser.add_argument("--model", default="gpt-4o",
                       help="OpenAI model to use (default: gpt-4o)")
    parser.add_argument("--output", 
                       help="Base directory for saving individual JSON files (default: same as overlay directory)")
    
    args = parser.parse_args()
    
    try:
        # Initialize analyzer
        analyzer = OpenAIChangeAnalyzer(api_key=args.api_key, model=args.model)
        
        if args.test:
            # Test mode
            print("Running in test mode...")
            test_folder = create_test_overlay_folder()
            result = analyzer.analyze_overlay_folder(test_folder)
            print(f"\nTest result: {result}")
            
        elif args.overlay_path:
            overlay_path = Path(args.overlay_path)
            
            if overlay_path.is_file() or not overlay_path.exists():
                print(f"Error: {args.overlay_path} is not a valid directory")
                sys.exit(1)
            
            # Check if it's a single overlay folder or directory with multiple overlays
            if "_overlay_results" in overlay_path.name:
                # Single overlay folder
                print(f"Analyzing single overlay folder: {overlay_path}")
                result = analyzer.analyze_overlay_folder(str(overlay_path))
                results = [result]
            else:
                # Directory with multiple overlay folders
                print(f"Analyzing multiple overlay folders in: {overlay_path}")
                results = analyzer.analyze_multiple_overlays(str(overlay_path))
            
            # Print summary
            print("\n" + "="*60)
            print("ANALYSIS SUMMARY")
            print("="*60)
            
            successful = [r for r in results if r.success]
            failed = [r for r in results if not r.success]
            
            print(f"Total analyzed: {len(results)}")
            print(f"Successful: {len(successful)}")
            print(f"Failed: {len(failed)}")
            
            for result in successful:
                print(f"\n📋 {result.drawing_name}:")
                print(f"   Changes found: {len(result.changes_found)}")
                if result.critical_change:
                    print(f"   Critical change: {result.critical_change}")
            
            for result in failed:
                print(f"\n❌ {result.drawing_name}: {result.error_message}")
            
            # Save results in the overlay directory structure
            analyzer.save_results(results)
            
        else:
            parser.print_help()
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

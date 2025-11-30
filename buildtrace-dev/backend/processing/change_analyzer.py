"""
Change Analyzer for Drawing Overlays

This module analyzes drawing overlay results using Gemini API to generate
comprehensive change lists for architectural modifications.

Adapted from buildtrace-overlay- for buildtrace-dev with Gemini support
"""

import os
import base64
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from PIL import Image

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from config import config
from utils.local_output_manager import LocalOutputManager

logger = logging.getLogger(__name__)


@dataclass
class ChangeAnalysisResult:
    """Results from change analysis"""
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


class ChangeAnalyzer:
    """Analyzes drawing overlays using Gemini API to generate change lists"""
    
    def __init__(self, api_key: str = None, model: str = None):
        """
        Initialize the analyzer with Gemini API key
        
        Args:
            api_key: Gemini API key (if None, will try config/environment)
            model: Gemini model to use (if None, will try config/environment)
        """
        if not GEMINI_AVAILABLE:
            raise ImportError(
                "google-generativeai library not installed. "
                "Install with: pip install google-generativeai"
            )
        
        if api_key is None:
            api_key = os.getenv("GEMINI_API_KEY") or getattr(config, 'GEMINI_API_KEY', None)
            if not api_key:
                raise ValueError(
                    "GEMINI_API_KEY not provided. Set it in environment or config.\n"
                    "Example: export GEMINI_API_KEY=your-api-key-here"
                )
        
        if model is None:
            model = os.getenv("GEMINI_MODEL") or getattr(config, 'GEMINI_MODEL', 'models/gemini-2.5-pro')
        
        # Ensure model name has 'models/' prefix
        if not model.startswith('models/'):
            model = f'models/{model}'
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
        self.model_name = model
        
        self.system_prompt = """
You are an expert project manager at a general contractor company with access to document search and web research tools. 
Analyze the provided architectural drawings thoroughly and identify all changes between the old and new versions.
Focus on practical construction implications and cost impacts.

CRITICAL: When analyzing changes, identify the SPATIAL LOCATION of each change by describing bounding regions.
Think of the drawing as having distinct sections (like floor plans, legends, notes, schedules, title blocks) that can be 
bounded by rectangular regions. Changes may occur in:
- Main drawing area (floor plan, elevation, section views)
- Legend sections (material legends, symbol legends, finish schedules)
- Note sections (general notes, sheet notes, specifications)
- Title block area (project info, revision history)
- Detail callouts and sections

For each change, provide:
1. **Change Description**: Clear description of what changed
2. **Spatial Location**: Describe which section/region of the drawing (e.g., "Main floor plan - northwest quadrant", 
   "Finish legend - row 3", "General notes section - note #5", "Title block - revision history")
3. **Bounding Reference**: If possible, reference nearby elements to help locate the change (e.g., "near grid line A-3", 
   "adjacent to room 101", "in the flooring types legend between CPT-1 and STL-1")

Provide your analysis in a structured format:
1. **Most Critical Change**: Identify the most significant change in terms of cost and construction impact, including its location
2. **Complete Change List**: Provide a numbered list of ALL changes found, each with spatial location information
3. **Change Format**: Use clear descriptions like "Room 101 extended by 10 feet from 200 to 300 sq ft [Location: Main floor plan, 
   northwest quadrant, near grid intersection A-3]"
4. **Construction Impact**: Assess implications for construction timeline and cost
5. **Recommendations**: Provide professional insights on construction implications

Format each change as: [Aspect] + [Action] + [Detail] + [Location/Reference] + [Spatial Region]
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
    
    def analyze_overlay_folder(
        self, 
        overlay_folder: str,
        output_manager: Optional[LocalOutputManager] = None
    ) -> ChangeAnalysisResult:
        """
        Analyze a single overlay folder and generate change list
        
        Args:
            overlay_folder: Path to overlay results folder (e.g., "A-201_overlay_results")
            output_manager: Optional LocalOutputManager for saving files
            
        Returns:
            ChangeAnalysisResult with analysis details
        """
        try:
            # Extract drawing name from folder path
            drawing_name = Path(overlay_folder).stem.replace("_overlay_results", "")
            
            logger.info(f"Analyzing {drawing_name} overlay folder...")
            
            # Validate and get PNG file paths
            old_png, new_png, overlay_png = self._validate_overlay_folder(overlay_folder)
            
            # Load images for Gemini (Gemini accepts PIL Images or file paths)
            old_img = Image.open(old_png)
            new_img = Image.open(new_png)
            overlay_img = Image.open(overlay_png)
            
            logger.info(f"Loaded images: {old_png}, {new_png}, {overlay_png}")
            
            # Create enhanced analysis prompt with bounding box guidance
            analysis_prompt = f"""
Please analyze these three architectural drawings for drawing {drawing_name} and identify all changes with spatial precision:

1. BEFORE drawing - the original design
2. AFTER drawing - the updated design  
3. OVERLAY drawing - Red shows removed content (old only), green shows added content (new only), grey means no change

ANALYSIS APPROACH:
Think of the drawing as having distinct bounded regions, similar to how architectural drawings are organized:
- **Main Drawing Area**: The primary floor plan, elevation, or section view (typically the largest central area)
- **Legend Sections**: Material legends, finish schedules, symbol legends (typically in side panels or corners)
- **Note Sections**: General notes, sheet notes, specifications (typically in side panels or bottom)
- **Title Block**: Project information, revision history, sheet identification (typically bottom-right corner)
- **Detail Callouts**: Enlarged details, sections, or special views (may be in side panels or separate areas)

For each change you identify:

1. **Locate the Change Region**: Identify which bounded section contains the change
   - Is it in the main drawing area? Which quadrant or region?
   - Is it in a legend? Which row or entry?
   - Is it in a note section? Which note number or item?
   - Is it in the title block? Which field or section?

2. **Describe Spatial Context**: Provide spatial references to help locate the change
   - Reference nearby room numbers, grid lines, or labels
   - Reference adjacent elements in legends or schedules
   - Use directional references (northwest, southeast, etc.) for main drawing areas
   - Reference note numbers or schedule rows for text-based sections

3. **Identify Change Type**: Categorize the change
   - **Geometric Change**: Room size, wall position, door/window location changes
   - **Material/Finish Change**: Finish type, material specification changes
   - **Text/Annotation Change**: Note modifications, specification updates, revision changes
   - **Legend/Schedule Change**: New entries, removed entries, modified entries in legends or schedules
   - **Title Block Change**: Revision updates, date changes, sheet number changes

Please provide a detailed analysis including:
1. **Most Critical Change**: Identify the most significant change in terms of cost and construction impact, including:
   - Exact description of the change
   - Spatial location (which bounded region and specific area)
   - Nearby reference elements for precise location

2. **Complete Change List**: Provide a numbered list of ALL changes found, each with:
   - Change description
   - Spatial location (bounded region + specific area)
   - Change type (geometric/material/text/legend/title block)
   - Nearby reference elements

3. **Change Format Example**: 
   "1. [Geometric Change] Room 101 extended by 10 feet from 200 to 300 sq ft [Location: Main floor plan, northwest quadrant, 
   near grid intersection A-3, adjacent to corridor]"

4. **Construction Impact**: Assess implications for construction timeline and cost, organized by:
   - Structural impact
   - MEP (mechanical/electrical/plumbing) impact
   - Finish/material impact
   - Schedule/timeline impact
   - Cost impact (if estimable)

5. **Recommendations**: Provide professional insights on construction implications, prioritized by:
   - Critical actions required
   - Coordination needs
   - Potential issues or risks
   - Best practices for implementation

Format each change as: [Change Type] + [Aspect] + [Action] + [Detail] + [Spatial Location] + [Reference Elements]
"""
            
            # Call Gemini API with images
            logger.info("Calling Gemini API for analysis...")
            response = self.model.generate_content(
                [
                    self.system_prompt,
                    analysis_prompt,
                    old_img,
                    new_img,
                    overlay_img
                ],
                generation_config={
                    'max_output_tokens': 4000,
                    'temperature': 0.7,
                }
            )
            
            analysis_text = response.text
            logger.info(f"Analysis completed ({len(analysis_text)} characters)")
            
            # Parse the response to extract structured information
            changes_found, critical_change, recommendations = self._parse_analysis_response(analysis_text)
            
            result = ChangeAnalysisResult(
                drawing_name=drawing_name,
                overlay_folder=overlay_folder,
                changes_found=changes_found,
                critical_change=critical_change,
                analysis_summary=analysis_text,
                recommendations=recommendations,
                success=True
            )
            
            # Save to output manager if provided
            if output_manager:
                try:
                    result_dict = result.to_dict()
                    output_manager.save_json(
                        result_dict,
                        f"change_analysis_{drawing_name}.json"
                    )
                except Exception as e:
                    logger.warning(f"Failed to save to output manager: {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing {overlay_folder}: {e}", exc_info=True)
            drawing_name = Path(overlay_folder).stem.replace("_overlay_results", "") if 'overlay_folder' in locals() else "unknown"
            return ChangeAnalysisResult(
                drawing_name=drawing_name,
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
        Parse Gemini response to extract structured information
        
        Args:
            analysis_text: Raw analysis text from Gemini
            
        Returns:
            Tuple of (changes_list, critical_change, recommendations)
        """
        changes_found = []
        critical_change = ""
        recommendations = []
        
        lines = analysis_text.split('\n')
        current_section = None
        critical_section_active = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Detect sections (more flexible matching)
            line_lower = line.lower()
            if "critical change" in line_lower or "most significant" in line_lower or "most critical" in line_lower:
                current_section = "critical"
                critical_section_active = True
                continue
            elif "change list" in line_lower or "changes found" in line_lower or "changes:" in line_lower or "complete change" in line_lower:
                current_section = "changes"
                critical_section_active = False
                continue
            elif "recommendation" in line_lower or "recommendations:" in line_lower:
                current_section = "recommendations"
                critical_section_active = False
                continue
            elif "construction impact" in line_lower or "impact:" in line_lower:
                # Don't treat impact section as recommendations
                if current_section != "recommendations":
                    current_section = None
                continue
            
            # Extract numbered/bulleted entries
            if line and (line[0].isdigit() or line.startswith("-") or line.startswith("*") or line.startswith("•")):
                clean_line = line.lstrip("0123456789.-*•) ").strip()
                for prefix in ["[", "(", "-", "*", "•"]:
                    if clean_line.startswith(prefix):
                        clean_line = clean_line[1:].strip()

                if clean_line and len(clean_line) > 10:
                    if current_section == "changes":
                        changes_found.append(clean_line)
                        continue
                    if current_section == "recommendations":
                        recommendations.append(clean_line)
                        continue
            
            # Extract critical change (collect multi-line if needed)
            elif current_section == "critical" or critical_section_active:
                # Skip section headers
                if "critical" not in line_lower and len(line) > 15:
                    if critical_change:
                        critical_change += " " + line
                    else:
                        critical_change = line
                    critical_section_active = True
            
        
        # Clean up critical change
        if critical_change:
            critical_change = critical_change.strip()
        
        return changes_found, critical_change, recommendations
    
    def analyze_multiple_overlays(
        self, 
        base_overlay_dir: str,
        output_manager: Optional[LocalOutputManager] = None
    ) -> List[ChangeAnalysisResult]:
        """
        Analyze multiple overlay folders in a directory
        
        Args:
            base_overlay_dir: Base directory containing overlay result folders
            output_manager: Optional LocalOutputManager for saving files
            
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
        
        logger.info(f"Found {len(overlay_folders)} overlay folders to analyze")
        
        results = []
        for overlay_folder in overlay_folders:
            result = self.analyze_overlay_folder(str(overlay_folder), output_manager)
            results.append(result)
        
        return results
    
    def save_results(
        self, 
        results: List[ChangeAnalysisResult], 
        base_overlay_dir: str = None,
        output_manager: Optional[LocalOutputManager] = None
    ):
        """
        Save analysis results to JSON files in their respective overlay directories
        
        Args:
            results: List of ChangeAnalysisResult objects
            base_overlay_dir: Base directory containing overlay folders (optional)
            output_manager: Optional LocalOutputManager for saving files
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
            logger.info(f"Saved analysis for {result.drawing_name} to {output_file}")
            
            # Also save to output manager if provided
            if output_manager:
                try:
                    output_manager.save_json(output_data, f"change_analysis_{result.drawing_name}.json")
                except Exception as e:
                    logger.warning(f"Failed to save to output manager: {e}")
        
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
            logger.info(f"Saved summary to {summary_file}")
            
            # Also save summary to output manager if provided
            if output_manager:
                try:
                    output_manager.save_json(summary_data, "change_analysis_summary.json")
                except Exception as e:
                    logger.warning(f"Failed to save summary to output manager: {e}")
        
        return saved_files

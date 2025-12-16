#!/usr/bin/env python3
"""
ATTEMPT-1: Advanced Captioning Pipeline
Following captioning.txt steps 18-28

Steps:
1. Upload 1 drawing, segment it: legend, drawing, and two segments (right side)
2. Convert 4 quadrants and caption with support of separated legend
3. Synthesize quadrant captions + full drawing image for detailed drawing info (grid level)
4. Full drawing caption newly synthesized with detailed quadrant level info
5. Perform search and retrieval on this

All using Gemini 3-pro-preview for captioning and API calls.
"""

import argparse
import base64
import io
import json
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from pdf2image import convert_from_path
    import PIL.Image
    PIL.Image.MAX_IMAGE_PIXELS = 200_000_000
except ImportError:
    print("ERROR: Install pdf2image and Pillow: pip install pdf2image pillow")
    sys.exit(1)

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


# Configuration
GEMINI_MODEL = "gemini-3-pro-preview"
GEMINI_CAPTION_MODEL = "gemini-3-pro-preview"
GPT_MODEL = "gpt-5.2-2025-12-11"


@dataclass
class Region:
    region_id: str
    bbox: Tuple[float, float, float, float]  # [x_min, y_min, x_max, y_max] normalized
    description: str = ""


def clamp_bbox(bbox: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
    """Clamp normalized bbox to [0,1]"""
    x0, y0, x1, y1 = bbox
    x0, y0 = max(0.0, x0), max(0.0, y0)
    x1, y1 = min(1.0, x1), min(1.0, y1)
    if x1 <= x0 or y1 <= y0:
        raise ValueError(f"Invalid bbox: {bbox}")
    return x0, y0, x1, y1


def convert_to_image(input_path: Path, page_num: int, dpi: int, output_dir: Path) -> Path:
    """Convert PDF or image file to PNG"""
    # Check if it's already an image
    if input_path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.tif']:
        print(f"[Image] Using existing image: {input_path}")
        # Copy/convert to PNG if needed
        with PIL.Image.open(input_path) as img:
            img_path = output_dir / f"page_{page_num + 1}.png"
            # Convert to RGB if necessary (for PNG/JPG compatibility)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img.save(img_path, "PNG")
            print(f"[Image] Saved: {img_path}")
            return img_path
    else:
        # It's a PDF, convert it
        print(f"[PDF] Converting page {page_num + 1} at {dpi} dpi...")
        images = convert_from_path(str(input_path), dpi=dpi, first_page=page_num + 1, last_page=page_num + 1)
        if not images:
            raise RuntimeError("No pages found in PDF")
        img_path = output_dir / f"page_{page_num + 1}.png"
        images[0].save(img_path, "PNG")
        print(f"[PDF] Saved: {img_path}")
        return img_path


def crop_image(image_path: Path, bbox: Tuple[float, float, float, float], output_dir: Path, suffix: str) -> Path:
    """Crop image region based on normalized bbox"""
    with PIL.Image.open(image_path) as img:
        w, h = img.size
        x0, y0, x1, y1 = bbox
        crop_box = (int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h))
        cropped = img.crop(crop_box)
        out_path = output_dir / f"{image_path.stem}_{suffix}.png"
        cropped.save(out_path, "PNG")
        print(f"[CROP] {suffix}: {cropped.size} -> {out_path}")
        return out_path


class GeminiCaptioner:
    """Caption generation using Gemini 3-pro-preview"""
    
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(GEMINI_MODEL)
        print(f"[Gemini] Using model: {GEMINI_MODEL}")
    
    def caption_region(
        self,
        image_path: Path,
        region: Region,
        legend_context: Optional[str] = None,
        drawing_name: str = "",
        page_num: int = 1,
        is_legend: bool = False
    ) -> str:
        """Generate caption for a region with optional legend context"""
        
        # Read image
        image_data = image_path.read_bytes()
        
        # Build prompt
        if is_legend:
            # Special prompt for legend extraction
            prompt_text = f"""You are extracting the LEGEND/SYMBOL KEY from architectural drawing: {drawing_name}, page {page_num}.
Region: {region.region_id} ({region.description})

Extract ALL symbols, keynotes, and their meanings from this legend.

This legend will be used to interpret symbols throughout the drawing, so be EXHAUSTIVE:
- List every symbol, icon, line type, and their meanings
- Include all keynote numbers and their descriptions
- Note any abbreviations and their full meanings
- Include material symbols, finish symbols, equipment symbols
- Document any special notation or conventions
- Be precise - this will be used for symbol interpretation in other regions

Return a comprehensive legend/symbol key that can be used to decode all symbols in the drawing."""
        else:
            # Build caption prompt
            prompt_text = f"""You are analyzing architectural drawing: {drawing_name}, page {page_num}.
Region: {region.region_id} ({region.description})
"""
            
            if legend_context:
                prompt_text += f"""
LEGEND CONTEXT (CRITICAL - use this to interpret ALL symbols and annotations):
{legend_context}
"""
            
            prompt_text += """
Provide an EXHAUSTIVE, retrieval-ready caption for this architectural drawing region.

This caption will substitute for the image in retrieval, so be extremely detailed and comprehensive.

Include:
- ALL rooms, spaces, and their numbers/names with precise locations
- ALL doors, windows, and their types (swing direction, size, type)
- ALL grid lines and grid intersections (e.g., "Grid A1", "Grid B2", "between Grid A-B")
- ALL annotations, dimensions, notes, labels, and callouts
- ALL symbols, keynotes, and their meanings (use legend context if provided)
- Spatial relationships: adjacencies, connections, flow paths
- Visible text: labels, notes, revisions, sheet numbers, project info
- Title block information (if visible in this region)
- Legend/schedule information (if visible)
- Material specifications, finishes, construction details

CRITICAL: Focus on grid-level precision. Every component should be mapped to grid locations.
Example: "Room 101 (Office) located at Grid A1-B2, with door to corridor at Grid A1.5"

Be exhaustive - this caption will be used for search and retrieval, so include every detail visible."""
        
        try:
            print(f"  [Caption] Generating caption for {region.region_id}...")
            
            # Adjust max tokens based on region type
            # Gemini 3 Pro supports up to 65,536 output tokens
            # Using maximum 65,536 for all regions to avoid token limit errors
            max_tokens = 65536
            
            # Logging: Image info
            with PIL.Image.open(image_path) as img:
                img_width, img_height = img.size
            img_size_mb = len(image_data) / (1024 * 1024)
            prompt_chars = len(prompt_text)
            prompt_tokens_est = int(prompt_chars / 4)  # Rough estimate
            
            print(f"  [Log] Image: {img_width}x{img_height}px, {img_size_mb:.2f}MB")
            print(f"  [Log] Prompt: {prompt_chars} chars (~{prompt_tokens_est} tokens)")
            print(f"  [Log] Region type: {'LEGEND' if is_legend else 'QUADRANT'}")
            print(f"  [Log] Max output tokens: {max_tokens}")
            
            # Warn if image is very large
            if img_size_mb > 10:
                print(f"  [Log] ⚠️  WARNING: Large image ({img_size_mb:.2f}MB) - may cause token issues")
            if is_legend and img_size_mb > 5:
                print(f"  [Log] ⚠️  WARNING: Large legend image - consider resizing")
            
            response = self.model.generate_content(
                [prompt_text, {"mime_type": "image/png", "data": image_data}],
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=max_tokens,
                ),
                safety_settings=[
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                ],
            )
            
            # Check response properly
            print(f"  [Log] Response received")
            
            if not response.candidates:
                print(f"  [Log] ❌ No candidates in response")
                return "[ERROR: No candidates in response]"
            
            candidate = response.candidates[0]
            finish_reason = candidate.finish_reason
            
            # Map finish reasons to human-readable
            finish_reason_map = {
                0: "STOP (normal completion)",
                1: "MAX_TOKENS (hit token limit)",
                2: "SAFETY (blocked by safety filters)",
                3: "RECITATION (content policy violation)",
                4: "OTHER"
            }
            finish_reason_str = finish_reason_map.get(finish_reason, f"UNKNOWN ({finish_reason})")
            print(f"  [Log] Finish reason: {finish_reason} ({finish_reason_str})")
            
            # Log candidate details
            if hasattr(candidate, 'content'):
                print(f"  [Log] Candidate.content exists: {candidate.content is not None}")
                if candidate.content and hasattr(candidate.content, 'parts'):
                    parts_count = len(candidate.content.parts) if candidate.content.parts else 0
                    print(f"  [Log] Content.parts count: {parts_count}")
            
            # Handle different finish reasons
            if finish_reason == 1:  # MAX_TOKENS
                print(f"  [Caption] ⚠️  Hit token limit (finish_reason=1)")
                print(f"  [Log] POSSIBLE REASONS:")
                print(f"    1. Image too large ({img_size_mb:.2f}MB, {img_width}x{img_height}px)")
                print(f"    2. Max tokens too low ({max_tokens}) - Gemini 3 Pro supports up to 65,536")
                print(f"    3. Legend very dense with symbols")
                print(f"    4. Response cut off before any content generated")
                print(f"  [Log] Attempting to extract available text...")
            
            # Try to get text from response
            caption = None
            try:
                caption = response.text.strip()
                print(f"  [Log] ✓ Extracted via response.text ({len(caption)} chars)")
            except (ValueError, AttributeError) as e:
                print(f"  [Log] ⚠️  response.text failed: {e}")
                # Fallback: try to extract from parts
                if hasattr(candidate, 'content') and candidate.content:
                    if hasattr(candidate.content, 'parts') and candidate.content.parts:
                        print(f"  [Log] Attempting fallback extraction from parts...")
                        text_parts = []
                        for i, part in enumerate(candidate.content.parts):
                            if hasattr(part, 'text') and part.text:
                                text_parts.append(part.text)
                                print(f"  [Log]   Part {i}: extracted {len(part.text)} chars")
                            else:
                                print(f"  [Log]   Part {i}: no text (has_text={hasattr(part, 'text')})")
                        if text_parts:
                            caption = "\n".join(text_parts).strip()
                            print(f"  [Log] ✓ Extracted {len(text_parts)} parts ({len(caption)} chars total)")
                        else:
                            print(f"  [Log] ❌ No text found in any parts")
                            return f"[ERROR: No text in response parts. Finish reason: {finish_reason} ({finish_reason_str})]"
                    else:
                        print(f"  [Log] ❌ No parts in candidate.content")
                        return f"[ERROR: No parts in response. Finish reason: {finish_reason} ({finish_reason_str})]"
                else:
                    print(f"  [Log] ❌ No content in candidate")
                    print(f"  [Log] Candidate attributes: {[x for x in dir(candidate) if not x.startswith('_')]}")
                    if hasattr(candidate, 'safety_ratings'):
                        print(f"  [Log] Safety ratings: {candidate.safety_ratings}")
                    return f"[ERROR: No content in candidate. Finish reason: {finish_reason} ({finish_reason_str})]"
            
            if not caption or len(caption) == 0:
                print(f"  [Log] ❌ Caption is empty after extraction")
                return f"[ERROR: Empty caption. Finish reason: {finish_reason} ({finish_reason_str})]"
            
            print(f"  [Caption] ✓ Generated {len(caption)} chars for {region.region_id} (finish_reason={finish_reason})")
            if finish_reason == 1:
                print(f"  [Log] ⚠️  WARNING: Response was truncated! Consider:")
                print(f"    - Increasing max_output_tokens (current: {max_tokens}, max: 65,536)")
                print(f"    - Resizing image (current: {img_width}x{img_height}px, {img_size_mb:.2f}MB)")
                print(f"    - Simplifying prompt for legend")
            return caption
            
        except Exception as e:
            print(f"  [Caption] ❌ Failed for {region.region_id}: {e}")
            import traceback
            traceback.print_exc()
            return f"[ERROR: Caption generation failed: {e}]"
    
    def synthesize_quadrants(
        self,
        quadrant_captions: Dict[str, str],
        full_drawing_image_path: Path,
        legend_caption: str,
        drawing_name: str
    ) -> str:
        """
        Step 3: CRITICAL SYNTHESIS STEP
        Synthesize quadrant captions + full drawing for detailed grid-level info.
        This is the KEY step that creates the knowledge base with grid-level precision.
        """
        
        image_data = full_drawing_image_path.read_bytes()
        
        # Build synthesis prompt - THIS IS CRITICAL
        quadrant_text = "\n\n".join([
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"QUADRANT {qid.upper().replace('_', ' ')}:\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{caption}\n"
            for qid, caption in quadrant_captions.items()
        ])
        
        prompt = f"""You are an expert architect performing CRITICAL knowledge synthesis for architectural drawings.

Your task is to create a COMPREHENSIVE, grid-level knowledge base by combining quadrant captions with the full drawing image.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DRAWING: {drawing_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

LEGEND CONTEXT (use for symbol interpretation):
{legend_caption}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUADRANT CAPTIONS (detailed regional information):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{quadrant_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FULL DRAWING IMAGE: (provided below - use this to verify and enhance)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CRITICAL SYNTHESIS TASK:

Analyze the full drawing image and synthesize ALL quadrant information into a unified, grid-level knowledge base.

REQUIREMENTS (THIS IS CRITICAL - FOLLOW EXACTLY):

1. GRID-LEVEL PRECISION (MOST IMPORTANT):
   - Extract grid-level information for EVERY component
   - Map each room/space to its grid coordinates (e.g., "Room 101 spans Grid A1-B2")
   - Map each door/window to grid intersections (e.g., "Door D-101 at Grid A1.5")
   - Map all annotations to grid positions
   - Identify grid system structure (e.g., "Grid lines A, B, C run vertically; 1, 2, 3 run horizontally")

2. COMPONENT INVENTORY WITH LOCATIONS:
   - List ALL rooms/spaces with their grid locations
   - List ALL doors with grid positions and types
   - List ALL windows with grid positions and types
   - List ALL annotations, dimensions, notes with grid references
   - List ALL symbols/keynotes with grid locations

3. SPATIAL RELATIONSHIPS:
   - Identify adjacencies between spaces across quadrants
   - Map connections (doors, corridors) between regions
   - Describe flow paths and circulation
   - Note spatial hierarchies and relationships

4. AGGREGATION AND DEDUPLICATION:
   - Combine information from all quadrants
   - Resolve any conflicts or inconsistencies
   - Create unified understanding of the entire drawing
   - Ensure no information is lost in synthesis

5. STRUCTURED OUTPUT FORMAT:
   Organize your synthesis as follows:

   GRID SYSTEM:
   [Describe the grid system structure, line labels, orientation]

   ROOMS/SPACES (with grid locations):
   [List each room with: name/number, grid location, type, adjacencies]

   DOORS (with grid locations):
   [List each door with: identifier, grid position, type, connects spaces]

   WINDOWS (with grid locations):
   [List each window with: identifier, grid position, type, room]

   ANNOTATIONS (with grid locations):
   [List annotations, dimensions, notes with grid references]

   SPATIAL RELATIONSHIPS:
   [Describe adjacencies, connections, flow paths]

   SUMMARY COUNTS:
   [Total rooms, doors, windows, annotations by type]

6. REASONING AND SOURCE CITATIONS (CRITICAL):
   After your synthesis, include a section explaining:
   - Your reasoning process: How you combined information from quadrants
   - Source citations: Which quadrant(s) each piece of information came from
   - Verification: How you verified information against the full drawing image
   - Conflicts resolved: Any inconsistencies found and how you resolved them
   - Confidence levels: Your confidence in different pieces of information

   Format as:
   
   REASONING AND SOURCES:
   [Explain your synthesis process]
   - Information from Q1: [what you extracted]
   - Information from Q2: [what you extracted]
   - Information from Q3: [what you extracted]
   - Information from Q4: [what you extracted]
   - Full image verification: [what you verified]
   - Conflicts resolved: [any inconsistencies and resolutions]
   - Confidence assessment: [confidence levels for different components]

Return a comprehensive, structured synthesis that provides grid-level detail for EVERY component.
This synthesis will be the foundation for search and retrieval, so completeness and precision are critical.
INCLUDE your reasoning and source citations so the process can be verified."""
        
        try:
            print(f"[Synthesis] Combining quadrants + full drawing for grid-level info...")
            response = self.model.generate_content(
                [prompt, {"mime_type": "image/png", "data": image_data}],
                generation_config=genai.types.GenerationConfig(
                    temperature=0.0,  # Lower temperature for more precise synthesis
                    max_output_tokens=65536,  # Maximum tokens for comprehensive synthesis with reasoning
                ),
                safety_settings=[
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                ],
            )
            
            # Check response properly
            if not response.candidates:
                return "[ERROR: No candidates in synthesis response]"
            
            candidate = response.candidates[0]
            finish_reason = candidate.finish_reason
            
            try:
                synthesis = response.text.strip()
            except (ValueError, AttributeError):
                # Fallback extraction
                if hasattr(candidate, 'content') and candidate.content:
                    if hasattr(candidate.content, 'parts') and candidate.content.parts:
                        text_parts = [part.text for part in candidate.content.parts if hasattr(part, 'text') and part.text]
                        synthesis = "\n".join(text_parts).strip() if text_parts else f"[ERROR: No text. Finish reason: {finish_reason}]"
                    else:
                        synthesis = f"[ERROR: No parts. Finish reason: {finish_reason}]"
                else:
                    synthesis = f"[ERROR: No content. Finish reason: {finish_reason}]"
            
            print(f"[Synthesis] ✓ Generated {len(synthesis)} chars (finish_reason={finish_reason})")
            return synthesis
        except Exception as e:
            print(f"[Synthesis] ❌ Failed: {e}")
            import traceback
            traceback.print_exc()
            return f"[ERROR: Synthesis failed: {e}]"
    
    def synthesize_final_caption(
        self,
        quadrant_synthesis: str,
        quadrant_captions: Dict[str, str],
        full_drawing_image_path: Path,
        drawing_name: str
    ) -> str:
        """Step 4: Final full drawing caption with detailed quadrant-level info"""
        
        image_data = full_drawing_image_path.read_bytes()
        
        quadrant_summary = "\n\n".join([
            f"QUADRANT {qid.upper()}:\n{caption[:1000]}..." if len(caption) > 1000 else f"QUADRANT {qid.upper()}:\n{caption}"
            for qid, caption in quadrant_captions.items()
        ])
        
        prompt = f"""You are creating the FINAL, definitive caption for architectural drawing: {drawing_name}.

This is the ULTIMATE synthesis that combines all information into a single, retrieval-optimized caption.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUADRANT-LEVEL SYNTHESIS (grid-level knowledge base):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{quadrant_synthesis}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUADRANT CAPTIONS (detailed regional information):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{quadrant_summary}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FULL DRAWING IMAGE: (provided below - use for verification)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CRITICAL FINAL SYNTHESIS TASK:

Create a NEW, comprehensive full-drawing caption that is the definitive knowledge base for this drawing.

REQUIREMENTS:

1. INCORPORATE ALL INFORMATION:
   - Integrate ALL grid-level details from quadrant synthesis
   - Include ALL detailed information from quadrant captions
   - Verify against full drawing image
   - Ensure nothing is lost or omitted

2. GRID-LEVEL PRECISION (MANDATORY):
   - Every component MUST have grid location
   - Use format: "Component at Grid X-Y" or "Component spans Grid A1-B2"
   - Maintain all grid references from synthesis

3. RETRIEVAL OPTIMIZATION:
   - Structure for search and retrieval
   - Use clear, descriptive language
   - Include synonyms and alternative terms
   - Make it easy to find specific components

4. COMPREHENSIVE COVERAGE:
   - All rooms/spaces with grid locations
   - All doors/windows with grid positions
   - All annotations with grid references
   - All spatial relationships
   - All symbols and keynotes
   - Complete inventory and counts

5. UNIFIED DESCRIPTION:
   - Single, coherent narrative
   - Logical organization (by area, by type, by grid)
   - Clear spatial relationships
   - Professional architectural terminology

OUTPUT FORMAT:

Create a comprehensive caption organized as:

[Title/Overview of drawing]

GRID SYSTEM:
[Grid structure description]

SPACES AND ROOMS:
[Complete inventory with grid locations]

DOORS AND OPENINGS:
[Complete inventory with grid positions]

WINDOWS:
[Complete inventory with grid positions]

ANNOTATIONS AND NOTES:
[All annotations with grid references]

SPATIAL RELATIONSHIPS:
[Adjacencies, connections, flow]

SUMMARY:
[Total counts, key features, important notes]

REASONING AND SOURCE CITATIONS:
[Explain your synthesis process]
- Sources used: quadrant_synthesis, quadrant_captions, full_drawing_image
- Reasoning: How you integrated information from different sources
- Verification: How you verified against the full drawing image
- Confidence: Confidence levels for different components
- Process: Step-by-step explanation of your synthesis approach

Return the final, definitive caption that serves as the complete knowledge base for this drawing.
This caption will be used for search and retrieval, so it must be exhaustive, precise, and well-structured.
INCLUDE your reasoning and source citations so the synthesis process can be verified."""
        
        try:
            print(f"[Final Synthesis] Creating final full-drawing caption...")
            response = self.model.generate_content(
                [prompt, {"mime_type": "image/png", "data": image_data}],
                generation_config=genai.types.GenerationConfig(
                    temperature=0.0,  # Lower temperature for more precise synthesis
                    max_output_tokens=65536,  # Maximum tokens for comprehensive synthesis with reasoning
                ),
                safety_settings=[
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                ],
            )
            
            # Check response properly
            if not response.candidates:
                return "[ERROR: No candidates in final synthesis response]"
            
            candidate = response.candidates[0]
            finish_reason = candidate.finish_reason
            
            try:
                final_caption = response.text.strip()
            except (ValueError, AttributeError):
                # Fallback extraction
                if hasattr(candidate, 'content') and candidate.content:
                    if hasattr(candidate.content, 'parts') and candidate.content.parts:
                        text_parts = [part.text for part in candidate.content.parts if hasattr(part, 'text') and part.text]
                        final_caption = "\n".join(text_parts).strip() if text_parts else f"[ERROR: No text. Finish reason: {finish_reason}]"
                    else:
                        final_caption = f"[ERROR: No parts. Finish reason: {finish_reason}]"
                else:
                    final_caption = f"[ERROR: No content. Finish reason: {finish_reason}]"
            
            print(f"[Final Synthesis] ✓ Generated {len(final_caption)} chars (finish_reason={finish_reason})")
            return final_caption
        except Exception as e:
            print(f"[Final Synthesis] ❌ Failed: {e}")
            import traceback
            traceback.print_exc()
            return f"[ERROR: Final synthesis failed: {e}]"


class GPTCaptioner:
    """Caption generation using GPT-5.2"""
    
    def __init__(self, api_key: str):
        if not OPENAI_AVAILABLE:
            print("ERROR: Install openai: pip install openai")
            sys.exit(1)
        self.client = OpenAI(api_key=api_key)
        self.model_name = GPT_MODEL
        print(f"[GPT] Using model: {GPT_MODEL}")
    
    def caption_region(
        self,
        image_path: Path,
        region: Region,
        legend_context: Optional[str] = None,
        drawing_name: str = "",
        page_num: int = 1,
        is_legend: bool = False
    ) -> str:
        """Generate caption for a region with optional legend context"""
        
        # Read and encode image
        try:
            with PIL.Image.open(image_path) as img:
                img_width, img_height = img.size
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                img_bytes = buf.getvalue()
                img_size_mb = len(img_bytes) / (1024 * 1024)
                b64 = base64.b64encode(img_bytes).decode("utf-8")
        except Exception as e:
            return f"[ERROR: Failed to load image: {e}]"
        
        # Build prompt
        if is_legend:
            prompt_text = f"""You are extracting the LEGEND/SYMBOL KEY from architectural drawing: {drawing_name}, page {page_num}.
Region: {region.region_id} ({region.description})

Extract ALL symbols, keynotes, and their meanings from this legend.

This legend will be used to interpret symbols throughout the drawing, so be EXHAUSTIVE:
- List every symbol, icon, line type, and their meanings
- Include all keynote numbers and their descriptions
- Note any abbreviations and their full meanings
- Include material symbols, finish symbols, equipment symbols
- Document any special notation or conventions
- Be precise - this will be used for symbol interpretation in other regions

Return a comprehensive legend/symbol key that can be used to decode all symbols in the drawing."""
        else:
            prompt_text = f"""You are analyzing architectural drawing: {drawing_name}, page {page_num}.
Region: {region.region_id} ({region.description})
"""
            if legend_context:
                prompt_text += f"""
LEGEND CONTEXT (CRITICAL - use this to interpret ALL symbols and annotations):
{legend_context}
"""
            prompt_text += """
Provide an EXHAUSTIVE, retrieval-ready caption for this architectural drawing region.

This caption will substitute for the image in retrieval, so be extremely detailed and comprehensive.

Include:
- ALL rooms, spaces, and their numbers/names with precise locations
- ALL doors, windows, and their types (swing direction, size, type)
- ALL grid lines and grid intersections (e.g., "Grid A1", "Grid B2", "between Grid A-B")
- ALL annotations, dimensions, notes, labels, and callouts
- ALL symbols, keynotes, and their meanings (use legend context if provided)
- Spatial relationships: adjacencies, connections, flow paths
- Visible text: labels, notes, revisions, sheet numbers, project info
- Title block information (if visible in this region)
- Legend/schedule information (if visible)
- Material specifications, finishes, construction details

CRITICAL: Focus on grid-level precision. Every component should be mapped to grid locations.
Example: "Room 101 (Office) located at Grid A1-B2, with door to corridor at Grid A1.5"

Be exhaustive - this caption will be used for search and retrieval, so include every detail visible."""
        
        try:
            print(f"  [Caption] Generating caption for {region.region_id}...")
            print(f"  [Log] Image: {img_width}x{img_height}px, {img_size_mb:.2f}MB")
            print(f"  [Log] Prompt: {len(prompt_text)} chars")
            print(f"  [Log] Region type: {'LEGEND' if is_legend else 'QUADRANT'}")
            print(f"  [Log] Max completion tokens: 65536")
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at describing architectural drawings with exhaustive detail for retrieval."
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt_text},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                        ],
                    },
                ],
                max_completion_tokens=65536,
            )
            
            caption = response.choices[0].message.content
            if not caption:
                return "[ERROR: Empty caption from GPT]"
            
            print(f"  [Caption] ✓ Generated {len(caption)} chars for {region.region_id}")
            return caption.strip()
            
        except Exception as e:
            print(f"  [Caption] ❌ Failed for {region.region_id}: {e}")
            import traceback
            traceback.print_exc()
            return f"[ERROR: Caption generation failed: {e}]"
    
    def synthesize_quadrants(
        self,
        quadrant_captions: Dict[str, str],
        full_drawing_image_path: Path,
        legend_caption: str,
        drawing_name: str
    ) -> str:
        """Step 3: CRITICAL SYNTHESIS STEP - GPT version"""
        
        # Read and encode image
        try:
            with PIL.Image.open(full_drawing_image_path) as img:
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                img_bytes = buf.getvalue()
                b64 = base64.b64encode(img_bytes).decode("utf-8")
        except Exception as e:
            return f"[ERROR: Failed to load image: {e}]"
        
        quadrant_text = "\n\n".join([
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"QUADRANT {qid.upper().replace('_', ' ')}:\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{caption}\n"
            for qid, caption in quadrant_captions.items()
        ])
        
        prompt = f"""You are an expert architect performing CRITICAL knowledge synthesis for architectural drawings.

Your task is to create a COMPREHENSIVE, grid-level knowledge base by combining quadrant captions with the full drawing image.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DRAWING: {drawing_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

LEGEND CONTEXT (use for symbol interpretation):
{legend_caption}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUADRANT CAPTIONS (detailed regional information):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{quadrant_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FULL DRAWING IMAGE: (provided below - use this to verify and enhance)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CRITICAL SYNTHESIS TASK:

Analyze the full drawing image and synthesize ALL quadrant information into a unified, grid-level knowledge base.

REQUIREMENTS (THIS IS CRITICAL - FOLLOW EXACTLY):

1. GRID-LEVEL PRECISION (MOST IMPORTANT):
   - Extract grid-level information for EVERY component
   - Map each room/space to its grid coordinates (e.g., "Room 101 spans Grid A1-B2")
   - Map each door/window to grid intersections (e.g., "Door D-101 at Grid A1.5")
   - Map all annotations to grid positions
   - Identify grid system structure (e.g., "Grid lines A, B, C run vertically; 1, 2, 3 run horizontally")

2. COMPONENT INVENTORY WITH LOCATIONS:
   - List ALL rooms/spaces with their grid locations
   - List ALL doors with grid positions and types
   - List ALL windows with grid positions and types
   - List ALL annotations, dimensions, notes with grid references
   - List ALL symbols/keynotes with grid locations

3. SPATIAL RELATIONSHIPS:
   - Identify adjacencies between spaces across quadrants
   - Map connections (doors, corridors) between regions
   - Describe flow paths and circulation
   - Note spatial hierarchies and relationships

4. AGGREGATION AND DEDUPLICATION:
   - Combine information from all quadrants
   - Resolve any conflicts or inconsistencies
   - Create unified understanding of the entire drawing
   - Ensure no information is lost in synthesis

5. STRUCTURED OUTPUT FORMAT:
   Organize your synthesis as follows:

   GRID SYSTEM:
   [Describe the grid system structure, line labels, orientation]

   ROOMS/SPACES (with grid locations):
   [List each room with: name/number, grid location, type, adjacencies]

   DOORS (with grid locations):
   [List each door with: identifier, grid position, type, connects spaces]

   WINDOWS (with grid locations):
   [List each window with: identifier, grid position, type, room]

   ANNOTATIONS (with grid locations):
   [List annotations, dimensions, notes with grid references]

   SPATIAL RELATIONSHIPS:
   [Describe adjacencies, connections, flow paths]

   SUMMARY COUNTS:
   [Total rooms, doors, windows, annotations by type]

6. REASONING AND SOURCE CITATIONS (CRITICAL):
   After your synthesis, include a section explaining:
   - Your reasoning process: How you combined information from quadrants
   - Source citations: Which quadrant(s) each piece of information came from
   - Verification: How you verified information against the full drawing image
   - Conflicts resolved: Any inconsistencies found and how you resolved them
   - Confidence levels: Your confidence in different pieces of information

   Format as:
   
   REASONING AND SOURCES:
   [Explain your synthesis process]
   - Information from Q1: [what you extracted]
   - Information from Q2: [what you extracted]
   - Information from Q3: [what you extracted]
   - Information from Q4: [what you extracted]
   - Full image verification: [what you verified]
   - Conflicts resolved: [any inconsistencies and resolutions]
   - Confidence assessment: [confidence levels for different components]

Return a comprehensive, structured synthesis that provides grid-level detail for EVERY component.
This synthesis will be the foundation for search and retrieval, so completeness and precision are critical.
INCLUDE your reasoning and source citations so the process can be verified."""
        
        try:
            print(f"[Synthesis] Combining quadrants + full drawing for grid-level info...")
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert architect performing critical knowledge synthesis for architectural drawings."
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                        ],
                    },
                ],
                max_completion_tokens=65536,
            )
            
            synthesis = response.choices[0].message.content
            if not synthesis:
                return "[ERROR: Empty synthesis from GPT]"
            
            print(f"[Synthesis] ✓ Generated {len(synthesis)} chars")
            return synthesis.strip()
            
        except Exception as e:
            print(f"[Synthesis] ❌ Failed: {e}")
            import traceback
            traceback.print_exc()
            return f"[ERROR: Synthesis failed: {e}]"
    
    def synthesize_final_caption(
        self,
        quadrant_synthesis: str,
        quadrant_captions: Dict[str, str],
        full_drawing_image_path: Path,
        drawing_name: str
    ) -> str:
        """Step 4: Final full drawing caption with detailed quadrant-level info - GPT version"""
        
        # Read and encode image
        try:
            with PIL.Image.open(full_drawing_image_path) as img:
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                img_bytes = buf.getvalue()
                b64 = base64.b64encode(img_bytes).decode("utf-8")
        except Exception as e:
            return f"[ERROR: Failed to load image: {e}]"
        
        quadrant_summary = "\n\n".join([
            f"QUADRANT {qid.upper()}:\n{caption[:1000]}..." if len(caption) > 1000 else f"QUADRANT {qid.upper()}:\n{caption}"
            for qid, caption in quadrant_captions.items()
        ])
        
        prompt = f"""You are creating the FINAL, definitive caption for architectural drawing: {drawing_name}.

This is the ULTIMATE synthesis that combines all information into a single, retrieval-optimized caption.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUADRANT-LEVEL SYNTHESIS (grid-level knowledge base):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{quadrant_synthesis}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUADRANT CAPTIONS (detailed regional information):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{quadrant_summary}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FULL DRAWING IMAGE: (provided below - use for verification)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CRITICAL FINAL SYNTHESIS TASK:

Create a NEW, comprehensive full-drawing caption that is the definitive knowledge base for this drawing.

REQUIREMENTS:

1. INCORPORATE ALL INFORMATION:
   - Integrate ALL grid-level details from quadrant synthesis
   - Include ALL detailed information from quadrant captions
   - Verify against full drawing image
   - Ensure nothing is lost or omitted

2. GRID-LEVEL PRECISION (MANDATORY):
   - Every component MUST have grid location
   - Use format: "Component at Grid X-Y" or "Component spans Grid A1-B2"
   - Maintain all grid references from synthesis

3. RETRIEVAL OPTIMIZATION:
   - Structure for search and retrieval
   - Use clear, descriptive language
   - Include synonyms and alternative terms
   - Make it easy to find specific components

4. COMPREHENSIVE COVERAGE:
   - All rooms/spaces with grid locations
   - All doors/windows with grid positions
   - All annotations with grid references
   - All spatial relationships
   - All symbols and keynotes
   - Complete inventory and counts

5. UNIFIED DESCRIPTION:
   - Single, coherent narrative
   - Logical organization (by area, by type, by grid)
   - Clear spatial relationships
   - Professional architectural terminology

OUTPUT FORMAT:

Create a comprehensive caption organized as:

[Title/Overview of drawing]

GRID SYSTEM:
[Grid structure description]

SPACES AND ROOMS:
[Complete inventory with grid locations]

DOORS AND OPENINGS:
[Complete inventory with grid positions]

WINDOWS:
[Complete inventory with grid positions]

ANNOTATIONS AND NOTES:
[All annotations with grid references]

SPATIAL RELATIONSHIPS:
[Adjacencies, connections, flow]

SUMMARY:
[Total counts, key features, important notes]

REASONING AND SOURCE CITATIONS:
[Explain your synthesis process]
- Sources used: quadrant_synthesis, quadrant_captions, full_drawing_image
- Reasoning: How you integrated information from different sources
- Verification: How you verified against the full drawing image
- Confidence: Confidence levels for different components
- Process: Step-by-step explanation of your synthesis approach

Return the final, definitive caption that serves as the complete knowledge base for this drawing.
This caption will be used for search and retrieval, so it must be exhaustive, precise, and well-structured.
INCLUDE your reasoning and source citations so the synthesis process can be verified."""
        
        try:
            print(f"[Final Synthesis] Creating final full-drawing caption...")
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert architect creating definitive captions for architectural drawings."
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                        ],
                    },
                ],
                max_completion_tokens=65536,
            )
            
            final_caption = response.choices[0].message.content
            if not final_caption:
                return "[ERROR: Empty final caption from GPT]"
            
            print(f"[Final Synthesis] ✓ Generated {len(final_caption)} chars")
            return final_caption.strip()
            
        except Exception as e:
            print(f"[Final Synthesis] ❌ Failed: {e}")
            import traceback
            traceback.print_exc()
            return f"[ERROR: Final synthesis failed: {e}]"


def segment_drawing(image_path: Path, tmp_dir: Path, output_base: Path) -> Dict[str, Path]:
    """
    Step 1: Segment drawing into 2 parts:
    - legend (right side)
    - drawing (main area, left side)
    Also saves images to output_base for analysis.
    """
    print("\n[Step 1] Segmenting drawing into 2 parts (legend + drawing)...")
    
    segments = {}
    
    # Heuristic segmentation (adjust based on typical drawing layout)
    # Legend: typically right side, 25% width
    legend_bbox = clamp_bbox((0.75, 0.0, 1.0, 1.0))  # Right 25%
    segments['legend'] = crop_image(image_path, legend_bbox, tmp_dir, "legend")
    
    # Main drawing: left 75% (this will be split into 4 quadrants later)
    drawing_bbox = clamp_bbox((0.0, 0.0, 0.75, 1.0))
    segments['drawing'] = crop_image(image_path, drawing_bbox, tmp_dir, "drawing")
    
    # Copy to output_base for analysis
    import shutil
    for key, tmp_path in segments.items():
        output_path = output_base / f"{key}.png"
        shutil.copy2(tmp_path, output_path)
        print(f"  [Save] Copied {key} to {output_path}")
    
    print(f"[Step 1] ✓ Segmented into 2 parts: legend and drawing")
    return segments


def create_quadrants(drawing_image_path: Path, tmp_dir: Path, output_base: Path) -> Dict[str, Path]:
    """
    Create 4 quadrants from the DRAWING area (not full page)
    The drawing area is already cropped (left 75% of original)
    Also saves images to output_base for analysis.
    """
    print("\n[Step 2] Creating 4 quadrants from drawing area...")
    
    # Since drawing_image_path is already the cropped drawing (0.0-0.75 width),
    # we split it into 4 equal quadrants
    quadrants = {
        'q1_top_left': clamp_bbox((0.0, 0.0, 0.5, 0.5)),
        'q2_top_right': clamp_bbox((0.5, 0.0, 1.0, 0.5)),
        'q3_bottom_left': clamp_bbox((0.0, 0.5, 0.5, 1.0)),
        'q4_bottom_right': clamp_bbox((0.5, 0.5, 1.0, 1.0)),
    }
    
    quadrant_paths = {}
    import shutil
    for qid, bbox in quadrants.items():
        quadrant_paths[qid] = crop_image(drawing_image_path, bbox, tmp_dir, qid)
        # Copy to output_base for analysis
        output_path = output_base / f"{qid}.png"
        shutil.copy2(quadrant_paths[qid], output_path)
        print(f"  [Save] Copied {qid} to {output_path}")
    
    print(f"[Step 2] ✓ Created {len(quadrant_paths)} quadrants from drawing area")
    return quadrant_paths


def main():
    parser = argparse.ArgumentParser(description="ATTEMPT-1: Advanced Captioning Pipeline")
    parser.add_argument("--pdf", type=Path, required=True, help="Path to PDF or image file (PNG, JPG, etc.)")
    parser.add_argument("--page", type=int, default=0, help="Zero-based page index (for PDFs)")
    parser.add_argument("--dpi", type=int, default=300, help="Rasterization DPI (for PDFs)")
    parser.add_argument("--output", type=Path, default=Path("attempt1/output"), help="Output directory")
    parser.add_argument("--model", type=str, choices=["gemini", "gpt", "both"], default="both", 
                       help="Model to use: gemini, gpt, or both (default: both)")
    args = parser.parse_args()
    
    # Check API keys based on model selection
    models_to_run = []
    if args.model in ["gemini", "both"]:
        gemini_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not gemini_key:
            print("ERROR: Set GOOGLE_API_KEY or GEMINI_API_KEY for Gemini")
            if args.model == "gemini":
                sys.exit(1)
        else:
            models_to_run.append(("gemini", gemini_key))
    
    if args.model in ["gpt", "both"]:
        gpt_key = os.getenv("OPENAI_API_KEY")
        if not gpt_key:
            print("ERROR: Set OPENAI_API_KEY for GPT")
            if args.model == "gpt":
                sys.exit(1)
        else:
            models_to_run.append(("gpt", gpt_key))
    
    if not models_to_run:
        print("ERROR: No valid API keys found for selected model(s)")
        sys.exit(1)
    
    if not args.pdf.exists():
        print(f"ERROR: File not found: {args.pdf}")
        sys.exit(1)
    
    # Setup output directory
    drawing_name = args.pdf.stem
    base_output = args.output / drawing_name
    base_output.mkdir(parents=True, exist_ok=True)
    
    print(f"💰 ATTEMPT-1: Advanced Captioning Pipeline")
    print(f"=" * 60)
    print(f"Drawing: {drawing_name}")
    print(f"Page: {args.page + 1}")
    print(f"Models: {[m[0] for m in models_to_run]}")
    print(f"Output: {base_output}")
    print(f"=" * 60)
    
    # Helper function to process one model
    def process_model(model_name: str, api_key: str, segments: Dict[str, Path], quadrants: Dict[str, Path], 
                      full_image: Path, output_dir: Path):
        """Process captioning for one model"""
        print(f"\n{'='*60}")
        print(f"🤖 Processing with {model_name.upper()}")
        print(f"{'='*60}")
        
        # Initialize captioner
        if model_name == "gemini":
            captioner = GeminiCaptioner(api_key)
        else:  # gpt
            captioner = GPTCaptioner(api_key)
        
        # Step 2a: Caption legend first (needed for quadrant captioning)
        print("\n[Step 2a] Captioning legend...")
        legend_region = Region("legend", (0.75, 0.0, 1.0, 1.0), "Legend strip")
        legend_caption = captioner.caption_region(
            segments['legend'],
            legend_region,
            legend_context=None,
            drawing_name=drawing_name,
            page_num=args.page + 1,
            is_legend=True  # Special handling for legend
        )
        
        # Save legend caption
        (output_dir / "legend_caption.txt").write_text(legend_caption)
        print(f"[Step 2a] ✓ Legend caption saved")
        
        # Step 2b: Caption 4 quadrants with legend support
        print("\n[Step 2b] Captioning 4 quadrants with legend support...")
        quadrant_captions = {}
        quadrant_regions = {
            'q1_top_left': Region("q1_top_left", (0.0, 0.0, 0.5, 0.5), "Top-left quadrant"),
            'q2_top_right': Region("q2_top_right", (0.5, 0.0, 1.0, 0.5), "Top-right quadrant"),
            'q3_bottom_left': Region("q3_bottom_left", (0.0, 0.5, 0.5, 1.0), "Bottom-left quadrant"),
            'q4_bottom_right': Region("q4_bottom_right", (0.5, 0.5, 1.0, 1.0), "Bottom-right quadrant"),
        }
        
        for qid, region in quadrant_regions.items():
            caption = captioner.caption_region(
                quadrants[qid],
                region,
                legend_context=legend_caption,
                drawing_name=drawing_name,
                page_num=args.page + 1
            )
            quadrant_captions[qid] = caption
            (output_dir / f"{qid}_caption.txt").write_text(caption)
        
        print(f"[Step 2b] ✓ Captioned {len(quadrant_captions)} quadrants")
        
        # Step 3: Synthesize quadrants + full drawing for grid-level info
        print("\n[Step 3] Synthesizing quadrants + full drawing...")
        quadrant_synthesis = captioner.synthesize_quadrants(
            quadrant_captions,
            full_image,
            legend_caption,
            drawing_name
        )
        (output_dir / "quadrant_synthesis.txt").write_text(quadrant_synthesis)
        print(f"[Step 3] ✓ Synthesis saved")
        
        # Step 4: Final full drawing caption with quadrant-level info
        print("\n[Step 4] Creating final full-drawing caption...")
        final_caption = captioner.synthesize_final_caption(
            quadrant_synthesis,
            quadrant_captions,
            full_image,
            drawing_name
        )
        (output_dir / "final_full_drawing_caption.txt").write_text(final_caption)
        print(f"[Step 4] ✓ Final caption saved")
        
        # Save all results as JSON
        results = {
            "drawing_name": drawing_name,
            "page_number": args.page + 1,
            "model": model_name,
            "legend_caption": legend_caption,
            "quadrant_captions": quadrant_captions,
            "quadrant_synthesis": quadrant_synthesis,
            "final_full_drawing_caption": final_caption,
        }
        
        (output_dir / "results.json").write_text(json.dumps(results, indent=2))
        
        print(f"\n✅ {model_name.upper()} Complete!")
        print(f"📁 Results saved to: {output_dir}")
        print("\n📊 Summary:")
        print(f"  - Legend caption: {len(legend_caption)} chars")
        print(f"  - Quadrant captions: {sum(len(c) for c in quadrant_captions.values())} chars total")
        print(f"  - Quadrant synthesis: {len(quadrant_synthesis)} chars")
        print(f"  - Final caption: {len(final_caption)} chars")
        
        return results
    
    # Process all models
    with tempfile.TemporaryDirectory() as tmp_str:
        tmp_dir = Path(tmp_str)
        
        # Convert PDF or image to PNG
        full_image = convert_to_image(args.pdf, args.page, args.dpi, tmp_dir)
        
        # Step 1: Segment drawing into 2 parts (legend + drawing) - shared between models
        print("\n" + "=" * 60)
        print("📐 SEGMENTATION (shared between models)")
        print("=" * 60)
        segments = segment_drawing(full_image, tmp_dir, base_output)
        
        # Step 2: Create 4 quadrants from the DRAWING area (not full page) - shared between models
        quadrants = create_quadrants(segments['drawing'], tmp_dir, base_output)
        
        # Process each model
        all_results = {}
        for model_name, api_key in models_to_run:
            model_output_dir = base_output / model_name
            model_output_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy shared images to model-specific folder
            import shutil
            for key, path in segments.items():
                shutil.copy2(path, model_output_dir / f"{key}.png")
            for qid, path in quadrants.items():
                shutil.copy2(path, model_output_dir / f"{qid}.png")
            
            results = process_model(model_name, api_key, segments, quadrants, full_image, model_output_dir)
            all_results[model_name] = results
    
    print("\n" + "=" * 60)
    print("✅ ATTEMPT-1 Complete for all models!")
    print(f"📁 Results saved to: {base_output}")
    print(f"   - Gemini: {base_output / 'gemini'}")
    print(f"   - GPT: {base_output / 'gpt'}")
    print("=" * 60)
    print("\n💡 Next: Step 5 - Perform search and retrieval on this data")
    print("💡 Compare outputs in gemini/ and gpt/ folders")


if __name__ == "__main__":
    main()

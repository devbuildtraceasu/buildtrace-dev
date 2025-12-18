#!/usr/bin/env python3
"""
AI Change Detection Evaluation Script

Processes evaluation outputs to run AI change detection analysis.
For each old/new drawing pair, loads images, captions, and calls OpenAI/Gemini APIs.
"""

import argparse
import base64
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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

try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Import prompts from backend
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))
try:
    from processing.prompts_v2 import SYSTEM_PROMPT_V2, USER_PROMPT_V2_3IMAGE
except ImportError:
    # Fallback: read from prompt_instruct.txt
    SYSTEM_PROMPT_V2 = None
    USER_PROMPT_V2_3IMAGE = None


def setup_logging(log_file: Path) -> logging.Logger:
    """Setup logging to both file and console."""
    logger = logging.getLogger("change_detection_eval")
    logger.setLevel(logging.DEBUG)
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # File handler
    file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    return logger


def load_prompts_from_file(prompt_file: Path) -> Tuple[str, str]:
    """Load prompts from prompt_instruct.txt if not available from backend."""
    if SYSTEM_PROMPT_V2 and USER_PROMPT_V2_3IMAGE:
        return SYSTEM_PROMPT_V2, USER_PROMPT_V2_3IMAGE
    
    try:
        content = prompt_file.read_text(encoding='utf-8')
        # Extract SYSTEM_PROMPT_V2 (lines 20-29)
        lines = content.split('\n')
        system_start = None
        system_end = None
        user_start = None
        
        for i, line in enumerate(lines):
            if 'SYSTEM_PROMPT_V2' in line and system_start is None:
                system_start = i
            if system_start and line.strip().startswith('USER_PROMPT_V2'):
                system_end = i
                user_start = i
                break
        
        if system_start and system_end:
            system_prompt = '\n'.join(lines[system_start+1:system_end]).strip()
            # Remove triple quotes if present
            system_prompt = system_prompt.strip('"""').strip()
        else:
            system_prompt = """You are an expert construction project manager and architectural reviewer with 20+ years of experience analyzing construction drawings for change management, RFI responses, and cost impact assessment."""
        
        # Extract USER_PROMPT_V2_3IMAGE (lines 31-174)
        if user_start:
            user_end = None
            for i in range(user_start, len(lines)):
                if 'USER_PROMPT_V2_OVERLAY_ONLY' in lines[i]:
                    user_end = i
                    break
            if user_end:
                user_prompt = '\n'.join(lines[user_start+1:user_end]).strip()
                # Remove triple quotes if present
                user_prompt = user_prompt.strip('"""').strip()
            else:
                user_prompt = content[content.find('USER_PROMPT_V2_3IMAGE'):].split('"""')[1] if '"""' in content else ""
        else:
            user_prompt = ""
        
        return system_prompt, user_prompt
    except Exception as e:
        logging.warning(f"Failed to load prompts from file: {e}")
        # Return defaults
        system_prompt = """You are an expert construction project manager and architectural reviewer with 20+ years of experience analyzing construction drawings for change management, RFI responses, and cost impact assessment."""
        user_prompt = """Analyze these THREE architectural drawings for {drawing_name} (Page {page_number}):"""
        return system_prompt, user_prompt


def find_drawing_pairs(input_dir: Path) -> List[Tuple[str, Path, Path]]:
    """
    Find all old/new drawing pairs in the input directory.
    
    Returns:
        List of tuples: (drawing_name, old_path, new_path)
    """
    pairs = []
    seen_drawings = set()
    
    for item in input_dir.iterdir():
        if not item.is_dir():
            continue
        
        name = item.name
        if name.endswith('_old'):
            drawing_name = name[:-4]  # Remove '_old'
            new_name = f"{drawing_name}_new"
            new_path = input_dir / new_name
            
            if new_path.exists() and new_path.is_dir():
                if drawing_name not in seen_drawings:
                    pairs.append((drawing_name, item, new_path))
                    seen_drawings.add(drawing_name)
    
    return sorted(pairs)


def load_image_as_base64(image_path: Path) -> Optional[str]:
    """Load an image file and convert to base64 string."""
    try:
        with open(image_path, 'rb') as f:
            image_bytes = f.read()
        return base64.b64encode(image_bytes).decode('utf-8')
    except Exception as e:
        logging.error(f"Failed to load image {image_path}: {e}")
        return None


def convert_pdf_to_png(pdf_path: Path, output_dir: Path, dpi: int = 300) -> Optional[Path]:
    """Convert a PDF page to PNG image."""
    if not PDF2IMAGE_AVAILABLE:
        logging.error("pdf2image not available. Install with: pip install pdf2image")
        return None
    
    try:
        images = convert_from_path(str(pdf_path), dpi=dpi, first_page=1, last_page=1)
        if not images:
            logging.error(f"No pages found in PDF: {pdf_path}")
            return None
        
        output_path = output_dir / f"{pdf_path.stem}.png"
        images[0].save(output_path, "PNG")
        return output_path
    except Exception as e:
        logging.error(f"Failed to convert PDF {pdf_path}: {e}")
        return None


def load_caption_files(chatbot_dir: Path) -> Dict[str, str]:
    """
    Load all 7 caption files from a chatbot directory.
    
    Returns:
        Dictionary mapping caption type to content
    """
    caption_files = {
        'q1_top_left': 'q1_top_left_caption.txt',
        'q2_top_right': 'q2_top_right_caption.txt',
        'q3_bottom_left': 'q3_bottom_left_caption.txt',
        'q4_bottom_right': 'q4_bottom_right_caption.txt',
        'legend': 'legend_caption.txt',
        'quadrant_synthesis': 'quadrant_synthesis.txt',
        'final_full_drawing': 'final_full_drawing_caption.txt',
    }
    
    captions = {}
    for key, filename in caption_files.items():
        file_path = chatbot_dir / filename
        if file_path.exists():
            try:
                captions[key] = file_path.read_text(encoding='utf-8').strip()
            except Exception as e:
                logging.warning(f"Failed to read {file_path}: {e}")
                captions[key] = ""
        else:
            logging.warning(f"Caption file not found: {file_path}")
            captions[key] = ""
    
    return captions


def format_captions_for_prompt(captions: Dict[str, Any]) -> str:
    """Format captions into a text block to insert into the prompt."""
    sections = [
        "**ADDITIONAL CONTEXT FROM CAPTION ANALYSIS:**",
        "",
        "The following captions were generated from detailed analysis of the OLD and NEW drawings:",
        "",
    ]
    
    caption_labels = {
        'q1_top_left': 'Quadrant 1 (Top Left)',
        'q2_top_right': 'Quadrant 2 (Top Right)',
        'q3_bottom_left': 'Quadrant 3 (Bottom Left)',
        'q4_bottom_right': 'Quadrant 4 (Bottom Right)',
        'legend': 'Legend',
        'quadrant_synthesis': 'Quadrant Synthesis',
        'final_full_drawing': 'Final Full Drawing Caption',
    }
    
    for key, label in caption_labels.items():
        caption_data = captions.get(key, {})
        if isinstance(caption_data, dict):
            old_text = caption_data.get('old', '')
            new_text = caption_data.get('new', '')
            sections.append(f"**{label}:**")
            if old_text:
                sections.append(f"OLD VERSION:")
                # Escape curly braces for format() compatibility
                sections.append(old_text.replace("{", "{{").replace("}", "}}"))
            if new_text:
                sections.append(f"NEW VERSION:")
                # Escape curly braces for format() compatibility
                sections.append(new_text.replace("{", "{{").replace("}", "}}"))
            if not old_text and not new_text:
                sections.append("N/A")
            sections.append("")
        else:
            # Fallback for simple string format
            sections.append(f"**{label}:**")
            # Escape curly braces for format() compatibility
            sections.append(str(caption_data).replace("{", "{{").replace("}", "}}") if caption_data else "N/A")
            sections.append("")
    
    return '\n'.join(sections)



def load_few_shot_examples(evals_base: Path, current_drawing: str, logger: logging.Logger) -> str:
    """Load few-shot examples from gold_summary.txt files, excluding current drawing."""
    available_drawings = ['A-101', 'A-111', 'A-113', 'A-201', 'G-101', 'G-105']
    few_shot_examples = []
    
    for drawing in available_drawings:
        if drawing == current_drawing:
            continue  # Skip current drawing to avoid giving away the answer
        
        gold_summary_path = evals_base / drawing / 'gold_summary.txt'
        if gold_summary_path.exists():
            try:
                gold_summary = gold_summary_path.read_text(encoding='utf-8').strip()
                if gold_summary:
                    # Escape curly braces for format() compatibility
                    escaped_gold_summary = gold_summary.replace("{", "{{").replace("}", "}}")
                    few_shot_examples.append(f"**Example: {drawing}**\n{escaped_gold_summary}\n")
                    logger.debug(f"Loaded few-shot example from {drawing}")
            except Exception as e:
                logger.warning(f"Failed to load gold_summary for {drawing}: {e}")
    
    if few_shot_examples:
        return "\n\n**FEW-SHOT EXAMPLES FROM OTHER COMPARISONS:**\n\n" + "\n---\n\n".join(few_shot_examples)
    return ""


def enhance_prompt_with_captions(base_prompt: str, captions: Dict[str, str], few_shot_examples: str = "") -> str:
    """Insert captions and few-shot examples into the user prompt before the analysis requirements."""
    caption_text = format_captions_for_prompt(captions)
    
    # Combine captions and few-shot examples
    additional_context = caption_text
    if few_shot_examples:
        additional_context += "\n\n" + few_shot_examples
    
    # Find where to insert (before "**ANALYSIS REQUIREMENTS:**")
    if "**ANALYSIS REQUIREMENTS:**" in base_prompt:
        parts = base_prompt.split("**ANALYSIS REQUIREMENTS:**", 1)
        enhanced = parts[0] + additional_context + "\n\n**ANALYSIS REQUIREMENTS:**" + parts[1]
    else:
        # If pattern not found, append at the end before the JSON format section
        if "Provide your analysis in this EXACT JSON format:" in base_prompt:
            parts = base_prompt.split("Provide your analysis in this EXACT JSON format:", 1)
            enhanced = parts[0] + additional_context + "\n\nProvide your analysis in this EXACT JSON format:" + parts[1]
        else:
            enhanced = base_prompt + "\n\n" + additional_context
    
    return enhanced


def call_openai_api(
    model_name: str,
    system_prompt: str,
    user_prompt: str,
    old_image_base64: str,
    new_image_base64: str,
    overlay_image_base64: Optional[str],
    api_key: str,
    max_tokens: int = 16000
) -> Dict:
    """Call OpenAI API with old/new images and optional overlay image."""
    if not OPENAI_AVAILABLE:
        return {"error": "OpenAI library not available"}
    
    try:
        client = OpenAI(api_key=api_key)
        
        # Build message content with images
        message_content = [{"type": "text", "text": user_prompt}]
        # Add old and new images (always present)
        message_content.extend([
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{old_image_base64}"}
            },
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{new_image_base64}"}
            }
        ])
        # Add overlay image if available
        if overlay_image_base64:
            message_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{overlay_image_base64}"}
            })
        
        # Call API
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message_content}
            ],
            max_completion_tokens=max_tokens,
            response_format={"type": "json_object"}
        )
        
        choice = response.choices[0]
        response_text = choice.message.content
        
        # Parse JSON response
        try:
            parsed_json = json.loads(response_text)
        except json.JSONDecodeError:
            # Try to clean markdown code blocks
            cleaned = response_text.strip()
            if cleaned.startswith('```'):
                lines = cleaned.split('\n')
                if lines[0].startswith('```'):
                    lines = lines[1:]
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                cleaned = '\n'.join(lines)
            try:
                parsed_json = json.loads(cleaned)
            except json.JSONDecodeError as e:
                return {
                    "error": f"Failed to parse JSON: {e}",
                    "raw_response": response_text
                }
        
        return {
            "success": True,
            "model": response.model,
            "finish_reason": choice.finish_reason,
            "response_text": response_text,
            "parsed_json": parsed_json
        }
    except Exception as e:
        return {
            "error": str(e),
            "success": False
        }

def call_gemini_api(
    model_name: str,
    system_prompt: str,
    user_prompt: str,
    old_image_path: Path,
    new_image_path: Path,
    overlay_image_path: Optional[Path],
    api_key: str,
    max_tokens: int = 16000
) -> Dict:
    """Call Gemini API with old/new images and optional overlay image."""

    if not GEMINI_AVAILABLE:
        return {"error": "Gemini library not available"}
    
    try:
        genai.configure(api_key=api_key)
        
        # Ensure model name has 'models/' prefix
        if not model_name.startswith('models/'):
            model_name = f'models/{model_name}'
        
        model = genai.GenerativeModel(model_name)
        
        # Load images as PIL Images for Gemini
        if not PIL_AVAILABLE:
            return {"error": "PIL not available for image loading"}
        
        old_img = Image.open(old_image_path)
        new_img = Image.open(new_image_path)
        
        # Combine prompts
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        # Build content list with images
        content_list = [full_prompt, old_img, new_img]
        if overlay_image_path:
            overlay_img = Image.open(overlay_image_path)
            content_list.append(overlay_img)
        
        # Call API with images
        response = model.generate_content(
            content_list,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.1,
                max_output_tokens=max_tokens
            )
        )
        
        response_text = response.text
        finish_reason = getattr(response.candidates[0], 'finish_reason', 'unknown') if response.candidates else 'no_candidates'
        
        # Parse JSON response
        try:
            parsed_json = json.loads(response_text)
        except json.JSONDecodeError as e:
            return {
                "error": f"Failed to parse JSON: {e}",
                "raw_response": response_text,
                "success": False
            }
        
        return {
            "success": True,
            "model": model_name,
            "finish_reason": finish_reason,
            "response_text": response_text,
            "parsed_json": parsed_json
        }
    except Exception as e:
        return {
            "error": str(e),
            "success": False
        }


def process_drawing_pair(
    drawing_name: str,
    old_dir: Path,
    new_dir: Path,
    evals_base: Path,
    output_base: Path,
    system_prompt: str,
    user_prompt_template: str,
    openai_models: List[str],
    gemini_model: Optional[str],
    chatbots: List[str],
    openai_key: str,
    gemini_key: Optional[str],
    logger: logging.Logger
) -> Dict:
    """Process a single drawing pair (old/new) for all chatbots and models."""
    results = {
        "drawing_name": drawing_name,
        "timestamp": datetime.now().isoformat(),
        "results": {}
    }
    
    # Load few-shot examples from other comparisons
    few_shot_examples = load_few_shot_examples(evals_base, drawing_name, logger)
    if few_shot_examples:
        logger.info(f"Loaded few-shot examples for {drawing_name}")
    else:
        logger.warning(f"No few-shot examples available for {drawing_name}")
    
    # Find overlay PDF (optional - if missing, use few-shot examples only)
    overlay_pdf = evals_base / drawing_name / f"{drawing_name}_overlay.pdf"
    overlay_png = None
    overlay_base64 = None
    
    if overlay_pdf.exists():
        # Convert overlay PDF to PNG (temporary)
        temp_dir = output_base / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        overlay_png = convert_pdf_to_png(overlay_pdf, temp_dir)
        if overlay_png:
            # Load overlay image as base64 for OpenAI
            overlay_base64 = load_image_as_base64(overlay_png)
            if overlay_base64:
                logger.info(f"Loaded overlay image for {drawing_name}")
            else:
                logger.warning(f"Failed to load overlay image for {drawing_name}")
        else:
            logger.warning(f"Failed to convert overlay PDF to PNG for {drawing_name}")
    else:
        logger.warning(f"Overlay PDF not found: {overlay_pdf}")
        logger.info(f"Continuing with few-shot examples only (no overlay image)")
    
    # Process each chatbot
    for chatbot in chatbots:
        chatbot_old_dir = old_dir / chatbot
        chatbot_new_dir = new_dir / chatbot
        
        if not chatbot_old_dir.exists() or not chatbot_new_dir.exists():
            logger.warning(f"Chatbot directory not found: {chatbot_old_dir} or {chatbot_new_dir}")
            continue
        
        # Load caption files from both old and new versions
        old_captions = load_caption_files(chatbot_old_dir)
        new_captions = load_caption_files(chatbot_new_dir)
        
        # Combine captions - include both old and new for context
        # Structure: {key: {"old": ..., "new": ...}}
        combined_captions = {}
        for key in old_captions.keys():
            combined_captions[key] = {
                "old": old_captions.get(key, ""),
                "new": new_captions.get(key, "")
            }
        
        # Load drawing images
        old_drawing_path = old_dir / "drawing.png"
        new_drawing_path = new_dir / "drawing.png"
        
        if not old_drawing_path.exists() or not new_drawing_path.exists():
            logger.warning(f"Drawing images not found for {drawing_name}")
            continue
        
        old_image_base64 = load_image_as_base64(old_drawing_path)
        new_image_base64 = load_image_as_base64(new_drawing_path)
        
        if not old_image_base64 or not new_image_base64:
            logger.warning(f"Failed to load drawing images for {drawing_name}")
            continue
        
        # Enhance prompt with captions and few-shot examples
        enhanced_prompt = enhance_prompt_with_captions(user_prompt_template, combined_captions, few_shot_examples)
        user_prompt = enhanced_prompt.format(drawing_name=drawing_name, page_number=1)
        
        chatbot_results = {}
        
        # Call OpenAI models
        for openai_model in openai_models:
            logger.info(f"Processing {drawing_name}/{chatbot} with {openai_model}...")
            start_time = time.time()
            
            result = call_openai_api(
                model_name=openai_model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                old_image_base64=old_image_base64,
                new_image_base64=new_image_base64,
                overlay_image_base64=overlay_base64,  # Can be None
                api_key=openai_key
            )
            
            duration = time.time() - start_time
            result["duration_seconds"] = duration
            result["timestamp"] = datetime.now().isoformat()
            
            if result.get("success"):
                logger.info(f"✓ {openai_model} completed in {duration:.2f}s")
            else:
                logger.error(f"✗ {openai_model} failed: {result.get('error')}")
            
            chatbot_results[openai_model] = result
        
        # Call Gemini model
        if gemini_model and gemini_key:
            logger.info(f"Processing {drawing_name}/{chatbot} with {gemini_model}...")
            start_time = time.time()
            
            result = call_gemini_api(
                model_name=gemini_model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                old_image_path=old_drawing_path,
                new_image_path=new_drawing_path,
                overlay_image_path=overlay_png,  # Can be None
                api_key=gemini_key
            )
            
            duration = time.time() - start_time
            result["duration_seconds"] = duration
            result["timestamp"] = datetime.now().isoformat()
            
            if result.get("success"):
                logger.info(f"✓ {gemini_model} completed in {duration:.2f}s")
            else:
                logger.error(f"✗ {gemini_model} failed: {result.get('error')}")
            
            chatbot_results[gemini_model] = result
        
        # Save results organized by model, then chatbot
        for model_name, model_result in chatbot_results.items():
            # Sanitize model name for folder name
            safe_model_name = model_name.replace('/', '_').replace('\\', '_')
            # Organize by model first, then chatbot
            model_output_dir = output_base / drawing_name / safe_model_name
            model_output_dir.mkdir(parents=True, exist_ok=True)
            output_file = model_output_dir / f"{chatbot}_comparison.json"

            # Prepare output with metadata
            output_data = {
                "drawing_name": drawing_name,
                "chatbot": chatbot,
                "model": model_name,
                "timestamp": model_result.get("timestamp"),
                "duration_seconds": model_result.get("duration_seconds"),
                "input_paths": {
                    "old_drawing": str(old_drawing_path),
                    "new_drawing": str(new_drawing_path),
                    "overlay_pdf": str(overlay_pdf) if overlay_pdf.exists() else None,
                    "has_overlay": overlay_pdf.exists() if overlay_pdf else False,
                    "has_few_shot": bool(few_shot_examples)
                },
                "api_response": model_result
            }

            output_file.write_text(json.dumps(output_data, indent=2), encoding='utf-8')
            logger.info(f"Saved results to {output_file}")
        results["results"][chatbot] = chatbot_results
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Run AI change detection evaluation on drawing pairs"
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path(__file__).parent / "outputs" / "20251216_011839",
        help="Input directory containing old/new drawing pairs (default: outputs/20251216_011839)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent.parent / "comparison_eval",
        help="Output directory for results (default: ../comparison_eval)"
    )
    parser.add_argument(
        "--openai-models",
        nargs="+",
        default=["gpt-5.2-2025-12-11"],
        help="OpenAI models to run (default: gpt-5.2-2025-12-11)"
    )
    parser.add_argument(
        "--gemini-model",
        type=str,
        default="gemini-3-pro-preview",
        help="Gemini model to run (default: gemini-3-pro-preview, use 'none' to skip)"
    )
    parser.add_argument(
        "--chatbots",
        nargs="+",
        default=["gpt", "gemini"],
        help="Chatbots to process (default: gpt gemini)"
    )
    parser.add_argument(
        "--evals-base",
        type=Path,
        default=Path(__file__).parent,
        help="Base directory for Evals folder (for overlay PDFs, default: current directory)"
    )
    parser.add_argument(
        "--drawing",
        type=str,
        default=None,
        help="Process only a specific drawing pair (e.g., 'A-101'). If not specified, processes all pairs."
    )
    
    args = parser.parse_args()
    
    # Get API keys
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        print("ERROR: OPENAI_API_KEY environment variable not set")
        return 1
    
    gemini_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if args.gemini_model.lower() != 'none' and not gemini_key:
        print("WARNING: GOOGLE_API_KEY or GEMINI_API_KEY not set, skipping Gemini")
        args.gemini_model = None
    
    # Normalize gemini model
    if args.gemini_model and args.gemini_model.lower() == 'none':
        args.gemini_model = None
    
    # Create output directory with run timestamp (so each run gets its own folder)
    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_base = args.output / run_timestamp
    output_base.mkdir(parents=True, exist_ok=True)
    
    # Setup logging
    log_file = output_base / "change_detection_eval.log"
    logger = setup_logging(log_file)
    
    logger.info("="*80)
    logger.info("AI CHANGE DETECTION EVALUATION")
    logger.info("="*80)
    logger.info(f"Run timestamp: {run_timestamp}")
    logger.info(f"Input directory: {args.input}")
    logger.info(f"Output directory: {output_base}")
    logger.info(f"OpenAI models: {args.openai_models}")
    logger.info(f"Gemini model: {args.gemini_model}")
    logger.info(f"Chatbots: {args.chatbots}")
    logger.info("="*80)
    
    # Load prompts
    prompt_file = args.evals_base / "prompt_instruct.txt"
    system_prompt, user_prompt_template = load_prompts_from_file(prompt_file)
    
    # Find drawing pairs
    pairs = find_drawing_pairs(args.input)
    if not pairs:
        logger.error(f"No drawing pairs found in {args.input}")
        return 1
    
    # Filter to specific drawing if requested
    if args.drawing:
        pairs = [(name, old, new) for name, old, new in pairs if name == args.drawing]
        if not pairs:
            logger.error(f"Drawing pair '{args.drawing}' not found in {args.input}")
            logger.info(f"Available drawings: {[name for name, _, _ in find_drawing_pairs(args.input)]}")
            return 1
        logger.info(f"Filtered to single drawing: {args.drawing}")
    
    logger.info(f"Found {len(pairs)} drawing pair(s) to process:")
    for drawing_name, old_path, new_path in pairs:
        logger.info(f"  - {drawing_name}: {old_path.name} / {new_path.name}")
    
    # Process each pair
    all_results = []
    start_time = time.time()
    
    for i, (drawing_name, old_dir, new_dir) in enumerate(pairs, 1):
        logger.info("")
        logger.info("#"*80)
        logger.info(f"Processing pair {i}/{len(pairs)}: {drawing_name}")
        logger.info("#"*80)
        
        try:
            result = process_drawing_pair(
                drawing_name=drawing_name,
                old_dir=old_dir,
                new_dir=new_dir,
                evals_base=args.evals_base,
                output_base=output_base,
                system_prompt=system_prompt,
                user_prompt_template=user_prompt_template,
                openai_models=args.openai_models,
                gemini_model=args.gemini_model,
                chatbots=args.chatbots,
                openai_key=openai_key,
                gemini_key=gemini_key,
                logger=logger
            )
            all_results.append(result)
        except Exception as e:
            logger.exception(f"Error processing {drawing_name}: {e}")
            all_results.append({
                "drawing_name": drawing_name,
                "error": str(e)
            })
    
    # Save summary
    total_duration = time.time() - start_time
    summary = {
        "run_timestamp": run_timestamp,
        "timestamp": datetime.now().isoformat(),
        "total_pairs": len(pairs),
        "total_duration_seconds": total_duration,
        "openai_models": args.openai_models,
        "gemini_model": args.gemini_model,
        "chatbots": args.chatbots,
        "input_directory": str(args.input),
        "results": all_results
    }
    
    summary_file = output_base / "summary.json"
    summary_file.write_text(json.dumps(summary, indent=2), encoding='utf-8')
    
    # Final summary
    logger.info("")
    logger.info("="*80)
    logger.info("✅ PROCESSING COMPLETE")
    logger.info("="*80)
    logger.info(f"Total pairs processed: {len(pairs)}")
    logger.info(f"Total duration: {total_duration/60:.1f} minutes")
    logger.info(f"Results saved to: {output_base}")
    logger.info(f"Summary: {summary_file}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

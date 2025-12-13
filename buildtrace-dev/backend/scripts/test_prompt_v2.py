#!/usr/bin/env python3
"""
Test script for Enhanced Prompt V2
Tests both Gemini 3 Pro and GPT-5.1 models
Logs results to file for comparison
"""

import os
import sys
import json
import base64
import logging
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables from .env file if available
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    # Also try .env copy
    env_copy_path = Path(__file__).parent.parent / ".env copy"
    if env_copy_path.exists():
        load_dotenv(env_copy_path)
except ImportError:
    # Fallback: manually parse .env file
    env_copy_path = Path(__file__).parent.parent / ".env copy"
    if env_copy_path.exists():
        with open(env_copy_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

from config import config
from gcp.storage import StorageService
from processing.prompts_v2 import SYSTEM_PROMPT_V2, USER_PROMPT_V2_3IMAGE, USER_PROMPT_V2_OVERLAY_ONLY

# Setup logging
log_file = Path(__file__).parent.parent.parent / "prompt_v2_test_results.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Test configuration
TEST_DRAWING_NAME = "A-111"
TEST_PAGE_NUMBER = 1
TEST_IMAGES_DIR = Path(__file__).parent.parent.parent.parent / "testing" / "A-111"

def load_test_images():
    """Load test images from local directory"""
    storage = StorageService()
    
    # Try to load images from local test directory
    old_image_path = TEST_IMAGES_DIR / "A-111_old" / "A-111.png"
    new_image_path = TEST_IMAGES_DIR / "A-111_new" / "A-111.png"
    overlay_path = TEST_IMAGES_DIR / "A-111_overlay.pdf"
    
    images = {}
    
    # Load old image
    if old_image_path.exists():
        with open(old_image_path, 'rb') as f:
            images['old_base64'] = base64.b64encode(f.read()).decode('utf-8')
            logger.info(f"Loaded old image: {old_image_path}")
    else:
        logger.warning(f"Old image not found: {old_image_path}")
    
    # Load new image
    if new_image_path.exists():
        with open(new_image_path, 'rb') as f:
            images['new_base64'] = base64.b64encode(f.read()).decode('utf-8')
            logger.info(f"Loaded new image: {new_image_path}")
    else:
        logger.warning(f"New image not found: {new_image_path}")
    
    # Load overlay - convert PDF to PNG if needed
    if overlay_path.exists():
        try:
            if overlay_path.suffix.lower() == '.pdf':
                # Convert PDF to PNG
                import fitz  # PyMuPDF
                pdf_doc = fitz.open(str(overlay_path))
                page = pdf_doc[0]  # Get first page
                
                # Render to image
                mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better quality
                pix = page.get_pixmap(matrix=mat)
                
                # Convert to PNG bytes
                import io
                import PIL.Image
                img_data = pix.tobytes("png")
                images['overlay_base64'] = base64.b64encode(img_data).decode('utf-8')
                logger.info(f"Loaded and converted overlay PDF: {overlay_path} (size: {pix.width}x{pix.height})")
                pdf_doc.close()
            else:
                # Already an image file
                with open(overlay_path, 'rb') as f:
                    images['overlay_base64'] = base64.b64encode(f.read()).decode('utf-8')
                    logger.info(f"Loaded overlay image: {overlay_path}")
        except ImportError:
            logger.warning("PyMuPDF (fitz) not available - cannot convert PDF overlay. Install with: pip install PyMuPDF")
        except Exception as e:
            logger.warning(f"Could not load overlay: {e}")
    else:
        logger.warning(f"Overlay not found: {overlay_path}")
    
    return images

def test_gemini_3_pro(images):
    """Test with Gemini 3 Pro (gemini-3-pro-preview)"""
    print("TESTING: Gemini 3 Pro (gemini-3-pro-preview)")
    logger.info("=" * 80)
    logger.info("TESTING: Gemini 3 Pro (gemini-3-pro-preview)")
    logger.info("=" * 80)
    
    try:
        import google.generativeai as genai
        import PIL.Image
        import io
        
        # Check for API key (try multiple env var names)
        api_key = (
            config.GEMINI_API_KEY or 
            os.getenv('GEMINI_API_KEY') or 
            os.getenv('GOOGLE_API_KEY') or
            os.getenv('GOOGLE_AI_API_KEY')
        )
        if not api_key:
            logger.error("GEMINI_API_KEY not configured. Set GEMINI_API_KEY or GOOGLE_API_KEY environment variable")
            return None
        
        genai.configure(api_key=api_key)
        
        # Try gemini-3-pro-preview, fallback to gemini-2.5-pro if not available
        model_name = 'gemini-3-pro-preview'
        try:
            model = genai.GenerativeModel(model_name)
        except Exception as e:
            logger.warning(f"gemini-3-pro-preview not available, trying gemini-2.5-pro: {e}")
            model_name = 'gemini-2.5-pro'
            model = genai.GenerativeModel(model_name)
        
        # Build prompt - need all 3 images (old, new, overlay)
        if images.get('old_base64') and images.get('new_base64') and images.get('overlay_base64'):
            user_prompt = USER_PROMPT_V2_3IMAGE.format(
                drawing_name=TEST_DRAWING_NAME,
                page_number=TEST_PAGE_NUMBER
            )
            
            # Load and resize images if needed (Gemini has size limits)
            PIL.Image.MAX_IMAGE_PIXELS = 200000000
            MAX_DIMENSION = 1600
            
            old_img_bytes = base64.b64decode(images['old_base64'])
            new_img_bytes = base64.b64decode(images['new_base64'])
            overlay_img_bytes = base64.b64decode(images['overlay_base64'])
            
            old_img = PIL.Image.open(io.BytesIO(old_img_bytes))
            new_img = PIL.Image.open(io.BytesIO(new_img_bytes))
            overlay_img = PIL.Image.open(io.BytesIO(overlay_img_bytes))
            
            # Resize if too large
            for img_name, img in [("old", old_img), ("new", new_img), ("overlay", overlay_img)]:
                if max(img.size) > MAX_DIMENSION:
                    ratio = MAX_DIMENSION / max(img.size)
                    new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                    if img_name == "old":
                        old_img = img.resize(new_size, PIL.Image.Resampling.LANCZOS)
                    elif img_name == "new":
                        new_img = img.resize(new_size, PIL.Image.Resampling.LANCZOS)
                    else:
                        overlay_img = img.resize(new_size, PIL.Image.Resampling.LANCZOS)
                    logger.info(f"Resized {img_name} image to {new_size}")
            
            # Combine system and user prompt
            full_prompt = f"{SYSTEM_PROMPT_V2}\n\n{user_prompt}"
            
            print(f"  Sending request with 3 images (old: {old_img.size}, new: {new_img.size}, overlay: {overlay_img.size})...")
            start_time = datetime.now()
            
            # Gemini supports multiple images in a single call - send all 3 images
            print("  Calling Gemini API...")
            response = model.generate_content(
                [
                    full_prompt,
                    old_img,
                    new_img,
                    overlay_img
                ],
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.1,
                )
            )
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            print(f"  ✓ Received response in {duration:.2f}s")
            
            result = {
                "model": model_name,
                "success": True,
                "duration_seconds": duration,
                "response_text": response.text,
                "finish_reason": getattr(response, 'finish_reason', 'unknown'),
                "timestamp": datetime.now().isoformat()
            }
            
            # Try to parse JSON
            try:
                result["parsed_json"] = json.loads(response.text)
                result["parse_success"] = True
                result["total_changes_detected"] = result["parsed_json"].get("total_changes", 0)
                result["keynotes_added"] = len(result["parsed_json"].get("added_keynotes", []))
                result["keynotes_removed"] = len(result["parsed_json"].get("removed_keynotes", []))
                result["keynotes_modified"] = len(result["parsed_json"].get("modified_keynotes", []))
            except json.JSONDecodeError as e:
                result["parse_success"] = False
                result["parse_error"] = str(e)
            
            logger.info(f"Gemini {model_name} completed in {duration:.2f}s")
            logger.info(f"Response length: {len(response.text)} chars")
            logger.info(f"Finish reason: {result['finish_reason']}")
            if result.get('parse_success'):
                logger.info(f"Total changes detected: {result.get('total_changes_detected', 0)}")
                logger.info(f"Keynotes - Added: {result.get('keynotes_added', 0)}, Removed: {result.get('keynotes_removed', 0)}, Modified: {result.get('keynotes_modified', 0)}")
            
            return result
            
        else:
            missing = []
            if not images.get('old_base64'):
                missing.append("old")
            if not images.get('new_base64'):
                missing.append("new")
            if not images.get('overlay_base64'):
                missing.append("overlay")
            logger.error(f"Missing required images for Gemini test: {', '.join(missing)}")
            return None
            
    except Exception as e:
        logger.error(f"Gemini 3 Pro test failed: {e}", exc_info=True)
        return {
            "model": "gemini-3-pro-preview",
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "timestamp": datetime.now().isoformat()
        }

def test_gpt_5_1(images):
    """Test with GPT-5.1 (note: GPT-5 doesn't support temperature parameter)"""
    print("TESTING: GPT-5.1 (gpt-5.1)")
    logger.info("=" * 80)
    logger.info("TESTING: GPT-5.1 (gpt-5.1)")
    logger.info("=" * 80)
    
    try:
        from openai import OpenAI
        
        # Check for OpenAI API key
        api_key = config.OPENAI_API_KEY or os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.error("OPENAI_API_KEY not configured. Set OPENAI_API_KEY environment variable")
            return None
        
        client = OpenAI(api_key=api_key)
        
        # Build message content - need all 3 images (old, new, overlay)
        if images.get('old_base64') and images.get('new_base64') and images.get('overlay_base64'):
            user_prompt = USER_PROMPT_V2_3IMAGE.format(
                drawing_name=TEST_DRAWING_NAME,
                page_number=TEST_PAGE_NUMBER
            )
            
            message_content = [{"type": "text", "text": user_prompt}]
            
            # Add all 3 images in order: old, new, overlay
            message_content.extend([
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{images['old_base64']}"}
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{images['new_base64']}"}
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{images['overlay_base64']}"}
                }
            ])
            
            print(f"  Sending request with 3 images (old, new, overlay)...")
            start_time = datetime.now()
            
            # Try gpt-5.1 first, fallback to gpt-4o if not available
            model_name = "gpt-5.1"
            print(f"  Trying model: {model_name}...")
            try:
                # GPT-5.1 doesn't support temperature, max_tokens, etc. - use minimal config
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT_V2},
                        {"role": "user", "content": message_content}
                    ],
                    response_format={"type": "json_object"}
                )
                print(f"  ✓ Using model: {model_name}")
            except Exception as e:
                print(f"  ⚠ {model_name} not available ({e}), trying gpt-4o...")
                logger.warning(f"gpt-5.1 not available ({e}), trying gpt-4o")
                model_name = "gpt-4o"
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT_V2},
                        {"role": "user", "content": message_content}
                    ],
                    response_format={"type": "json_object"},
                    max_completion_tokens=16000
                )
                print(f"  ✓ Using model: {model_name}")
            
            print("  Calling OpenAI API...")
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            print(f"  ✓ Received response in {duration:.2f}s")
            
            choice = response.choices[0]
            response_text = choice.message.content
            
            result = {
                "model": model_name,
                "success": True,
                "duration_seconds": duration,
                "response_text": response_text,
                "finish_reason": choice.finish_reason,
                "model_used": response.model,
                "timestamp": datetime.now().isoformat()
            }
            
            # Try to parse JSON
            try:
                result["parsed_json"] = json.loads(response_text)
                result["parse_success"] = True
                result["total_changes_detected"] = result["parsed_json"].get("total_changes", 0)
                result["keynotes_added"] = len(result["parsed_json"].get("added_keynotes", []))
                result["keynotes_removed"] = len(result["parsed_json"].get("removed_keynotes", []))
                result["keynotes_modified"] = len(result["parsed_json"].get("modified_keynotes", []))
            except json.JSONDecodeError as e:
                result["parse_success"] = False
                result["parse_error"] = str(e)
            
            logger.info(f"{model_name} completed in {duration:.2f}s")
            logger.info(f"Response length: {len(response_text)} chars")
            logger.info(f"Finish reason: {result['finish_reason']}")
            if result.get('parse_success'):
                logger.info(f"Total changes detected: {result.get('total_changes_detected', 0)}")
                logger.info(f"Keynotes - Added: {result.get('keynotes_added', 0)}, Removed: {result.get('keynotes_removed', 0)}, Modified: {result.get('keynotes_modified', 0)}")
            
            return result
            
        else:
            missing = []
            if not images.get('old_base64'):
                missing.append("old")
            if not images.get('new_base64'):
                missing.append("new")
            if not images.get('overlay_base64'):
                missing.append("overlay")
            logger.error(f"Missing required images for GPT-5.1 test: {', '.join(missing)}")
            return None
            
    except Exception as e:
        logger.error(f"GPT-5.1 test failed: {e}", exc_info=True)
        return {
            "model": "gpt-5.1",
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "timestamp": datetime.now().isoformat()
        }

def main():
    """Run tests for both models"""
    print("=" * 80)
    print("PROMPT V2 TEST SUITE")
    print(f"Started at: {datetime.now().isoformat()}")
    print("=" * 80)
    logger.info("=" * 80)
    logger.info("PROMPT V2 TEST SUITE")
    logger.info(f"Started at: {datetime.now().isoformat()}")
    logger.info("=" * 80)
    
    # Check API keys
    print("\n[1/5] Checking API keys...")
    gemini_key = config.GEMINI_API_KEY or os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
    openai_key = config.OPENAI_API_KEY or os.getenv('OPENAI_API_KEY')
    
    if gemini_key:
        print(f"✓ GEMINI_API_KEY found (length: {len(gemini_key)})")
    else:
        print("✗ GEMINI_API_KEY not found")
    
    if openai_key:
        print(f"✓ OPENAI_API_KEY found (length: {len(openai_key)})")
    else:
        print("✗ OPENAI_API_KEY not found")
    
    # Load test images
    print("\n[2/5] Loading test images...")
    logger.info("Loading test images...")
    images = load_test_images()
    
    if not images.get('old_base64') or not images.get('new_base64') or not images.get('overlay_base64'):
        missing = []
        if not images.get('old_base64'):
            missing.append("old")
        if not images.get('new_base64'):
            missing.append("new")
        if not images.get('overlay_base64'):
            missing.append("overlay")
        print(f"✗ Failed to load required test images. Missing: {', '.join(missing)}")
        print("All 3 images (old, new, overlay) are required for testing")
        logger.error(f"Failed to load required test images. Missing: {', '.join(missing)}")
        logger.error("All 3 images (old, new, overlay) are required for testing")
        return
    
    print(f"✓ Loaded all 3 images: old ({len(images['old_base64'])} chars), new ({len(images['new_base64'])} chars), overlay ({len(images['overlay_base64'])} chars)")
    logger.info(f"Loaded all 3 images: old, new, and overlay")
    
    # Test Gemini 3 Pro
    print("\n[3/5] Testing Gemini 3 Pro...")
    print("-" * 80)
    gemini_result = test_gemini_3_pro(images)
    
    # Test GPT-5.1
    print("\n[4/5] Testing GPT-5.1...")
    print("-" * 80)
    gpt_result = test_gpt_5_1(images)
    
    # Summary
    print("\n[5/5] TEST SUMMARY")
    print("=" * 80)
    logger.info("=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)
    
    if gemini_result:
        status = 'SUCCESS' if gemini_result.get('success') else 'FAILED'
        print(f"\nGemini 3 Pro: {status}")
        logger.info(f"Gemini 3 Pro: {status}")
        if gemini_result.get('success'):
            print(f"  Duration: {gemini_result.get('duration_seconds', 0):.2f}s")
            print(f"  Response length: {len(gemini_result.get('response_text', ''))} chars")
            print(f"  JSON parse: {'SUCCESS' if gemini_result.get('parse_success') else 'FAILED'}")
            if gemini_result.get('parse_success'):
                print(f"  Total changes: {gemini_result.get('total_changes_detected', 0)}")
                print(f"  Keynotes - Added: {gemini_result.get('keynotes_added', 0)}, Removed: {gemini_result.get('keynotes_removed', 0)}, Modified: {gemini_result.get('keynotes_modified', 0)}")
            logger.info(f"  Duration: {gemini_result.get('duration_seconds', 0):.2f}s")
            logger.info(f"  Response length: {len(gemini_result.get('response_text', ''))} chars")
            logger.info(f"  JSON parse: {'SUCCESS' if gemini_result.get('parse_success') else 'FAILED'}")
        else:
            print(f"  Error: {gemini_result.get('error', 'Unknown error')}")
    
    if gpt_result:
        status = 'SUCCESS' if gpt_result.get('success') else 'FAILED'
        print(f"\nGPT-5.1: {status}")
        logger.info(f"GPT-5.1: {status}")
        if gpt_result.get('success'):
            print(f"  Model used: {gpt_result.get('model_used', gpt_result.get('model', 'unknown'))}")
            print(f"  Duration: {gpt_result.get('duration_seconds', 0):.2f}s")
            print(f"  Response length: {len(gpt_result.get('response_text', ''))} chars")
            print(f"  JSON parse: {'SUCCESS' if gpt_result.get('parse_success') else 'FAILED'}")
            if gpt_result.get('parse_success'):
                print(f"  Total changes: {gpt_result.get('total_changes_detected', 0)}")
                print(f"  Keynotes - Added: {gpt_result.get('keynotes_added', 0)}, Removed: {gpt_result.get('keynotes_removed', 0)}, Modified: {gpt_result.get('keynotes_modified', 0)}")
            logger.info(f"  Duration: {gpt_result.get('duration_seconds', 0):.2f}s")
            logger.info(f"  Response length: {len(gpt_result.get('response_text', ''))} chars")
            logger.info(f"  JSON parse: {'SUCCESS' if gpt_result.get('parse_success') else 'FAILED'}")
        else:
            print(f"  Error: {gpt_result.get('error', 'Unknown error')}")
    
    # Save detailed results to JSON
    results_file = Path(__file__).parent.parent.parent / "prompt_v2_test_results.json"
    with open(results_file, 'w') as f:
        json.dump({
            "test_config": {
                "drawing_name": TEST_DRAWING_NAME,
                "page_number": TEST_PAGE_NUMBER,
                "prompt_version": "v2",
                "test_timestamp": datetime.now().isoformat()
            },
            "gemini_3_pro": gemini_result,
            "gpt_5_1": gpt_result
        }, f, indent=2)
    
    print(f"\n✓ Detailed results saved to: {results_file}")
    print(f"✓ Log file: {log_file}")
    print("=" * 80)
    logger.info(f"Detailed results saved to: {results_file}")
    logger.info(f"Log file: {log_file}")
    logger.info("=" * 80)

if __name__ == "__main__":
    main()


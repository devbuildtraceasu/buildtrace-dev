#!/usr/bin/env python3
"""Test Gemini 3 Pro Preview API call with timeout and error handling"""

import os
import sys
import time
from pathlib import Path

try:
    import google.generativeai as genai
except ImportError:
    print("ERROR: google-generativeai not installed. Run: pip install google-generativeai")
    sys.exit(1)

# Get API key
gemini_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
if not gemini_key:
    print("ERROR: Set GOOGLE_API_KEY or GEMINI_API_KEY")
    sys.exit(1)

print(f"✓ API Key found (length: {len(gemini_key)})")

# Configure Gemini
genai.configure(api_key=gemini_key)

# Test 1: Simple text prompt (fast test)
print("\n" + "="*60)
print("Test 1: Simple text prompt with gemini-3-pro-preview")
print("="*60)
try:
    model = genai.GenerativeModel("gemini-3-pro-preview")
    print("✓ Model initialized: gemini-3-pro-preview")
    
    start = time.time()
    print("Calling API...")
    response = model.generate_content(
        "Say 'Hello, Gemini 3 Pro is working!' if you can read this.",
        generation_config=genai.types.GenerationConfig(
            temperature=0.1,
            max_output_tokens=100,
        ),
        safety_settings=[
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ],
    )
    elapsed = time.time() - start
    
    print(f"✓ Response received in {elapsed:.2f} seconds")
    
    # Check finish_reason
    if hasattr(response, "candidates") and response.candidates:
        candidate = response.candidates[0]
        finish_reason = getattr(candidate, "finish_reason", None)
        print(f"Finish reason: {finish_reason} (0=STOP, 1=MAX_TOKENS, 2=SAFETY)")
        
        if finish_reason == 2:
            print("⚠️  Response blocked by safety filters!")
            if hasattr(candidate, "safety_ratings"):
                print(f"Safety ratings: {candidate.safety_ratings}")
            sys.exit(1)
    
    # Try to get text
    try:
        print(f"Response: {response.text[:200]}")
    except ValueError:
        # Try parts
        if hasattr(response, "candidates") and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, "content") and candidate.content:
                if hasattr(candidate.content, "parts") and candidate.content.parts:
                    for part in candidate.content.parts:
                        if hasattr(part, "text") and part.text:
                            print(f"Response: {part.text[:200]}")
                            break
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 2: Image with small timeout
print("\n" + "="*60)
print("Test 2: Image caption with gemini-3-pro-preview (with timeout)")
print("="*60)

# Try to load a test image
test_image_path = Path("../testing/Temple/TempleTest_Add1.pdf")
if not test_image_path.exists():
    print(f"⚠️  Test PDF not found: {test_image_path}")
    print("Skipping image test...")
    sys.exit(0)

try:
    from pdf2image import convert_from_path
    import PIL.Image
    PIL.Image.MAX_IMAGE_PIXELS = 200000000
    
    print(f"Converting PDF page 1 to image...")
    images = convert_from_path(str(test_image_path), dpi=150, first_page=1, last_page=1)
    if not images:
        print("❌ No images returned")
        sys.exit(1)
    
    # Resize to small test size
    img = images[0]
    if max(img.size) > 800:
        ratio = 800 / max(img.size)
        new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
        print(f"Resizing from {img.size} to {new_size}")
        img = img.resize(new_size, PIL.Image.Resampling.LANCZOS)
    
    print(f"Image size: {img.size}, mode: {img.mode}")
    
    # Save to bytes
    import io
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    image_data = img_bytes.read()
    print(f"Image data size: {len(image_data) / 1024:.1f} KB")
    
    print("\nCalling Gemini 3 Pro Preview with image...")
    print("(This may take 30-90 seconds for gemini-3-pro-preview)")
    print("Setting 120 second timeout...")
    
    start = time.time()
    
    # Add timeout using signal (Unix only) or threading
    import signal
    
    def timeout_handler(signum, frame):
        raise TimeoutError("API call timed out after 120 seconds")
    
    # Set alarm for 120 seconds
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(120)
    
    try:
        response = model.generate_content(
        [
            "Describe this architectural drawing in detail. What rooms, doors, windows, and annotations do you see?",
            {"mime_type": "image/png", "data": image_data}
        ],
        generation_config=genai.types.GenerationConfig(
            temperature=0.2,
            max_output_tokens=1000,  # Small for testing
        ),
        safety_settings=[
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ],
        )
        signal.alarm(0)  # Cancel alarm
        elapsed = time.time() - start
        
        print(f"✓ Response received in {elapsed:.2f} seconds")
    except TimeoutError as e:
        signal.alarm(0)  # Cancel alarm
        print(f"❌ {e}")
        print("The API call is taking too long. Possible issues:")
        print("  - Network connectivity problems")
        print("  - API rate limiting")
        print("  - Model overloaded")
        print("  - Image too large")
        sys.exit(1)
    
    # Check finish_reason
    if hasattr(response, "candidates") and response.candidates:
        candidate = response.candidates[0]
        finish_reason = getattr(candidate, "finish_reason", None)
        print(f"Finish reason: {finish_reason} (0=STOP, 1=MAX_TOKENS, 2=SAFETY)")
        
        if finish_reason == 2:
            print("⚠️  Response blocked by safety filters")
            if hasattr(candidate, "safety_ratings"):
                print(f"Safety ratings: {candidate.safety_ratings}")
    
    # Try to get text
    try:
        text = response.text
        print(f"\n✓ Caption generated ({len(text)} chars):")
        print(text[:500])
        if len(text) > 500:
            print("... (truncated)")
    except ValueError as e:
        print(f"❌ Cannot access response.text: {e}")
        # Try parts
        if hasattr(response, "candidates") and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, "content") and candidate.content:
                if hasattr(candidate.content, "parts") and candidate.content.parts:
                    for part in candidate.content.parts:
                        if hasattr(part, "text") and part.text:
                            print(f"\n✓ Caption from parts ({len(part.text)} chars):")
                            print(part.text[:500])
                            break
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*60)
print("✅ All tests completed!")
print("="*60)

#!/usr/bin/env python3
"""
Test script to check GPT-5 OCR timing locally
"""
import os
import time
import base64
from openai import OpenAI

# Get API key from environment or config
API_KEY = os.getenv('OPENAI_API_KEY')
if not API_KEY:
    # Try to read from buildtrace config
    import sys
    sys.path.insert(0, 'buildtrace-dev/backend')
    try:
        from config import config
        API_KEY = config.OPENAI_API_KEY
    except:
        pass

if not API_KEY:
    print("ERROR: OPENAI_API_KEY not found. Please set it in environment.")
    exit(1)

print(f"API Key length: {len(API_KEY)}")

# Initialize client with timeout
client = OpenAI(api_key=API_KEY, timeout=180.0)  # 3 minute timeout

# Test images
TEST_IMAGES = [
    "testing/A-111/A-111_old/A-111.png",
    "testing/A-111/A-111_new/A-111.png",
    "testing/A-101/A-101_old/A-101.png",
]

def encode_image(image_path):
    with open(image_path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")

def test_gpt5_ocr(image_path, model="gpt-5"):
    """Test OCR with specified model"""
    print(f"\n{'='*60}")
    print(f"Testing: {image_path}")
    print(f"Model: {model}")
    print(f"{'='*60}")
    
    if not os.path.exists(image_path):
        print(f"ERROR: File not found: {image_path}")
        return None
    
    # Get file size
    file_size = os.path.getsize(image_path) / 1024 / 1024
    print(f"File size: {file_size:.2f} MB")
    
    # Encode image
    print("Encoding image...")
    image_base64 = encode_image(image_path)
    print(f"Base64 length: {len(image_base64)} chars")
    
    # Prepare prompt
    prompt = """Analyze this architectural drawing and extract:
1. Drawing number/name
2. Title block information
3. Key annotations and notes
4. Scale information
5. Any revision information

Return as structured JSON."""

    # Make API call
    print(f"\nCalling {model} API...")
    start_time = time.time()
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ],
            max_completion_tokens=4000
        )
        
        elapsed = time.time() - start_time
        print(f"\n✓ SUCCESS in {elapsed:.2f} seconds")
        print(f"Tokens used: {response.usage.total_tokens if response.usage else 'N/A'}")
        print(f"\nResponse preview (first 500 chars):")
        print(response.choices[0].message.content[:500] if response.choices else "No content")
        return elapsed
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n✗ FAILED after {elapsed:.2f} seconds")
        print(f"Error: {type(e).__name__}: {e}")
        return None

def main():
    print("="*60)
    print("GPT-5 OCR Timing Test")
    print("="*60)
    
    results = []
    
    # Test with GPT-5
    for img in TEST_IMAGES:
        result = test_gpt5_ocr(img, model="gpt-5")
        results.append(("gpt-5", img, result))
    
    # Also test with GPT-4o for comparison
    print("\n\n" + "="*60)
    print("Now testing with GPT-4o for comparison...")
    print("="*60)
    
    for img in TEST_IMAGES[:1]:  # Just test one image
        result = test_gpt5_ocr(img, model="gpt-4o")
        results.append(("gpt-4o", img, result))
    
    # Summary
    print("\n\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for model, img, elapsed in results:
        status = f"{elapsed:.2f}s" if elapsed else "FAILED"
        print(f"{model:10} | {os.path.basename(img):20} | {status}")

if __name__ == "__main__":
    main()


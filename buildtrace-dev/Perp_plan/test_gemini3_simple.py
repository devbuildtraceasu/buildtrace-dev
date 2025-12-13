#!/usr/bin/env python3
"""Simple test for Gemini 3 Pro Preview - checks if model is available and responds"""

import os
import sys
import time

try:
    import google.generativeai as genai
except ImportError:
    print("ERROR: google-generativeai not installed")
    sys.exit(1)

gemini_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
if not gemini_key:
    print("ERROR: Set GOOGLE_API_KEY or GEMINI_API_KEY")
    sys.exit(1)

genai.configure(api_key=gemini_key)

# List available models
print("Checking available models...")
try:
    models = genai.list_models()
    available = [m.name for m in models if 'generateContent' in m.supported_generation_methods]
    print(f"Available models: {len(available)}")
    gemini3_models = [m for m in available if 'gemini-3' in m.lower() or 'gemini-pro' in m.lower()]
    if gemini3_models:
        print(f"✓ Gemini 3 models found: {gemini3_models}")
    else:
        print("⚠️  No Gemini 3 models found in available models")
        print("Top 10 available models:")
        for m in available[:10]:
            print(f"  - {m}")
except Exception as e:
    print(f"⚠️  Could not list models: {e}")

# Test model name - try gemini-3-pro-image-preview first (better for images)
model_name = "gemini-3-pro-image-preview"
print(f"\nTesting model: {model_name}")
print("(Note: gemini-3-pro-preview may have stricter safety filters)")

try:
    model = genai.GenerativeModel(model_name)
    print(f"✓ Model '{model_name}' initialized successfully")
except Exception as e:
    print(f"❌ Failed to initialize model '{model_name}': {e}")
    print("\nTrying alternative model names...")
    alternatives = [
        "gemini-pro",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-2.0-flash-exp",
    ]
    for alt in alternatives:
        try:
            test_model = genai.GenerativeModel(alt)
            print(f"✓ Alternative '{alt}' works")
        except:
            pass
    sys.exit(1)

# Simple text test with safety settings
print(f"\nTest 1: Simple text prompt (should be fast)...")
start = time.time()
try:
    response = model.generate_content(
        "Say 'OK' if you can read this.",
        generation_config=genai.types.GenerationConfig(max_output_tokens=10),
        safety_settings=[
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ],
    )
    elapsed = time.time() - start
    
    # Check finish_reason first
    if hasattr(response, "candidates") and response.candidates:
        candidate = response.candidates[0]
        finish_reason = getattr(candidate, "finish_reason", None)
        print(f"Finish reason: {finish_reason} (0=STOP, 1=MAX_TOKENS, 2=SAFETY)")
        
        if finish_reason == 2:
            print("⚠️  Response blocked by safety filters even with BLOCK_NONE!")
            if hasattr(candidate, "safety_ratings"):
                print(f"Safety ratings: {candidate.safety_ratings}")
            sys.exit(1)
        
        # Try to get text from parts
        if hasattr(candidate, "content") and candidate.content:
            if hasattr(candidate.content, "parts") and candidate.content.parts:
                for part in candidate.content.parts:
                    if hasattr(part, "text") and part.text:
                        print(f"✓ Response in {elapsed:.2f}s: {part.text}")
                        break
        else:
            try:
                print(f"✓ Response in {elapsed:.2f}s: {response.text}")
            except ValueError:
                print("❌ Cannot access response text")
                sys.exit(1)
    else:
        print("❌ No candidates in response")
        sys.exit(1)
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✅ Basic test passed! Model is responding.")
print("\nIf image calls are slow, that's normal for gemini-3-pro-preview.")
print("Consider using gemini-2.5-flash for faster results.")

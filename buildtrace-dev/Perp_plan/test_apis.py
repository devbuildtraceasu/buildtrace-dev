#!/usr/bin/env python3
"""Quick test to verify Gemini and OpenAI APIs work"""

import os
import sys
from pathlib import Path

# Test Gemini
try:
    import google.generativeai as genai
    gemini_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        print("❌ GEMINI_API_KEY not set")
        sys.exit(1)
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel("gemini-2.5-flash")
    print("✓ Gemini configured")
    
    # Test with a simple text prompt
    response = model.generate_content("Say 'Hello' if you can read this.")
    print(f"✓ Gemini response: {response.text[:50]}")
except Exception as e:
    print(f"❌ Gemini failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test OpenAI
try:
    from openai import OpenAI
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        print("❌ OPENAI_API_KEY not set")
        sys.exit(1)
    client = OpenAI(api_key=openai_key)
    print("✓ OpenAI configured")
    
    # Test embedding
    resp = client.embeddings.create(model="text-embedding-3-small", input="test")
    print(f"✓ OpenAI embedding: {len(resp.data[0].embedding)} dimensions")
except Exception as e:
    print(f"❌ OpenAI failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✅ All APIs working!")

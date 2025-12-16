# Token Limit Issues - Analysis & Fixes

**Date:** December 12, 2025  
**Issue:** Legend and quadrant captioning hitting token limits (finish_reason=1)

---

## Web Search Findings

### Gemini 3 Pro Token Limits
- **Maximum Output Tokens:** Up to **65,536 tokens** (not 16,384)
- **Input Tokens:** Up to 1,048,576 tokens
- **Issue:** Setting `maxOutputTokens` too low can prevent the model from generating ANY content
- **Behavior:** When `finish_reason=1` (MAX_TOKENS) with empty content, it means the limit was hit before any content was generated

### Common Causes
1. **Image Size Too Large**
   - High resolution images consume many tokens
   - Legend regions can be very dense with symbols
   - Solution: Resize images before sending

2. **Max Tokens Too Low**
   - Previous setting: 16,384 for legend, 8,192 for quadrants
   - Gemini 3 Pro supports up to 65,536
   - Solution: Increased to 32,768 for legend, 16,384 for quadrants

3. **Dense Content**
   - Legends with many symbols/keynotes
   - Quadrants with detailed architectural elements
   - Solution: Better prompt optimization

4. **Response Cut Off**
   - If response is cut off before any content is generated, `candidate.content` may be empty
   - Solution: Better error handling and fallback extraction

---

## Fixes Applied

### 1. Increased Token Limits
- **Legend:** 16,384 → **32,768 tokens**
- **Quadrants:** 8,192 → **16,384 tokens**
- **Synthesis:** 16,384 → **32,768 tokens**

### 2. Comprehensive Logging Added
- Image dimensions and file size
- Prompt length (chars and estimated tokens)
- Finish reason with human-readable description
- Candidate structure details
- Part-by-part text extraction
- Possible reasons when hitting limits
- Recommendations for fixes

### 3. Better Error Handling
- Checks for `candidate.content` existence
- Checks for `content.parts` existence
- Part-by-part extraction with logging
- Detailed error messages with finish reason

### 4. Image Saving
- All cropped images (legend, drawing, 4 quadrants) saved to output directory
- Allows manual verification of segmentation quality

### 5. Synthesis Reasoning
- Added requirement for reasoning and source citations
- Model must explain synthesis process
- Source tracking (which quadrant provided what info)
- Confidence levels
- Conflict resolution documentation

---

## Recommendations

1. **If Still Hitting Limits:**
   - Increase to 65,536 tokens (maximum)
   - Resize images to reduce token consumption
   - Simplify prompts for legend extraction

2. **Monitor Logs:**
   - Check image sizes in logs
   - Monitor finish_reason values
   - Track which regions consistently hit limits

3. **Optimize Images:**
   - Resize legend to max 2000px width
   - Reduce DPI if needed (300 → 200)
   - Compress images before sending

---

**Last Updated:** December 12, 2025

# Failure Analysis: Gemini Token Limit Issues

**Date:** December 12, 2025  
**Issue:** Multiple captioning failures with `finish_reason=1` (MAX_TOKENS) and empty content

---

## Failure Pattern

### Symptoms
- `finish_reason=1` (MAX_TOKENS)
- `candidate.content` exists but is empty
- `response.text` fails with: "Invalid operation: The `response.text` quick accessor requires the response to contain a valid `Part`, but none were returned"
- No text extracted from `candidate.content.parts`

### Affected Regions
1. **Legend** - Failed completely (no content)
2. **Q3 (bottom-left)** - Failed completely (no content)
3. **Q1, Q2, Q4** - Partial success (truncated but some content extracted)

---

## Root Cause Analysis

### 1. Image Size vs Token Consumption
- **Legend:** 3150x9000px, 1.65MB → **FAILED**
- **Q1:** 4725x4500px, 0.22MB → **PARTIAL** (3186 chars)
- **Q2:** 4725x4500px, 1.05MB → **PARTIAL** (5266 chars)
- **Q3:** 4725x4500px, 0.66MB → **FAILED**
- **Q4:** 4725x4500px, 0.62MB → **PARTIAL** (6041 chars)

**Observation:** Larger images (legend, Q2, Q3) are more likely to fail. However, Q1 (smallest) succeeded partially, suggesting it's not just file size.

### 2. Token Limit Already at Maximum
- Current setting: **65,536 tokens** (maximum for Gemini 3 Pro)
- Cannot increase further
- Issue: Model is hitting limit **before generating any content**

### 3. Possible Causes

#### A. Input Token Consumption
- Large images consume significant input tokens
- Legend image: 3150x9000px = 28.35M pixels
- Each pixel may consume tokens in the vision encoder
- Prompt + image may exceed input token budget, leaving no room for output

#### B. Model Behavior
- When input is too large, model may:
  1. Process the image but run out of tokens before generating output
  2. Return `finish_reason=1` with empty content
  3. This is different from truncation (which would have partial content)

#### C. Dense Content
- Legend with many symbols/keynotes
- Architectural drawings with complex details
- Model needs many tokens to describe everything

---

## Solutions

### Immediate: Use GPT-5.2
- **Higher token limits:** GPT-5.2 supports larger contexts
- **Better handling:** May handle large images better
- **Cost:** $14/1M output tokens (vs Gemini's pricing)
- **Comparison:** Run both models and compare outputs

### Long-term: Image Optimization
1. **Resize images before sending**
   - Legend: Max 2000px width
   - Quadrants: Max 3000px width
   - Reduce DPI from 300 to 200

2. **Chunk complex regions**
   - Split legend into smaller sections
   - Process each section separately
   - Combine results

3. **Progressive captioning**
   - First pass: High-level overview
   - Second pass: Detailed components
   - Combine both passes

---

## Recommendations

1. **Implement GPT-5.2** as alternative (DONE)
2. **Compare outputs** from both models
3. **If GPT-5.2 works better:**
   - Use it for large/complex regions
   - Keep Gemini for simpler regions
4. **If both fail:**
   - Implement image resizing
   - Implement chunking strategy
   - Reduce prompt verbosity

---

**Last Updated:** December 12, 2025

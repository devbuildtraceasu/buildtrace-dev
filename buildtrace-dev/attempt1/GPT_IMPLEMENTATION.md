# GPT-5.2 Implementation

**Date:** December 12, 2025  
**Feature:** Added GPT-5.2 support alongside Gemini for comparison

---

## Changes Made

### 1. Added GPT-5.2 Captioner Class
- **Class:** `GPTCaptioner` (mirrors `GeminiCaptioner` functionality)
- **Model:** `gpt-5.2-2025-12-11` (correct model name)
- **API:** OpenAI Chat Completions API with vision support
- **Token Limit:** 65,536 `max_completion_tokens` (same as Gemini)

### 2. Model Selection
- **New Parameter:** `--model` with choices: `gemini`, `gpt`, `both` (default: `both`)
- **API Keys:**
  - Gemini: `GOOGLE_API_KEY` or `GEMINI_API_KEY`
  - GPT: `OPENAI_API_KEY`

### 3. Output Organization
- **Structure:**
  ```
  output/
    drawing_name/
      legend.png          # Shared segmentation
      drawing.png         # Shared segmentation
      q1_top_left.png     # Shared quadrants
      q2_top_right.png
      q3_bottom_left.png
      q4_bottom_right.png
      gemini/
        legend_caption.txt
        q1_top_left_caption.txt
        q2_top_right_caption.txt
        q3_bottom_left_caption.txt
        q4_bottom_right_caption.txt
        quadrant_synthesis.txt
        final_full_drawing_caption.txt
        results.json
      gpt/
        legend_caption.txt
        q1_top_left_caption.txt
        q2_top_right_caption.txt
        q3_bottom_left_caption.txt
        q4_bottom_right_caption.txt
        quadrant_synthesis.txt
        final_full_drawing_caption.txt
        results.json
  ```

### 4. Shared Segmentation
- Segmentation (legend/drawing split) and quadrant creation happen once
- Results are shared between both models
- Images are copied to each model's folder for reference

---

## Usage

### Run Both Models (Default)
```bash
python3 attempt1/attempt1_captioning.py \
  --pdf "path/to/drawing.pdf" \
  --page 0 \
  --output attempt1/output \
  --model both
```

### Run Only Gemini
```bash
python3 attempt1/attempt1_captioning.py \
  --pdf "path/to/drawing.pdf" \
  --page 0 \
  --output attempt1/output \
  --model gemini
```

### Run Only GPT
```bash
python3 attempt1/attempt1_captioning.py \
  --pdf "path/to/drawing.pdf" \
  --page 0 \
  --output attempt1/output \
  --model gpt
```

---

## GPT-5.2 Implementation Details

### API Call Pattern
```python
response = self.client.chat.completions.create(
    model="gpt-5.2-2025-12-11",
    messages=[
        {
            "role": "system",
            "content": "You are an expert at describing architectural drawings..."
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
```

### Key Differences from Gemini
1. **API Format:** Chat completions vs. generate_content
2. **Image Encoding:** Base64 in data URL vs. binary data
3. **Response:** `response.choices[0].message.content` vs. `response.text`
4. **Error Handling:** Simpler (no finish_reason complexity)

---

## Cost Information

### GPT-5.2 Pricing
- **Input:** $1.750 / 1M tokens
- **Cached input:** $0.175 / 1M tokens
- **Output:** $14.000 / 1M tokens

### Comparison
- **Gemini:** Free tier available, then pay-per-use
- **GPT-5.2:** Higher output cost but may handle large images better

---

## Expected Benefits

1. **Better Token Handling:** GPT-5.2 may handle large images better
2. **Comparison:** Side-by-side outputs for quality assessment
3. **Fallback:** If one model fails, the other may succeed
4. **Quality:** Different models may capture different details

---

## Next Steps

1. **Run comparison tests** on problematic drawings
2. **Analyze outputs** to see which model performs better
3. **Optimize prompts** based on model-specific behavior
4. **Consider hybrid approach:** Use GPT for large/complex regions, Gemini for simpler ones

---

**Last Updated:** December 12, 2025

## Region-Based RAG PoC (Temple/A1 drawings)

Two scripts:
1) `region_rag_poc.py` – single region (default full-page), caption + embed + answer.
2) `region_rag_quadrants.py` – captions full page + 4 quadrants; retrieves top region and answers with both caption and image.

Current defaults:
- Caption provider: OpenAI vision (`gpt-5.1`), no downscale (sends full cropped image).
- Embeddings: `text-embedding-3-small`.
- Answer model: `gpt-5.1` (vision-capable).
- PDF: `testing/Temple/TempleTest_Add1.pdf`
- Questions: `vecTOR_EMBEDDING/Q_set_immediate.txt`

> PDFs are git-ignored. Ensure the drawing file exists at the path you pass (Temple or A1).

### Setup
```bash
python -m pip install google-generativeai openai pdf2image pillow
export OPENAI_API_KEY=...
# Gemini optional if you switch providers
export GOOGLE_API_KEY=...   # or GEMINI_API_KEY
```
 
### Run: single-region PoC
```bash
python Perp_plan/region_rag_poc.py \
  --pdf testing/Temple/TempleTest_Add1.pdf \
  --page 0 \
  --questions vecTOR_EMBEDDING/Q_set_immediate.txt \
  --output Perp_plan/output \
  --caption-provider openai \
  --openai-caption-model gpt-5.1 \
  --caption-max-tokens 4000 \
  --save-raw
```
Key flags:
- `--regions <path>`: JSON list of regions `[id, bbox]` (default: full_page).
- `--caption-provider {openai|gemini}`; `--openai-caption-model` or `--caption-model` (for Gemini).
- `--caption-max-tokens`: caption length cap.
- `--region-filter`: limit RAG to a region.

### Run: quadrant PoC (full page + 4 quadrants)
```bash
python Perp_plan/region_rag_quadrants.py \
  --pdf testing/Temple/TempleTest_Add1.pdf \
  --page 0 \
  --questions vecTOR_EMBEDDING/Q_set_immediate.txt \
  --output Perp_plan/output_quadrants \
  --caption-model gpt-5.1 \
  --caption-max-tokens 4000 \
  --answer-model gpt-5.1 \
  --save-raw
```
Behavior:
- Captions full page + Q1–Q4 crops (no resize), saves raw captions if requested.
- Embeds captions; retrieval picks top region.
- Answers with caption + region image sent to the answer model (vision).

### Outputs
- Single-region: `Perp_plan/output/{captions.json, embeddings_metadata.json, rag_results.json}` (+ raw captions if `--save-raw`).
- Quadrants: `Perp_plan/output_quadrants/{captions.json, embeddings_metadata.json, rag_results.json}` plus `openai_caption_<region>.txt` when `--save-raw`.

Notes:
- For faster but lighter answers, you can switch `--answer-model` to `gpt-4o`.
- If you need multi-region context, consider extending to use top-k regions instead of top-1. At present, retrieval uses only the top match.

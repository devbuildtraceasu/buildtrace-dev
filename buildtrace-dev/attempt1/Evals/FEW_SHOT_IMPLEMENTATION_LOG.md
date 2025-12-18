# Few-Shot Examples and Overlay Fallback Implementation Log

**Date:** December 18, 2025  
**Changes:** Added few-shot examples from gold summaries and fallback for missing overlay PDFs

---

## Changes Made

### 1. Added Few-Shot Examples Loading

**Function:** `load_few_shot_examples(evals_base: Path, current_drawing: str, logger: logging.Logger) -> str`

**Location:** `attempt1/Evals/run_change_detection_eval.py` (lines 277-298)

**Functionality:**
- Loads gold_summary.txt files from other drawing comparisons
- Available drawings: A-101, A-111, A-113, A-201, G-101, G-105
- **Excludes current drawing** to avoid giving away the expected output
- Escapes curly braces in gold_summary text for format() compatibility
- Returns formatted few-shot examples string

**Example Output Format:**
```
**FEW-SHOT EXAMPLES FROM OTHER COMPARISONS:**

**Example: A-111**
[gold_summary content from A-111/gold_summary.txt]

---

**Example: A-113**
[gold_summary content from A-113/gold_summary.txt]

---
...
```

### 2. Updated Prompt Enhancement

**Function:** `enhance_prompt_with_captions(base_prompt: str, captions: Dict[str, str], few_shot_examples: str = "") -> str`

**Changes:**
- Added `few_shot_examples` parameter (optional)
- Combines captions and few-shot examples before inserting into prompt
- Few-shot examples are inserted after captions, before "**ANALYSIS REQUIREMENTS:**"

### 3. Overlay Fallback Implementation

**Function:** `process_drawing_pair()`

**Changes:**
- **Before:** Script would return early if overlay PDF was missing
- **After:** Script continues processing even without overlay PDF
- When overlay is missing:
  - Logs warning but continues
  - Loads few-shot examples (always loaded, but more important when overlay missing)
  - Sends only old/new images to API (no overlay image)
  - Includes few-shot examples in prompt to guide the model

**Behavior:**
- If overlay PDF exists: Send 3 images (old, new, overlay) + captions + few-shot examples
- If overlay PDF missing: Send 2 images (old, new) + captions + few-shot examples

### 4. Updated API Functions

**`call_openai_api()`:**
- `overlay_image_base64` parameter is now `Optional[str]` (can be None)
- Only adds overlay image to message_content if `overlay_image_base64` is not None
- Always sends old and new images

**`call_gemini_api()`:**
- `overlay_image_path` parameter is now `Optional[Path]` (can be None)
- Only loads and adds overlay image if `overlay_image_path` is not None
- Always sends old and new images

### 5. Metadata Updates

**Output JSON now includes:**
```json
{
  "input_paths": {
    "old_drawing": "...",
    "new_drawing": "...",
    "overlay_pdf": "..." or null,
    "has_overlay": true/false,
    "has_few_shot": true/false
  }
}
```

### 6. Timestamped Output Folders

**Change:** Each run now creates a unique timestamped folder to prevent overwriting previous results.

**Implementation:**
- Each run generates a timestamp in format: `YYYYMMDD_HHMMSS` (e.g., `20251218_100149`)
- Output structure: `comparison_eval/{run_timestamp}/`
- Allows iterative testing and comparison of different prompt/strategy improvements
- Run timestamp is logged at the start of each run
- Run timestamp is included in `summary.json` for reference

**Output Structure:**
```
comparison_eval/
├── 20251218_100149/              # Run 1 - Initial test
│   ├── A-101/
│   │   ├── gpt-5.2-2025-12-11/
│   │   │   ├── gpt_comparison.json
│   │   │   └── gemini_comparison.json
│   │   └── gemini-3-pro-preview/
│   │       ├── gpt_comparison.json
│   │       └── gemini_comparison.json
│   ├── G-101/
│   ├── summary.json               # Contains run_timestamp field
│   └── change_detection_eval.log
├── 20251218_103022/              # Run 2 - Different prompt strategy
│   ├── A-101/
│   ├── summary.json
│   └── change_detection_eval.log
└── 20251218_110530/              # Run 3 - Another iteration
    └── ...
```

**Benefits:**
- ✅ Never overwrites previous results
- ✅ Easy to compare results across different runs
- ✅ Track improvements with different prompts/strategies
- ✅ Each run is uniquely identifiable by timestamp

---

## Usage

### With Overlay (Normal Case)
- Processes with 3 images (old, new, overlay)
- Includes captions + few-shot examples in prompt

### Without Overlay (Fallback Case - G-101, G-105)
- Processes with 2 images (old, new only)
- Includes captions + few-shot examples in prompt
- Few-shot examples provide guidance when overlay visualization is unavailable

---

## Logging

The script now logs:
- `INFO`: "Run timestamp: {run_timestamp}" - at the start of each run
- `INFO`: "Loaded few-shot examples for {drawing_name}" - when few-shot examples are successfully loaded
- `WARNING`: "No few-shot examples available for {drawing_name}" - when no gold summaries found
- `WARNING`: "Overlay PDF not found: {path}" - when overlay is missing
- `INFO`: "Continuing with few-shot examples only (no overlay image)" - when processing without overlay
- `DEBUG`: "Loaded few-shot example from {drawing}" - for each gold summary loaded

---

## Files Modified

1. `attempt1/Evals/run_change_detection_eval.py`
   - Added `load_few_shot_examples()` function
   - Updated `enhance_prompt_with_captions()` to accept few-shot examples
   - Updated `call_openai_api()` to handle optional overlay
   - Updated `call_gemini_api()` to handle optional overlay
   - Updated `process_drawing_pair()` to:
     - Load few-shot examples
     - Handle missing overlay gracefully
     - Pass few-shot examples to prompt enhancement
     - Pass None for overlay when missing
   - Updated `main()` to:
     - Always generate a run timestamp for each execution
     - Create timestamped output folders (prevents overwriting)
     - Log run timestamp at start of execution
     - Include run_timestamp in summary.json

---

## Testing

The script should now:
1. ✅ Process A-101, A-111, A-113, A-201 with overlay + few-shot examples
2. ✅ Process G-101, G-105 without overlay but with few-shot examples
3. ✅ Exclude current drawing's gold_summary from few-shot examples
4. ✅ Escape curly braces in gold_summary text
5. ✅ Log all few-shot loading and overlay status

---

**End of Log**

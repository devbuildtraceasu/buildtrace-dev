# AI Change Detection Evaluation Script

This script runs AI change detection evaluation on architectural drawing pairs using OpenAI and Gemini models.

## Features

- **Few-shot learning**: Automatically loads examples from other comparisons to guide the model
- **Overlay fallback**: Gracefully handles missing overlay PDFs by using few-shot examples
- **Timestamped runs**: Each run creates a unique timestamped folder to prevent overwriting results
- **Multi-model support**: Supports multiple OpenAI models and Gemini models in a single run
- **Structured output**: Results organized by model, then by chatbot for easy comparison

## Usage

### Basic Usage

```bash
# Run for a specific drawing
python3 run_change_detection_eval.py --drawing A-101

# Run for multiple drawings (run separately)
python3 run_change_detection_eval.py --drawing A-101
python3 run_change_detection_eval.py --drawing G-101
python3 run_change_detection_eval.py --drawing G-105

# Run for all drawings
python3 run_change_detection_eval.py
```

### Command-Line Arguments

- `--input`: Input directory containing old/new drawing pairs (default: `outputs/20251216_011839`)
- `--output`: Output directory for results (default: `../comparison_eval`)
- `--openai-models`: OpenAI models to run (default: `gpt-5.2-2025-12-11`)
  - Example: `--openai-models gpt-5.2-2025-12-11 gpt-3.0-pro-preview`
- `--gemini-model`: Gemini model to run (default: `gemini-3-pro-preview`, use `none` to skip)
- `--chatbots`: Chatbots to process (default: `gpt gemini`)
- `--evals-base`: Base directory for Evals folder (for overlay PDFs, default: current directory)
- `--drawing`: Process only a specific drawing pair (e.g., `A-101`). If not specified, processes all pairs.

### Examples

```bash
# Run with multiple OpenAI models
python3 run_change_detection_eval.py --drawing A-101 \
  --openai-models gpt-5.2-2025-12-11 gpt-3.0-pro-preview

# Run only with OpenAI (skip Gemini)
python3 run_change_detection_eval.py --drawing A-101 \
  --gemini-model none

# Run only with GPT chatbot captions
python3 run_change_detection_eval.py --drawing A-101 \
  --chatbots gpt

# Custom input/output directories
python3 run_change_detection_eval.py --drawing A-101 \
  --input /path/to/input \
  --output /path/to/output
```

## Output Structure

Each run creates a timestamped folder to prevent overwriting previous results:

```
comparison_eval/
├── 20251218_100149/              # Run timestamp: YYYYMMDD_HHMMSS
│   ├── A-101/
│   │   ├── gpt-5.2-2025-12-11/
│   │   │   ├── gpt_comparison.json
│   │   │   └── gemini_comparison.json
│   │   └── gemini-3-pro-preview/
│   │       ├── gpt_comparison.json
│   │       └── gemini_comparison.json
│   ├── G-101/
│   │   └── ... (same structure)
│   ├── summary.json               # Run summary with run_timestamp
│   └── change_detection_eval.log  # Detailed execution log
├── 20251218_103022/              # Another run with different timestamp
│   └── ...
└── 20251218_110530/              # Yet another run
    └── ...
```

### Output File Structure

Each `{chatbot}_comparison.json` file contains:

```json
{
  "drawing_name": "A-101",
  "chatbot": "gpt",
  "model": "gpt-5.2-2025-12-11",
  "timestamp": "2025-12-18T10:01:49.123456",
  "duration_seconds": 45.2,
  "input_paths": {
    "old_drawing": "...",
    "new_drawing": "...",
    "overlay_pdf": "..." or null,
    "has_overlay": true/false,
    "has_few_shot": true/false
  },
  "api_response": {
    "success": true,
    "model": "...",
    "parsed_json": { ... }
  }
}
```

## Environment Variables

Required:
- `OPENAI_API_KEY`: Your OpenAI API key

Optional:
- `GOOGLE_API_KEY` or `GEMINI_API_KEY`: Your Google/Gemini API key (required if using Gemini models)

## How It Works

1. **Loads prompts**: Reads system and user prompts from `prompt_instruct.txt`
2. **Finds drawing pairs**: Discovers `_old` and `_new` drawing pairs in the input directory
3. **Loads few-shot examples**: Loads gold summaries from other comparisons (excluding current drawing)
4. **Handles overlay**: 
   - If overlay PDF exists: Converts to PNG and includes in API calls
   - If overlay PDF missing: Continues with few-shot examples only (fallback mode)
5. **Processes each chatbot**: For each chatbot (gpt, gemini), loads caption files
6. **Calls AI models**: Sends images and enhanced prompts to OpenAI and Gemini APIs
7. **Saves results**: Organizes results by model, then by chatbot in timestamped folders

## Few-Shot Examples

The script automatically loads few-shot examples from `gold_summary.txt` files in other drawing directories:
- Available drawings: A-101, A-111, A-113, A-201, G-101, G-105
- **Excludes current drawing** to avoid giving away the expected output
- Examples are inserted into the prompt before analysis requirements

## Overlay Fallback

For drawings without overlay PDFs (e.g., G-101, G-105):
- Script logs a warning but continues processing
- Uses few-shot examples to guide the model
- Sends only old/new images (no overlay image)
- Results are still saved with `has_overlay: false` flag

## Iterative Testing

The timestamped folder structure allows you to:
- ✅ Compare results across different runs
- ✅ Track improvements with different prompts/strategies
- ✅ Never overwrite previous results
- ✅ Easily identify which run used which configuration

Each `summary.json` includes the `run_timestamp` field for reference.

## Troubleshooting

### Missing API Keys
- Ensure `OPENAI_API_KEY` is set
- For Gemini, set `GOOGLE_API_KEY` or `GEMINI_API_KEY`

### Missing Overlay PDFs
- Script will continue with few-shot examples only
- Check logs for warnings about missing overlay PDFs

### No Drawing Pairs Found
- Verify input directory structure: `{drawing_name}_old/` and `{drawing_name}_new/`
- Check that drawing images exist: `drawing.png` in each directory

## See Also

- `FEW_SHOT_IMPLEMENTATION_LOG.md`: Detailed implementation notes
- `prompt_instruct.txt`: Prompt templates used by the script

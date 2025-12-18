# Batch PDF Processing for Captioning

This script processes all PDF files in the Evals folder (and subfolders) using the `attempt1_captioning.py` script.

## Features

- **Filtered Processing**: Only processes PDFs ending with `_new.pdf` or `_old.pdf` (excludes `_overlay.pdf`)
- **Detailed Logging**: Comprehensive logging to both file and console
- **Real-time Progress**: See progress updates in real-time as each PDF is processed
- **Progress Tracking**: Shows elapsed time, estimated remaining time, and success/failure counts
- **Timestamped Outputs**: All outputs organized by timestamp for easy tracking

## Output Structure

```
Evals/
  outputs/
    YYYYMMDD_HHMMSS/          # Timestamp folder
      drawing_name1/          # Drawing folder (from PDF name)
        gemini/               # Gemini model outputs
          - legend_caption.txt
          - q1_top_left_caption.txt
          - q2_top_right_caption.txt
          - q3_bottom_left_caption.txt
          - q4_bottom_right_caption.txt
          - quadrant_synthesis.txt
          - final_full_drawing_caption.txt
          - results.json
          - [segmented images]
        gpt/                  # GPT model outputs
          - [same files as gemini]
      drawing_name2/
        ...
      batch_summary.json      # Processing summary (JSON)
      batch_summary_human_readable.txt  # Human-readable summary
      batch_processing.log     # Detailed processing log with all output
```

## Logging

The script creates detailed logs:

- **Console Output**: Real-time progress updates, important status messages
- **Log File** (`batch_processing.log`): Complete detailed log including:
  - All subprocess stdout/stderr output
  - Timing information for each PDF
  - Progress summaries
  - Error details

Log levels:
- **INFO**: Progress updates, status messages, important events
- **DEBUG**: Detailed subprocess output
- **WARNING**: Error messages from subprocess
- **ERROR**: Processing failures

## Usage

### Basic Usage (process all PDFs with both models)

```bash
cd attempt1/Evals
python batch_process_pdfs.py
```

### Process with specific model only

```bash
# Only Gemini
python batch_process_pdfs.py --model gemini

# Only GPT
python batch_process_pdfs.py --model gpt
```

### Custom options

```bash
# Process specific page (0-indexed)
python batch_process_pdfs.py --page 0

# Change DPI
python batch_process_pdfs.py --dpi 300

# Custom output directory
python batch_process_pdfs.py --output-base /path/to/output

# Dry run (see what would be processed)
python batch_process_pdfs.py --dry-run
```

## Requirements

1. **API Keys**: Set environment variables before running:
   ```bash
   export GOOGLE_API_KEY="your-key"  # or GEMINI_API_KEY
   export OPENAI_API_KEY="your-key"
   ```

2. **Dependencies**: Same as `attempt1_captioning.py`:
   - pdf2image
   - Pillow
   - google-generativeai (for Gemini)
   - openai (for GPT)

## Analysis

After processing, you can:

1. **Compare model outputs**: Check the `gemini/` and `gpt/` folders for each drawing
2. **Review summaries**: Read `batch_summary_human_readable.txt` for overview
3. **Detailed analysis**: Compare specific files:
   - `quadrant_synthesis.txt` - Grid-level synthesis
   - `final_full_drawing_caption.txt` - Final comprehensive caption
   - `results.json` - Complete results in JSON format

## Notes

- The script processes PDFs recursively in the Evals folder
- Each PDF is processed independently
- Outputs are organized by timestamp for easy tracking
- Failed processing is logged in the summary file

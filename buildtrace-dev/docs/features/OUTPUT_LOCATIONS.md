# Output Locations Guide

This document shows where all outputs, logs, and intermediate files are saved in local development mode.

## Base Directory Structure

All paths are relative to `buildtrace-dev/backend/`:

```
backend/
├── outputs/          # Main output directory (created by LocalOutputManager)
│   ├── sessions/     # Session-based outputs
│   ├── jobs/         # Job-based outputs
│   ├── logs/         # General logs
│   └── temp/         # Temporary files
├── uploads/          # Uploaded files
│   └── drawings/     # Drawing uploads
├── results/          # Processing results
├── temp/             # Temporary processing files
└── logs/             # Application logs
```

## Output Locations by Feature

### 1. Drawing Comparison Pipeline

**Module**: `processing/drawing_comparison.py`

**Outputs**:
- `outputs/sessions/{session_id}/overlays/`
  - `{drawing_name}_old.png` - Original old drawing
  - `{drawing_name}_new.png` - New drawing
  - `{drawing_name}_overlay.png` - Overlay comparison image

**Example**:
```
outputs/sessions/abc-123/overlays/
  ├── A-101_old.png
  ├── A-101_new.png
  └── A-101_overlay.png
```

### 2. Change Analyzer

**Module**: `processing/change_analyzer.py`

**Outputs**:
- `outputs/sessions/{session_id}/json/`
  - `change_analysis_{drawing_name}.json` - Individual analysis
  - `change_analysis_summary.json` - Summary of all analyses

**Example**:
```
outputs/sessions/abc-123/json/
  ├── change_analysis_A-101.json
  ├── change_analysis_A-102.json
  └── change_analysis_summary.json
```

**JSON Structure**:
```json
{
  "drawing_name": "A-101",
  "overlay_folder": "path/to/overlay",
  "success": true,
  "changes_found": ["Change 1", "Change 2"],
  "critical_change": "Most critical change",
  "recommendations": ["Rec 1", "Rec 2"],
  "analysis_summary": "Full analysis text..."
}
```

### 3. Complete Drawing Pipeline

**Module**: `processing/complete_pipeline.py`

**Outputs**:
- Combines outputs from Drawing Comparison + Change Analyzer
- Also creates overlay folders in working directory:
  - `{pdf_name}_overlays/{drawing_name}_overlay_results/`

**Example**:
```
backend/
  ├── outputs/sessions/abc-123/
  │   ├── overlays/...
  │   └── json/...
  └── new_drawings_overlays/
      ├── A-101_overlay_results/
      │   ├── A-101_old.png
      │   ├── A-101_new.png
      │   ├── A-101_overlay.png
      │   └── change_analysis_A-101.json
      └── A-102_overlay_results/
          └── ...
```

### 4. OCR Pipeline

**Module**: `processing/ocr_pipeline.py`

**Outputs**:
- `outputs/sessions/{session_id}/ocr_results/`
  - `{drawing_name}_ocr.json` - OCR extraction results

### 5. Diff Pipeline

**Module**: `processing/diff_pipeline.py`

**Outputs**:
- `outputs/sessions/{session_id}/diff_results/`
  - `{drawing_name}_diff.json` - Diff analysis results

### 6. Summary Pipeline

**Module**: `processing/summary_pipeline.py`

**Outputs**:
- `outputs/sessions/{session_id}/summaries/`
  - `{drawing_name}_summary.json` - Summary results

### 7. Processing Logs

**Outputs**:
- `outputs/sessions/{session_id}/logs/`
  - `processing_log_{timestamp}.json` - Processing logs

## Configuration

### Environment Variables

Set these in `.env` or environment:

```bash
# Local output paths (defaults shown)
LOCAL_OUTPUT_PATH=outputs
LOCAL_UPLOAD_PATH=uploads
LOCAL_RESULTS_PATH=results
LOCAL_TEMP_PATH=temp

# Enable/disable features
USE_GCS=false          # Set to false for local dev
USE_DATABASE=false     # Set to false for local dev
```

### Using LocalOutputManager

```python
from utils.local_output_manager import LocalOutputManager

# Initialize
output_manager = LocalOutputManager()

# Get session path
session_path = output_manager.get_session_path("session-123")
# Returns: outputs/sessions/session-123/

# Save files
output_manager.save_file("path/to/file.png", "file.png", session_id="session-123")
# Saves to: outputs/sessions/session-123/files/file.png

output_manager.save_json({"data": "value"}, "result.json", session_id="session-123")
# Saves to: outputs/sessions/session-123/json/result.json
```

## Finding Your Outputs

### By Session ID
```bash
# Find all files for a session
find outputs/sessions/{session_id} -type f
```

### By Drawing Name
```bash
# Find all files for a drawing
find outputs -name "*A-101*"
```

### By Type
```bash
# Find all overlays
find outputs -name "*_overlay.png"

# Find all analysis JSONs
find outputs -name "change_analysis_*.json"

# Find all OCR results
find outputs -name "*_ocr.json"
```

## Test Outputs

When running tests, outputs are saved to temporary directories:

```python
# Tests use tempfile.mkdtemp()
# Outputs are cleaned up after tests
```

## Production Mode

When `USE_GCS=true`:
- Files are saved to Google Cloud Storage buckets
- Local outputs are still created for debugging
- Check GCS buckets:
  - `GCS_UPLOAD_BUCKET` - Uploaded files
  - `GCS_PROCESSED_BUCKET` - Processed results

## Quick Reference

| Feature | Output Location | File Pattern |
|---------|----------------|--------------|
| Overlays | `outputs/sessions/{id}/overlays/` | `*_overlay.png` |
| Change Analysis | `outputs/sessions/{id}/json/` | `change_analysis_*.json` |
| OCR Results | `outputs/sessions/{id}/ocr_results/` | `*_ocr.json` |
| Diff Results | `outputs/sessions/{id}/diff_results/` | `*_diff.json` |
| Summaries | `outputs/sessions/{id}/summaries/` | `*_summary.json` |
| Logs | `outputs/sessions/{id}/logs/` | `processing_log_*.json` |
| Uploads | `uploads/drawings/` | Original uploaded files |

## Viewing Outputs

### Using the Script
```bash
cd buildtrace-dev/backend
python3 show_output_locations.py
```

### Direct Access
```bash
# List all sessions
ls outputs/sessions/

# View a specific session
ls -R outputs/sessions/{session_id}/

# View latest analysis
cat outputs/sessions/{session_id}/json/change_analysis_*.json | jq
```


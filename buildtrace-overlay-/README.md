
# Drawing Alignment Tool

This tool aligns two versions of the same drawing using computer vision. It detects features using SIFT, matches them between images, and applies a constrained affine transformation to align the drawings.

## Core Components

### 1. Drawing Alignment (`align_drawings.py`)
The main tool for aligning two versions of the same drawing.

**Usage:**
```bash
python align_drawings.py \
    --old_path drawings/test1_old.png \
    --new_path drawings/test1_new.png \
    --overlay_path drawings/test1_overlay.png \
    --show_overlay
```

**API:**
```py
aligned_old_img = AlignDrawings(debug=args.debug)(old_img, new_img)
overlay = create_overlay_image(aligned_old_img, new_img)
```

### 2. Drawing Name Extraction (`extract_drawing.py`)
Extracts drawing names from PDF pages using a two-step approach:

**Logic:**
1. **Text Extraction**: Uses PyMuPDF to extract text with positions from vector/text PDFs
2. **Bottom-Right Preference**: Chooses drawing names closest to the bottom-right corner of each page
3. **OCR Fallback**: If no text found, uses Tesseract OCR on the bottom-right region
4. **Pattern Matching**: Finds drawing names like A-101, A-102, A-344-MB, S-12A, etc.

**Usage:**
```bash
python extract_drawing.py drawingset.pdf
```

**Output:**
```
Page   1: A-001
Page   2: A-101
Page   3: A-102
Page   4: A-103
Page   5: A-201
Page   6: A-202
Page   7: A-301
Page   8: A-302
```

**Dependencies:**
```bash
pip install PyMuPDF pytesseract
brew install tesseract  # macOS
```

### 3. PDF to PNG Parser (`pdf_parser.py`)
Splits PDF files into individual PNG pages with organized directory structure.

**Logic:**
1. **Page Detection**: Determines total number of pages in the PDF
2. **Directory Creation**: Creates `{pdf_name}/` directory for organized output
3. **Page Conversion**: Uses existing `pdf_to_png()` function to convert each page
4. **Sequential Naming**: Names files as `{pdf_name}_page1.png`, `{pdf_name}_page2.png`, etc.

**Usage:**
```bash
python pdf_parser.py drawings/drawingset.pdf --list
```

**Output Structure:**
```
drawingset/
├── drawingset_page1.png
├── drawingset_page2.png
├── drawingset_page3.png
└── ...
```

**Options:**
- `--dpi 600`: Set custom DPI for PNG conversion
- `--list`: Show all created PNG files after conversion

### 4. PDF Parser with Smart Naming (`pdf_parser.py`)
Combines drawing name extraction and PDF-to-PNG conversion for intelligent file naming.

**Logic:**
1. **Extract Drawing Names**: Uses `extract_drawing_names()` to get drawing names from each PDF page
2. **Create Output Directory**: Creates `{pdf_name}/` directory
3. **Convert with Smart Naming**: Uses `pdf_to_png()` to convert each page
4. **Fallback Handling**: If drawing name extraction fails, falls back to `{pdf_name}_page{N}.png` format

**Usage:**
```bash
python pdf_parser.py drawingset.pdf --list
```

**Output Structure:**
```
drawingset/
├── A-001.png    # Page 1 with extracted drawing name
├── A-101.png    # Page 2 with extracted drawing name
├── A-102.png    # Page 3 with extracted drawing name
└── drawingset_page4.png  # Page 4 with fallback naming (if extraction failed)
```

### 5. Drawing Comparison Pipeline (`drawing_comparison.py`)
Complete pipeline for comparing two PDF drawing sets and creating alignment overlays.

**Features:**
- **Complete Pipeline**: Converts PDFs to PNG, finds matches, creates overlays
- **Smart Matching**: Automatically matches drawings with same names between sets
- **Organized Output**: Creates structured folders for each comparison result
- **Error Handling**: Continues processing even if some alignments fail

**Command Line Usage:**

**PDF Mode (Complete Pipeline):**
```bash
python drawing_comparison.py old_drawings.pdf new_drawings.pdf --pdf-mode --debug
```

**PNG Folder Mode (Direct Comparison):**
```bash
python drawing_comparison.py old_folder/ new_folder/ --output results --debug
```

**Options:**
- `--pdf-mode`: Treat inputs as PDF files and run complete pipeline
- `--dpi 600`: Set DPI for PDF conversion (default: 300)
- `--output folder_name`: Base name for output folders
- `--debug`: Enable debug mode for alignment process

**Python API:**

**PDF Comparison (Complete Pipeline):**
```python
from drawing_comparison import compare_pdf_drawing_sets

# Complete pipeline: PDF → PNG → Match → Overlay
results = compare_pdf_drawing_sets(
    old_pdf_path="old_drawings.pdf",
    new_pdf_path="new_drawings.pdf", 
    dpi=300,
    debug=True
)

print(f"Found {results['matches_found']} matching drawings")
print(f"Created {results['successful_overlays']} overlays")
```

**PNG Folder Comparison (Direct):**
```python
from drawing_comparison import compare_drawing_sets

# Direct comparison of PNG folders
results = compare_drawing_sets(
    old_folder="old_pngs/",
    new_folder="new_pngs/",
    output_base="comparison_results",
    debug=True
)
```

**Output Structure:**
```
new_drawings_overlays/
├── A-001_overlay_results/
│   ├── A-001_old.png
│   ├── A-001_new.png
│   └── A-001_overlay.png
├── A-101_overlay_results/
│   ├── A-101_old.png
│   ├── A-101_new.png
│   └── A-101_overlay.png
└── ...
```

**Results Dictionary:**
```python
{
    'old_pdf': 'old_drawings.pdf',
    'new_pdf': 'new_drawings.pdf',
    'old_png_count': 5,
    'new_png_count': 6,
    'matches_found': 4,
    'successful_overlays': 3,
    'failed_overlays': 1,
    'output_folders': ['A-001_overlay_results/', 'A-101_overlay_results/'],
    'matches': [('A-001', 'old/A-001.png', 'new/A-001.png'), ...],
    'only_in_old': ['A-999'],
    'only_in_new': ['A-888', 'A-777']
}
```

### 6. OpenAI Change Analyzer (`openai_change_analyzer.py`)
Analyzes drawing overlays using OpenAI's API to generate comprehensive change lists.

**Features:**
- **AI-Powered Analysis**: Uses GPT-4 to analyze drawing changes
- **Automatic Detection**: Finds overlay folders and PNG files automatically
- **Structured Output**: Generates organized change lists and recommendations
- **Batch Processing**: Can analyze multiple overlay folders at once
- **JSON Export**: Saves results in structured JSON format

**Command Line Usage:**
```bash
# Analyze all overlays in a directory
python openai_change_analyzer.py test_new_overlays/

# Analyze single overlay folder
python openai_change_analyzer.py A-201_overlay_results

# Test with dummy data
python openai_change_analyzer.py --test
```

**Python API:**
```python
from openai_change_analyzer import OpenAIChangeAnalyzer

# Initialize analyzer (uses config.env automatically)
analyzer = OpenAIChangeAnalyzer()

# Analyze single overlay folder
result = analyzer.analyze_overlay_folder("A-201_overlay_results")
print(f"Found {len(result.changes_found)} changes")
print(f"Critical change: {result.critical_change}")

# Analyze multiple overlays
results = analyzer.analyze_multiple_overlays("test_new_overlays/")
analyzer.save_results(results, "test_new_overlays/")  # Saves individual JSON files in overlay directories
```

**Output Structure:**
```
test_new_overlays/
├── A-201_overlay_results/
│   ├── A-201_old.png
│   ├── A-201_new.png
│   ├── A-201_overlay.png
│   └── change_analysis_A-201.json    # Individual analysis file
├── A-101_overlay_results/
│   ├── A-101_old.png
│   ├── A-101_new.png
│   ├── A-101_overlay.png
│   └── change_analysis_A-101.json    # Individual analysis file
└── change_analysis_summary.json      # Summary of all analyses
```

**Individual Analysis File Example (`change_analysis_A-201.json`):**
```json
{
  "drawing_name": "A-201",
  "overlay_folder": "test_new_overlays/A-201_overlay_results",
  "success": true,
  "changes_found": [
    "Room 101 extended by 10 feet from 200 to 300 sq ft",
    "Door relocated from north to west wall",
    "Window added to south wall"
  ],
  "critical_change": "Major structural modification to Room 101",
  "recommendations": [
    "Update foundation plans for extended room",
    "Coordinate with structural engineer for load calculations"
  ],
  "analysis_summary": "Detailed AI analysis of the drawing changes..."
}
```

### 7. Complete Drawing Pipeline (`complete_drawing_pipeline.py`)
One-stop solution that runs the entire workflow from PDF files to AI-generated change lists.

**Features:**
- **Complete Workflow**: PDF → PNG → Overlay → AI Analysis in one command
- **Automatic Processing**: Handles all steps automatically
- **Flexible Options**: Can skip AI analysis or run with custom settings
- **Comprehensive Results**: Returns detailed results from all pipeline steps

**Command Line Usage:**
```bash
# Run complete pipeline
python complete_drawing_pipeline.py old_drawings.pdf new_drawings.pdf

# Run with custom settings
python complete_drawing_pipeline.py old.pdf new.pdf --dpi 600 --debug

# Skip AI analysis (overlays only)
python complete_drawing_pipeline.py old.pdf new.pdf --skip-ai

# Test with dummy data
python complete_drawing_pipeline.py --test
```

**Python API:**
```python
from complete_drawing_pipeline import complete_drawing_pipeline

# Run complete pipeline
results = complete_drawing_pipeline(
    old_pdf_path="old_drawings.pdf",
    new_pdf_path="new_drawings.pdf",
    dpi=300,
    debug=True,
    skip_ai_analysis=False
)

print(f"Created {results['summary']['overlays_created']} overlays")
print(f"Completed {results['summary']['analyses_completed']} AI analyses")
print(f"Total time: {results['summary']['total_time']:.1f} seconds")
```

**Pipeline Steps:**
1. **PDF Processing**: Converts both PDFs to PNG pages with drawing names
2. **Overlay Creation**: Creates alignment overlays for matching drawings
3. **AI Analysis**: Analyzes each overlay using OpenAI to generate change lists
4. **Results Organization**: Saves all results in organized directory structure

**Output Structure:**
```
new_drawings_overlays/
├── A-201_overlay_results/
│   ├── A-201_old.png
│   ├── A-201_new.png
│   ├── A-201_overlay.png
│   └── change_analysis_A-201.json
├── A-101_overlay_results/
│   ├── A-101_old.png
│   ├── A-101_new.png
│   ├── A-101_overlay.png
│   └── change_analysis_A-101.json
└── change_analysis_summary.json
```

## Installation

```bash
pip install -r requirements.txt
brew install tesseract poppler  # macOS system dependencies
```

## Configuration

### OpenAI API Setup

**The `config.env` file is already configured with your API key and will be loaded automatically.**

If you need to change settings, edit `config.env`:
```bash
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_MODEL=gpt-4o
DEFAULT_DPI=300
DEBUG_MODE=false
```

## Requirements

- Python 3.8+
- OpenCV
- NumPy
- Matplotlib
- PyMuPDF
- pytesseract
- pdf2image
- Pillow
# ATTEMPT-1: Advanced Captioning Pipeline

**Based on:** `captioning.txt` lines 18-28  
**Model:** Gemini 3-pro-preview for all captioning and API calls

---

## Overview

This implementation follows the ATTEMPT-1 approach for advanced drawing captioning:

1. **Upload 1 drawing**, segment it: legend, drawing, and two segments (right side)
2. **Convert 4 quadrants** and caption with support of separated legend
3. **Synthesize** quadrant captions + full drawing image for detailed drawing info (grid level)
4. **Full drawing caption** newly synthesized with detailed quadrant level info
5. **Perform search and retrieval** on this

---

## Steps

### Step 1: Segmentation
- Segment drawing into:
  - **Legend**: Right 20% of page
  - **Drawing**: Left 80% of page
  - **Right Top**: Top half of right side
  - **Right Bottom**: Bottom half of right side

### Step 2: Quadrant Captioning
- Create 4 quadrants (Q1-Q4)
- Caption legend first
- Caption each quadrant **with legend context** for symbol interpretation

### Step 3: Quadrant Synthesis
- Synthesize quadrant captions + full drawing image
- Extract **grid-level information** for every component
- Map components to grid locations (e.g., "Room 101 at Grid A1-B2")

### Step 4: Final Caption
- Create final full-drawing caption
- Incorporates all quadrant-level information
- Grid-level precision for component locations
- Optimized for search and retrieval

### Step 5: Search & Retrieval (TODO)
- Perform search and retrieval on synthesized captions

---

## Usage

### Prerequisites
```bash
pip install pdf2image pillow google-generativeai
export GOOGLE_API_KEY=your_key_here
```

### Run
```bash
python attempt1/attempt1_captioning.py \
  --pdf path/to/drawing.pdf \
  --page 0 \
  --dpi 300 \
  --output attempt1/output
```

### Arguments
- `--pdf`: Path to PDF drawing (required)
- `--page`: Zero-based page index (default: 0)
- `--dpi`: Rasterization DPI (default: 300)
- `--output`: Output directory (default: `attempt1/output`)

---

## Output Structure

```
attempt1/output/
└── <drawing_name>/
    ├── legend_caption.txt              # Step 2a: Legend caption
    ├── q1_top_left_caption.txt         # Step 2b: Quadrant captions
    ├── q2_top_right_caption.txt
    ├── q3_bottom_left_caption.txt
    ├── q4_bottom_right_caption.txt
    ├── quadrant_synthesis.txt          # Step 3: Grid-level synthesis
    ├── final_full_drawing_caption.txt  # Step 4: Final caption
    └── results.json                    # All results in JSON
```

---

## Key Features

- ✅ **Legend Support**: All quadrant captions use legend context
- ✅ **Grid-Level Detail**: Synthesis extracts grid locations for components
- ✅ **Multi-Stage Synthesis**: Progressive refinement from quadrants → synthesis → final
- ✅ **Gemini 3-pro-preview**: Best-in-class vision model for all operations
- ✅ **Comprehensive Output**: All intermediate and final results saved

---

## Next Steps

1. **Human Evaluation**: Review captions for information completeness
2. **Step 5 Implementation**: Add search and retrieval functionality
3. **ATTEMPT-2**: Update quadrants with relation to total information

---

**Last Updated:** December 12, 2025

# Overlay Generation Fix Summary

## Issues Fixed

### 1. **Missing Overlap Buffer (CRITICAL)**
**Problem**: Original implementation uses `overlap_buffer_px=2` to dilate masks before computing overlap, making alignment more forgiving.

**Fix Applied**: Added MaxFilter dilation with kernel size 5 (for 2px buffer):
```python
overlap_buffer_px = 2
if overlap_buffer_px and overlap_buffer_px > 0:
    k = int(max(1, 2 * overlap_buffer_px + 1))  # k=5
    A_dil = A_soft.filter(ImageFilter.MaxFilter(k))
    B_dil = B_soft.filter(ImageFilter.MaxFilter(k))
    overlap = ImageChops.darker(A_dil, B_dil)
```

**Impact**: This treats pixels within 2px of each other as "overlapping", creating cleaner gray regions and more accurate red/green distinction.

### 2. **Color Mapping**
**Corrected Colors**:
- **GREEN (0,255,0)**: Old drawing only (removed elements)
- **RED (255,0,0)**: New drawing only (added elements)
- **GRAY (200,200,200)**: Overlap (unchanged elements)
- **BLACK (20,20,20)**: Drawing lines preserved on top

### 3. **PDF Output**
Added PDF export matching reference format:
- Embedded PNG at correct dimensions
- 300 DPI to 72 DPI points conversion
- PyMuPDF (fitz) for PDF generation

## Files Updated

1. **`utils/image_utils.py`**
   - Added overlap buffer dilation
   - Fixed color mapping
   - Full PIL-based implementation with edge detection

2. **`processing/diff_pipeline.py`**
   - Added PDF output generation
   - PIL-based saving for quality

3. **`test_overlay_pdf.py`**
   - Test script for PNG + PDF generation

4. **`test_end_to_end.py`**
   - Added PDF output to E2E tests

## Implementation Details

### Overlay Algorithm (matching layer_overlay_2d.py):
1. Convert BGR → RGB → RGBA (PIL format)
2. Create soft ink masks with gamma=1.2
3. **Dilate masks with MaxFilter(5) for 2px buffer**
4. Compute overlap from dilated masks
5. Subtract from original masks for a_only/b_only
6. Composite colors on white background
7. Edge detection + line preservation (threshold=40)
8. Composite black lines on top
9. Convert back to BGR for OpenCV

### Key Parameters:
- `mask_gamma`: 1.2
- `alpha_gamma`: 1.0  
- `edge_threshold`: 40
- `overlap_buffer_px`: 2 ← **This was missing**
- `line_color`: (20, 20, 20)
- `overlap_color`: (200, 200, 200)

## Output Files

Generated in `testrun/`:
- `overlay_with_lines.png` - High-quality PNG overlay
- `overlay_with_lines.pdf` - PDF format matching reference

## Testing

Run test:
```bash
cd buildtrace-dev/backend
python3 test_overlay_pdf.py
```

Output should now match `testing/A-101/A-101_overlay.pdf` in:
- Color mapping (green for old, red for new)
- Gray overlap regions with proper buffering
- Black drawing lines preserved throughout
- Overall visual quality and appearance

## Next Steps

1. ✅ GPT calls disabled for alignment focus
2. ✅ Overlay logic fully migrated and fixed
3. ✅ PDF output implemented
4. ⏭️ Re-enable GPT OCR when ready
5. ⏭️ Test full pipeline with database integration
6. ⏭️ Deploy workers to Cloud Run

## Reference

Original implementation: `buildtrace-overlay-/layer_overlay_2d.py` lines 648-837
- Function: `_build_colored_overlay_image()`
- Key insight: PDF-based rendering at zoom=4.0 with overlap buffer dilation


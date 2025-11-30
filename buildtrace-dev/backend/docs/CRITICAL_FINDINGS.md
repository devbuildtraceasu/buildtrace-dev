# CRITICAL FINDINGS - Overlay Method Mismatch

## The Problem

**The reference overlays (`A-101_overlay.pdf`, `A-111_overlay.pdf`) were created using a DIFFERENT method than `drawing_comparison.py`!**

## Evidence

### Reference Overlay Analysis (`A-111_overlay.pdf`):

**Color Distribution:**
- **(232, 249, 232)** RGB - Greenish tint (most common - 5,771 samples)
- **(255, 255, 255)** RGB - White (3,355 samples)
- **(255, 0, 0)** RGB - Pure RED (90 samples)
- **(0, 196, 0)** RGB - Pure GREEN (120 samples)
- **(0, 0, 0)** RGB - BLACK drawing lines (138 samples)
- **(106, 0, 0)** RGB - Dark red (73 samples)
- **(214, 212, 190)** RGB - Beige/tan (271 samples)

**NO evidence of simple binary masking colors:**
- ❌ NO (255, 100, 100) light red
- ❌ NO (100, 255, 100) light green
- ❌ NO (150, 150, 150) gray

### Our Implementation (Using `image_utils.py` simple masking):

**Color Distribution:**
- 61.0% Light Red (100, 100, 255) BGR
- 2.1% Light Green (100, 255, 100) BGR
- 7.9% Gray (150, 150, 150) BGR
- 29.0% White (255, 255, 255) BGR

## Conclusion

**The reference overlays were created using:**
- ✅ `layer_overlay_2d.py` - PDF-based sophisticated overlay
- ✅ PIL soft masking with gamma correction
- ✅ Edge detection and line preservation
- ✅ Pure saturated colors (255,0,0 / 0,255,0)
- ✅ Black lines composited on top
- ✅ Color blending/tinting

**NOT created using:**
- ❌ `drawing_comparison.py` - PNG raster simple masking
- ❌ `image_utils.py` - Binary threshold overlay
- ❌ Light pastel colors

## What This Means

We need to use the **PDF layer overlay workflow** from `layer_overlay_2d.py`, specifically the `overlay_two_drawings()` or `_build_colored_overlay_image()` functions.

This approach:
1. Renders PDFs at high zoom (4x)
2. Uses PIL for soft ink masks
3. Applies edge detection
4. Preserves drawing lines in black
5. Uses pure RGB colors (255,0,0 / 0,255,0)
6. Applies color blending

## Next Steps

1. Implement `layer_overlay_2d.py` logic in buildtrace-dev
2. Use PDF-to-PDF workflow (not PNG-based)
3. Apply soft masking, edge detection, line preservation
4. Test with A-101 and A-111 PDFs to match reference


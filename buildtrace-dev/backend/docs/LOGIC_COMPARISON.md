# Logic Comparison: Raster vs Layer Overlay

## ✅ CURRENT IMPLEMENTATION (Correct - Raster Logic)

### File: `buildtrace-dev/backend/utils/image_utils.py`

```python
def create_overlay_image(old_img, new_img):
    """SIMPLE binary masking - RASTER LOGIC"""
    
    # 1. Convert to grayscale
    old_gray = cv2.cvtColor(old_img, cv2.COLOR_BGR2GRAY)
    new_gray = cv2.cvtColor(new_img, cv2.COLOR_BGR2GRAY)
    
    # 2. Binary masks (threshold at 240)
    old_content_mask = old_gray < 240
    new_content_mask = new_gray < 240
    
    # 3. Split regions
    old_only_mask = old_content_mask & ~new_content_mask
    new_only_mask = new_content_mask & ~old_content_mask
    common_mask = old_content_mask & new_content_mask
    
    # 4. Apply colors
    overlay[old_only_mask] = (100, 100, 255)  # BGR light pink/red
    overlay[new_only_mask] = (100, 255, 100)  # BGR light green
    overlay[common_mask] = (150, 150, 150)    # BGR gray
```

**Characteristics:**
- ✅ Pure OpenCV/NumPy
- ✅ Simple binary threshold (< 240)
- ✅ Light pastel colors
- ✅ NO PIL imports
- ✅ NO edge detection
- ✅ NO line preservation
- ✅ NO soft masks
- ✅ NO gamma correction

**Verification:**
```bash
$ grep -E "from PIL|ImageChops|ImageFilter|soft_ink|edge_threshold" \
  buildtrace-dev/backend/utils/image_utils.py
# Result: No matches found ✅
```

---

## ❌ WRONG APPROACH (layer_overlay_2d.py - NOT USED)

### File: `buildtrace-overlay-/layer_overlay_2d.py`

```python
def _build_colored_overlay_image(pdf_a, pdf_b, ...):
    """PDF-based overlay with PIL - LAYER OVERLAY LOGIC"""
    from PIL import Image, ImageChops, ImageFilter, ImageOps
    
    # 1. Render PDFs at zoom=4.0
    img_a = page_a.get_pixmap(matrix=mat_a).pil_image()
    img_b = page_b.get_pixmap(matrix=mat_b).pil_image()
    
    # 2. Soft ink masks with gamma
    A_soft = _soft_ink_mask_from_rgba(img_a, mask_gamma=1.2, alpha_gamma=1.0)
    B_soft = _soft_ink_mask_from_rgba(img_b, mask_gamma=1.2, alpha_gamma=1.0)
    
    # 3. Overlap buffer dilation
    k = int(max(1, 2 * overlap_buffer_px + 1))
    A_dil = A_soft.filter(ImageFilter.MaxFilter(k))
    B_dil = B_soft.filter(ImageFilter.MaxFilter(k))
    overlap = ImageChops.darker(A_dil, B_dil)
    
    # 4. Edge detection for line preservation
    edges_a = ImageOps.autocontrast(gray_a.filter(ImageFilter.FIND_EDGES))
    edges_b = ImageOps.autocontrast(gray_b.filter(ImageFilter.FIND_EDGES))
    
    # 5. Alpha composite lines on top
    lines_rgba = lines_rgb.convert("RGBA")
    lines_rgba.putalpha(line_mask)
    base_rgba = Image.alpha_composite(base_rgba, lines_rgba)
```

**Characteristics:**
- ❌ Requires PIL/Pillow
- ❌ PDF rendering at high zoom
- ❌ Soft ink masks with gamma
- ❌ Edge detection (FIND_EDGES)
- ❌ Line preservation (alpha compositing)
- ❌ Overlap buffer dilation
- ❌ Pure saturated colors (255,0,0 / 0,255,0)
- ❌ Complex multi-layer compositing

**This approach is NOT used for drawing_comparison.py!**

---

## Side-by-Side Comparison

| Feature | Raster Logic (✅ Used) | Layer Overlay (❌ Not Used) |
|---------|----------------------|---------------------------|
| **Import PIL** | No | Yes |
| **Input** | PNG files | PDF files |
| **Rendering** | Direct cv2.imread | PDF render at zoom=4x |
| **Masking** | Binary threshold < 240 | Soft ink mask with gamma |
| **Colors** | Light tints (100,100,255) | Pure saturated (255,0,0) |
| **Edge Detection** | No | Yes (FIND_EDGES) |
| **Line Preservation** | No | Yes (alpha composite) |
| **Overlap Buffer** | No | Yes (MaxFilter dilation) |
| **Complexity** | ~40 lines | ~200 lines |
| **Used By** | drawing_comparison.py | layer_overlay_2d.py standalone |

---

## Color Values Comparison

### Raster Logic (✅ Correct - Used by drawing_comparison.py)

| Region | BGR Value | RGB Value | Appearance |
|--------|-----------|-----------|------------|
| Old only | (100, 100, 255) | (255, 100, 100) | Light pink/red (pastel) |
| New only | (100, 255, 100) | (100, 255, 100) | Light green (pastel) |
| Common | (150, 150, 150) | (150, 150, 150) | Medium gray |

### Layer Overlay (❌ NOT Used)

| Region | RGB Value | Appearance |
|--------|-----------|------------|
| A only | (255, 0, 0) | Pure saturated red |
| B only | (0, 255, 0) | Pure saturated green |
| Overlap | (200, 200, 200) | Light gray |
| Lines | (20, 20, 20) | Near black (composited on top) |

---

## Workflow Comparison

### ✅ drawing_comparison.py (Raster - CORRECT)

```
1. PDF Input
   ↓
2. process_pdf_with_drawing_names() → PNG files (300 DPI)
   ↓
3. load_image() → cv2.imread
   ↓
4. AlignDrawings()(old, new) → SIFT alignment
   ↓
5. create_overlay_image() → SIMPLE binary masking
   ↓
6. cv2.imwrite() → Save PNG
```

**No PIL, no PDF rendering, no edge detection!**

### ❌ layer_overlay_2d.py (Layer - WRONG for drawing_comparison)

```
1. PDF Input
   ↓
2. Open PDF directly with fitz
   ↓
3. Render pages at zoom=4x → PIL Image
   ↓
4. Soft ink masks → PIL operations
   ↓
5. Edge detection → PIL FIND_EDGES
   ↓
6. Alpha composite → PIL alpha_composite
   ↓
7. Save as PDF with show_pdf_page()
```

**Heavy PIL usage, PDF-to-PDF workflow!**

---

## Verification Checklist

### ✅ Current Implementation Verified:

- [x] No PIL imports in `utils/image_utils.py`
- [x] Uses simple `cv2.cvtColor` + binary masking
- [x] Color values match original: (100,100,255), (100,255,100), (150,150,150)
- [x] No edge detection code
- [x] No soft mask functions
- [x] No ImageFilter, ImageChops, or ImageOps
- [x] No alpha compositing
- [x] No overlap buffer dilation
- [x] Matches `buildtrace-overlay-/image_utils.py` exactly

### ❌ NOT Using layer_overlay_2d.py:

- [x] No `_soft_ink_mask_from_rgba` function
- [x] No `_build_colored_overlay_image` function
- [x] No PIL Image operations
- [x] No edge detection filters
- [x] No line mask compositing
- [x] No PDF rendering at zoom
- [x] No gamma correction

---

## Conclusion

✅ **CONFIRMED: Using RASTER logic (drawing_comparison.py workflow)**

Our implementation correctly uses:
- Simple PNG-based comparison (not PDF layer-based)
- Binary masking with OpenCV (not PIL soft masks)
- Light pastel colors (not saturated colors)
- No edge detection or line preservation

This matches the original `buildtrace-overlay-/drawing_comparison.py` exactly!

The color issues were because I was initially trying to implement layer_overlay_2d.py logic,
which is a completely different approach for PDF vector overlays, not PNG raster comparison.

**The fix: Use simple raster logic from image_utils.py, NOT layer_overlay_2d.py!**


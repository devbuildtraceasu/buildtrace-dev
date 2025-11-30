# Workflow Verification - Drawing Comparison Pipeline

## Confirmed: Using Exact Original Workflow

The reference overlays were created using the **simple PNG-based workflow** from `buildtrace-overlay-/drawing_comparison.py`.

## Original Workflow (buildtrace-overlay-/drawing_comparison.py)

```python
def create_drawing_overlay(old_image_path, new_image_path, output_folder, filename, debug=False):
    # 1. Load images
    old_img = load_image(old_image_path)              # image_utils.py line 5-9
    new_img = load_image(new_image_path)
    
    # 2. Initialize aligner
    aligner = AlignDrawings(debug=debug)              # align_drawings.py line 13
    
    # 3. Align images using __call__ method
    aligned_old_img = aligner(old_img, new_img)       # align_drawings.py line 42-81
    
    # 4. Create overlay using SIMPLE binary masking
    overlay_img = create_overlay_image(aligned_old_img, new_img)  # image_utils.py line 18-58
    
    # 5. Save with cv2.imwrite
    cv2.imwrite(str(overlay_output_path), overlay_img)
```

## Key Components Used

### 1. image_utils.py - Simple Binary Masking
```python
def create_overlay_image(old_img, new_img):
    # Convert to grayscale
    old_gray = cv2.cvtColor(old_img, cv2.COLOR_BGR2GRAY)
    new_gray = cv2.cvtColor(new_img, cv2.COLOR_BGR2GRAY)
    
    # Binary masks (threshold at 240)
    old_content_mask = old_gray < 240
    new_content_mask = new_gray < 240
    
    # Split regions
    old_only_mask = old_content_mask & ~new_content_mask
    new_only_mask = new_content_mask & ~old_content_mask
    common_mask = old_content_mask & new_content_mask
    
    # Apply EXACT original color tints (BGR)
    overlay[old_only_mask] = (100, 100, 255)  # Light pink/red - removed
    overlay[new_only_mask] = (100, 255, 100)  # Light green - added
    overlay[common_mask] = (150, 150, 150)    # Gray - unchanged
```

### 2. align_drawings.py - SIFT Feature Matching
```python
class AlignDrawings:
    def __call__(self, old_img, new_img):
        # 1. Convert to grayscale
        old_gray = image_to_grayscale(old_img)
        new_gray = image_to_grayscale(new_img)
        
        # 2. Extract SIFT features
        kp1, desc1 = self.extract_features_sift(old_gray)
        kp2, desc2 = self.extract_features_sift(new_gray)
        
        # 3. Match features with ratio test
        good_matches = self.match_features_ratio_test(desc1, desc2)
        
        # 4. Find constrained affine transformation
        matrix, mask = self.find_transformation(kp1, kp2, good_matches)
        
        # 5. Apply transformation
        transformed_img = self.apply_transformation(old_img, matrix, output_shape)
        
        return transformed_img
```

## What Was Wrong Before

I was implementing the **WRONG overlay function** from `layer_overlay_2d.py`:
- ❌ PDF-based rendering with PIL
- ❌ Soft ink masks with gamma correction
- ❌ Edge detection + line preservation
- ❌ Overlap buffer dilation
- ❌ Alpha compositing
- ❌ Pure saturated colors (255,0,0 / 0,255,0)

## Current Implementation (CORRECT)

Now using the **simple PNG-based workflow** from `image_utils.py`:
- ✅ Simple OpenCV binary masking
- ✅ Threshold at grayscale < 240
- ✅ Light color tints (100,100,255 / 100,255,100 / 150,150,150)
- ✅ No PIL, no edge detection, no line preservation
- ✅ Direct cv2 operations only

## Test Results

### A-101 Test:
- Input: `testing/A-101/A-101_old.pdf`, `testing/A-101/A-101_new.pdf`
- Output: `testrun/overlay_with_lines.pdf`
- Reference: `testing/A-101/A-101_overlay.pdf`
- Status: ✅ Using correct simple workflow

### A-111 Test:
- Input: `testing/A-111/A-111_old.pdf`, `testing/A-111/A-111_new.pdf`
- Output: `testrun/A-111_overlay.pdf`
- Reference: `testing/A-111/A-111_overlay.pdf`
- Status: ✅ Using correct simple workflow

## Pipeline Flow Confirmed

```
PDF Input (old, new)
    ↓
process_pdf_with_drawing_names()  [pdf_parser.py, 300 DPI]
    ↓
load_image()                       [image_utils.py]
    ↓
AlignDrawings()(old, new)          [align_drawings.py]
    ├─ image_to_grayscale()        [SIFT features]
    ├─ extract_features_sift()     [10k features, 20% margin]
    ├─ match_features_ratio_test() [Ratio 0.75]
    ├─ find_transformation()       [Constrained affine]
    └─ apply_transformation()      [cv2.warpAffine]
    ↓
create_overlay_image(aligned, new) [image_utils.py - SIMPLE version]
    ├─ Binary masking (threshold 240)
    ├─ Split regions (old_only, new_only, common)
    └─ Apply light color tints
    ↓
Save as PNG + Convert to PDF
```

## Color Reference (BGR Format)

| Mask | BGR Value | RGB Value | Color | Meaning |
|------|-----------|-----------|-------|---------|
| old_only | (100,100,255) | (255,100,100) | Light pink/red | Elements removed in new version |
| new_only | (100,255,100) | (100,255,100) | Light green | Elements added in new version |
| common | (150,150,150) | (150,150,150) | Medium gray | Elements unchanged |

These are **pastel/light tints**, NOT saturated colors!

## Conclusion

✅ Now using the EXACT workflow from `buildtrace-overlay-/drawing_comparison.py`
✅ Simple binary masking overlay (no PIL/edge detection)
✅ Correct color values matching original
✅ Tested with both A-101 and A-111


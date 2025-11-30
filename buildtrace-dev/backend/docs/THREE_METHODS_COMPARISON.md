# Three Methods Comparison Results

## Test Results Summary

### A-101 Comparison

| Metric | Reference | Method 1 (Simple) | Method 2 (PIL Soft) | Method 3 (Channel) |
|--------|-----------|-------------------|---------------------|-------------------|
| **White** | 75.8% | 82.1% | 80.2% | 82.2% |
| **Light Red (100,100,255)** | 0% | 15.2% | 0% | 1.6% |
| **Light Green (100,255,100)** | 0% | 1.5% | 0% | 1.3% |
| **Pure Red (0,0,255)** | **0.3%** | 0% | **1.8%** ✅ | 0% |
| **Pure Green (0,255,0)** | 0% | 0% | **0.1%** ✅ | 0% |
| **Gray (150,150,150)** | 0% | 1.2% | 0% | 0% |
| **Gray (200,200,200)** | 0% | 0% | **0.1%** ✅ | 0% |
| **Black (0,0,0)** | **1.6%** | 0% | **0.4%** ✅ | 0% |

### A-111 Comparison

| Metric | Reference | Method 1 (Simple) | Method 2 (PIL Soft) | Method 3 (Channel) |
|--------|-----------|-------------------|---------------------|-------------------|
| **White** | 30.1% | 29.0% | 28.4% | 29.0% |
| **Light Red (100,100,255)** | 0% | 61.0% ❌ | 0% | 61.0% ❌ |
| **Light Green (100,255,100)** | 0% | 2.1% | 0% | 2.1% |
| **Pure Red (0,0,255)** | **0.9%** | 0% | **1.3%** ✅ | 0% |
| **Pure Green (0,255,0)** | 0% | 0% | **1.1%** ✅ | 0% |
| **Gray (150,150,150)** | 0% | 7.9% ❌ | 0% | 0% |
| **Gray (200,200,200)** | 0% | 0% | **1.0%** ✅ | 0% |
| **Black (0,0,0)** | **0.8%** | 0% | 0% ⚠️ | 0% |

## Analysis

### ✅ METHOD 2 (PIL Soft Mask) - CLOSEST MATCH

**Why it's closest:**
- ✅ Uses PURE colors (255,0,0 RED and 0,255,0 GREEN) like reference
- ✅ Has BLACK lines (A-101: 0.4% vs ref 1.6%)
- ✅ Uses soft masking and edge detection
- ✅ Color percentages in similar range to reference

**Differences:**
- ⚠️ A-111 missing black lines (0% vs 0.8% in ref)
- ⚠️ Slightly higher color percentages than reference
- ⚠️ May need tuning of edge threshold or mask gamma

### ❌ METHOD 1 (Simple Binary) - WRONG

**Why it doesn't match:**
- ❌ Uses LIGHT colors (100,100,255) instead of PURE colors
- ❌ NO black lines preserved
- ❌ A-111 shows 61% light red - completely wrong!
- ❌ Binary threshold too crude

### ❌ METHOD 3 (Channel Based) - PARTIAL

**Why it doesn't match:**
- ❌ Uses LIGHT colors (100,100,255) like Method 1
- ❌ NO black lines preserved
- ⚠️ Better than Method 1 for A-101 but still wrong

## Color Codes Used

### Reference Overlays:
- **Pure Red (255, 0, 0)** - Old elements removed
- **Pure Green (0, 255, 0)** - New elements added
- **Black (0, 0, 0)** - Drawing lines preserved
- **Gray/Beige blends** - Soft overlapping regions
- **White (255, 255, 255)** - Background

### Method 1 (Simple Binary):
- Light Red (100, 100, 255) BGR
- Light Green (100, 255, 100) BGR
- Gray (150, 150, 150) BGR
- **WRONG COLORS!**

### Method 2 (PIL Soft Mask):
- **Pure Red (255, 0, 0)** RGB ✅
- **Pure Green (0, 255, 0)** RGB ✅
- **Black (0, 0, 0)** for lines ✅
- Gray (200, 200, 200)
- **CORRECT COLORS!**

### Method 3 (Channel Based):
- Light Red (100, 100, 255) BGR
- Light Green (100, 255, 100) BGR
- **WRONG COLORS!**

## Recommendation

**Use METHOD 2 (PIL Soft Mask) as the baseline, but needs refinement:**

1. **Increase edge detection sensitivity** to capture more black lines in A-111
2. **Adjust mask_gamma** to reduce color saturation
3. **Fine-tune overlap_buffer_px** for better blending
4. **Verify edge_threshold** is appropriate for all drawings

## Output Files

All test outputs saved to:
- `testrun/A-101/`
  - `A-101_METHOD_1_SimpleBinary.png/.pdf`
  - `A-101_METHOD_2_PILSoftMask.png/.pdf` ← **CLOSEST MATCH**
  - `A-101_METHOD_3_ChannelBased.png/.pdf`

- `testrun/A-111/`
  - `A-111_METHOD_1_SimpleBinary.png/.pdf`
  - `A-111_METHOD_2_PILSoftMask.png/.pdf` ← **CLOSEST MATCH**
  - `A-111_METHOD_3_ChannelBased.png/.pdf`

Compare these with the references:
- `testing/A-101/A-101_overlay.pdf`
- `testing/A-111/A-111_overlay.pdf`

## Next Steps

1. ✅ Confirm METHOD_2 visually matches references best
2. 🔧 Fine-tune METHOD_2 parameters:
   - Edge threshold (currently 40, try 30-50)
   - Mask gamma (currently 1.2, try 1.0-1.5)
   - Alpha gamma (currently 1.0, try 0.8-1.2)
   - Overlap buffer (currently 2px, try 1-3px)
3. 🎯 Implement METHOD_2 as the default overlay function
4. 🧪 Test on more drawings to validate


"""
Extract drawing names (e.g., A-101, A 101, A-344-MB) from every page of a PDF.

Strategy:
1) Try direct text extraction via PyMuPDF (vector/text PDFs -> no OCR, very accurate).
   - Choose the candidate nearest to the bottom-right of the page.
2) If none found, render page and OCR the bottom-right "title block" region.

Deps (install if needed):
  pip install pymupdf pillow pytesseract
Also install Tesseract on your system (macOS: brew install tesseract).
"""

import sys, re, io
import fitz  # PyMuPDF
from PIL import Image
Image.MAX_IMAGE_PIXELS = None  # Remove PIL decompression bomb limit
import pytesseract

# Regex to match drawing names like A-101, A 101, A-344-MB, S-12A, A2.1, A1.1, B-S01, A20-01, etc.
# Supports: traditional (A-101), decimal (A2.1), multi-part prefix (B-S01, A20-01), with letters (S-12A)
DRAWING_RE = re.compile(r"\b([A-Z]\d*)[-\s]?(\d{1,4}(?:\.\d{1,2})?|[A-Z]\d{1,4}(?:\.\d{1,2})?)([A-Z])?(?:-([A-Z0-9]{1,8}))?\b")

def normalize_dwg(text: str, token_match: re.Match) -> str:
    """Preserve original format (A2.1 stays A2.1, A-101 stays A-101, B-S01 stays B-S01)"""
    prefix = token_match.group(1)           # Group 1: A, B, A20, S10
    number = token_match.group(2)           # Group 2: 101, S01, 2.1
    direct_letter = token_match.group(3)    # Group 3: Single letter after number (A in S-12A)
    hyphen_suffix = token_match.group(4)    # Group 4: Suffix after hyphen (-REV, -MB)
    
    # Find the original separator between prefix and number
    start_pos = token_match.start()
    number_start = token_match.start(2)
    separator = text[start_pos + len(prefix):number_start]
    
    # Build the result preserving the original separator
    result = prefix + separator + number
    
    # Add direct letter if present (like A in S-12A)
    if direct_letter:
        result += direct_letter
    
    # Add hyphen suffix if present (like REV in A2.1-REV)
    if hyphen_suffix:
        result += '-' + hyphen_suffix
    
    return result

def words_to_candidates(words, page_rect, page=None):
    """
    Given PyMuPDF word tuples and page rect, return list of
    (normalized_candidate, center_x, center_y, font_size).
    """
    cands = []
    
    # Get font size information if page is provided
    font_sizes = {}
    font_by_y_position = {}  # Store font size by Y-coordinate for same-line lookup
    if page:
        try:
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text = span["text"]
                            size = span["size"]
                            bbox = span["bbox"]
                            cx = 0.5 * (bbox[0] + bbox[2])
                            cy = 0.5 * (bbox[1] + bbox[3])
                            # Store font size keyed by approximate position and text
                            key = (round(cx), round(cy), text.strip())
                            font_sizes[key] = size
                            # Also store by Y-coordinate (±2 pixels) for same-line lookup
                            # This helps when "SHEET B-S01" and "B-S01" are on same line but different X
                            y_key = round(cy/2)*2  # Round to nearest 2 pixels
                            if y_key not in font_by_y_position or size > font_by_y_position[y_key]:
                                font_by_y_position[y_key] = size
        except:
            pass
    
    # words: list of (x0, y0, x1, y1, "text", block_no, line_no, word_no)
    for (x0, y0, x1, y1, text, *_rest) in words:
        for m in DRAWING_RE.finditer(text):
            cand = normalize_dwg(text, m)
            cx = 0.5 * (x0 + x1)
            cy = 0.5 * (y0 + y1)
            # Try to find font size
            font_size = 0
            if font_sizes:
                key = (round(cx), round(cy), text.strip())
                font_size = font_sizes.get(key, 0)
                # If not found, try Y-coordinate lookup (for cases like "SHEET B-S01" split to "B-S01")
                if font_size == 0 and font_by_y_position:
                    y_key = round(cy/2)*2
                    font_size = font_by_y_position.get(y_key, 0)
            cands.append((cand, cx, cy, font_size))
    
    # Also try line-level text in blocks (sometimes indices are split across words)
    # We concatenate words per line and re-scan; map the match near the line's bbox center.
    # Build per-line text quickly:
    from collections import defaultdict
    lines = defaultdict(list)
    for (x0, y0, x1, y1, text, block_no, line_no, _wno) in words:
        lines[(block_no, line_no)].append((x0, y0, x1, y1, text))
    for (_blk, _ln), items in lines.items():
        items.sort(key=lambda t: t[0])  # by x
        line_text = " ".join(t[4] for t in items)
        match = DRAWING_RE.search(line_text)
        if match:
            cand = normalize_dwg(line_text, match)
            # use the overall line bbox center
            lx0 = min(t[0] for t in items); ly0 = min(t[1] for t in items)
            lx1 = max(t[2] for t in items); ly1 = max(t[3] for t in items)
            cx = 0.5*(lx0+lx1)
            cy = 0.5*(ly0+ly1)
            # Try to find font size for this line
            font_size = 0
            if font_sizes:
                for item in items:
                    text_item = item[4].strip()
                    item_cx = 0.5 * (item[0] + item[2])
                    item_cy = 0.5 * (item[1] + item[3])
                    key = (round(item_cx), round(item_cy), text_item)
                    if key in font_sizes:
                        font_size = max(font_size, font_sizes[key])
                # If still not found, try Y-coordinate lookup
                if font_size == 0 and font_by_y_position:
                    y_key = round(cy/2)*2
                    font_size = font_by_y_position.get(y_key, 0)
            cands.append((cand, cx, cy, font_size))
    return cands

def pick_bottom_right(candidates, page_rect):
    """
    Prefer candidates nearest to bottom-right corner with largest font size.
    Drawing numbers in title blocks are typically the largest text in the bottom-right area.
    Score = font_size_weight + position_weight, higher is better.
    """
    if not candidates:
        return None
    w = page_rect.width
    h = page_rect.height
    
    # Extract font sizes to normalize
    font_sizes = []
    for item in candidates:
        if len(item) >= 4:
            font_sizes.append(item[3])
        else:
            font_sizes.append(0)
    
    max_font_size = max(font_sizes) if font_sizes else 1
    if max_font_size == 0:
        max_font_size = 1
    
    best = None
    best_score = -1e9
    
    for i, item in enumerate(candidates):
        if len(item) >= 4:
            cand, cx, cy, font_size = item[0], item[1], item[2], item[3]
        else:
            cand, cx, cy = item[0], item[1], item[2]
            font_size = 0
        
        # Normalize font size (0-1 range)
        norm_font_size = font_size / max_font_size if max_font_size > 0 else 0
        
        # Position score (0-2 range: 0-1 for x, 0-1 for y)
        position_score = (cx / w) + (cy / h)
        
        # Combined score: font size is weighted heavily (3x) since drawing numbers are largest
        # Font size: 0-3, Position: 0-2, Total: 0-5
        score = (norm_font_size * 3.0) + position_score
        
        if score > best_score:
            best_score = score
            best = cand
    
    return best

def ocr_bottom_right(page, frac_left=0.70, frac_top=0.76):
    """
    Render page to image, crop bottom-right region by fractions, OCR it,
    and extract a drawing name.
    """
    # Render at higher resolution to help OCR
    zoom = 2.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, annots=False)
    img = Image.open(io.BytesIO(pix.tobytes("png")))

    W, H = img.size
    crop_box = (int(W * frac_left), int(H * frac_top), W, H)
    crop = img.crop(crop_box)

    text = pytesseract.image_to_string(crop, config="--psm 6")
    m = DRAWING_RE.search(text)
    return normalize_dwg(text, m) if m else None

def extract_drawing_names(pdf_path):
    doc = fitz.open(pdf_path)
    results = []
    for i, page in enumerate(doc, start=1):
        # 1) Try text extraction with positions
        words = page.get_text("words")
        cands = words_to_candidates(words, page.rect, page)
        chosen = pick_bottom_right(cands, page.rect)

        # 2) Fallback: OCR bottom-right region
        if not chosen:
            chosen = ocr_bottom_right(page)

        results.append({"page": i, "drawing_name": chosen})
    return results

def main():
    if len(sys.argv) < 2:
        print("Usage: python extract_drawings.py <file.pdf>")
        sys.exit(1)
    pdf_path = sys.argv[1]
    print(f"Processing PDF: {pdf_path}")
    
    try:
        out = extract_drawing_names(pdf_path)
        print(f"Found {len(out)} pages")

        # Print a clean list
        for row in out:
            print(f"Page {row['page']:>3}: {row['drawing_name'] or '[not found]'}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

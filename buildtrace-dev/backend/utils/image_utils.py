"""
Image Utilities for Drawing Processing
Handles image loading, grayscale conversion, and overlay creation
"""

import cv2
import numpy as np
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

try:
    from PIL import Image, ImageChops, ImageFilter, ImageOps
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("PIL/Pillow not available. Advanced overlay features disabled.")

def load_image(path: str) -> np.ndarray:
    """Load image from file path"""
    img = cv2.imread(path)
    if img is None:
        raise FileNotFoundError(f"Could not load image from {path}")
    return img

def image_to_grayscale(img: np.ndarray) -> np.ndarray:
    """Convert image to grayscale and invert"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.bitwise_not(gray)
    return gray

def _soft_ink_mask_from_rgba(img_rgba, mask_gamma: float = 1.2, alpha_gamma: float = 1.0):
    """Return a soft ink mask (L, 0..255) proportional to darkness and alpha.
    
    This matches the logic from layer_overlay_2d.py _soft_ink_mask_from_rgba.
    ink = ((1 - luminance) ** mask_gamma) * (alpha ** alpha_gamma)
    
    Args:
        img_rgba: PIL Image in RGBA mode
        mask_gamma: Gamma correction for darkness component
        alpha_gamma: Gamma correction for alpha component
        
    Returns:
        PIL Image in L mode (grayscale mask)
    """
    gray = img_rgba.convert("L")
    alpha = img_rgba.getchannel("A")
    
    # Darkness component: 255 - gray
    darkness = ImageChops.invert(gray)
    
    # Apply gamma LUTs
    def _build_lut(gamma: float):
        if gamma is None or abs(gamma - 1.0) < 1e-6:
            return [i for i in range(256)]
        return [int(round(((i / 255.0) ** gamma) * 255)) for i in range(256)]
    
    darkness_gamma = darkness.point(_build_lut(mask_gamma))
    alpha_gamma_img = alpha.point(_build_lut(alpha_gamma))
    
    # Multiply darkness and alpha (PIL multiply scales by 255 automatically)
    ink = ImageChops.multiply(darkness_gamma, alpha_gamma_img)
    return ink  # L image


def create_overlay_image(
    old_img: np.ndarray, 
    new_img: np.ndarray,
    mask_gamma: float = 1.2,
    alpha_gamma: float = 1.0,
    edge_threshold: int = 40,
    draw_lines: bool = True,
    line_color: Tuple[int, int, int] = (0, 0, 0),  # Pure black
    overlap_color: Tuple[int, int, int] = (200, 200, 200),
    overlap_buffer_px: int = 2
) -> np.ndarray:
    """Create overlay using PIL soft masking with edge detection and line preservation.
    
    This matches the reference overlays (A-101, A-111) which use layer_overlay_2d.py logic:
    - Soft ink masks with gamma correction
    - Edge detection for line preservation
    - Pure saturated colors (RED 255,0,0 and GREEN 0,255,0)
    - Black drawing lines composited on top
    
    Colors (RGB format):
    - Pure Red (255, 0, 0): Old elements that were removed
    - Pure Green (0, 255, 0): New elements that were added
    - Gray (200, 200, 200): Unchanged/overlapping elements
    - Black (0, 0, 0): Drawing lines preserved on top
    
    Args:
        old_img: Aligned old drawing (BGR from OpenCV)
        new_img: New drawing (BGR from OpenCV)
        mask_gamma: Gamma correction for soft mask (default 1.2)
        alpha_gamma: Gamma correction for alpha channel (default 1.0)
        edge_threshold: Threshold for edge detection (default 40)
        draw_lines: Whether to preserve drawing lines (default True)
        line_color: Color for preserved lines (default black)
        overlap_color: Color for overlapping regions (default gray 200,200,200)
        overlap_buffer_px: Buffer pixels for overlap dilation (default 2)
        
    Returns:
        Overlay image (BGR) with soft masking and line preservation
    """
    if not PIL_AVAILABLE:
        logger.warning("PIL not available, falling back to simple overlay")
        return _create_overlay_simple(old_img, new_img)
    
    try:
        # Ensure images match
        if old_img.shape != new_img.shape:
            logger.warning(f"Image size mismatch: old {old_img.shape} vs new {new_img.shape}, resizing")
            new_img = cv2.resize(new_img, (old_img.shape[1], old_img.shape[0]), interpolation=cv2.INTER_AREA)

        # Resize if extremely large (memory limit)
        max_dimension = 15000
        if old_img.shape[0] > max_dimension or old_img.shape[1] > max_dimension:
            scale = max_dimension / max(old_img.shape[0], old_img.shape[1])
            new_size = (int(old_img.shape[1] * scale), int(old_img.shape[0] * scale))
            logger.info(f"Resizing for overlay: {old_img.shape[:2]} -> {new_size[::-1]}")
            old_img = cv2.resize(old_img, new_size, interpolation=cv2.INTER_AREA)
            new_img = cv2.resize(new_img, new_size, interpolation=cv2.INTER_AREA)

        # Convert BGR to RGB for PIL, then to RGBA
        old_rgb = cv2.cvtColor(old_img, cv2.COLOR_BGR2RGB)
        new_rgb = cv2.cvtColor(new_img, cv2.COLOR_BGR2RGB)
        img_a = Image.fromarray(old_rgb).convert("RGBA")
        img_b = Image.fromarray(new_rgb).convert("RGBA")
        
        h, w = old_img.shape[:2]
        
        # Build soft ink masks (L 0..255) using opacity and luminance
        A_soft = _soft_ink_mask_from_rgba(img_a, mask_gamma=mask_gamma, alpha_gamma=alpha_gamma)
        B_soft = _soft_ink_mask_from_rgba(img_b, mask_gamma=mask_gamma, alpha_gamma=alpha_gamma)
        
        # Split into overlap and exclusive contributions
        # If a buffer is requested, dilate masks before computing overlap
        if overlap_buffer_px and overlap_buffer_px > 0:
            try:
                k = int(max(1, 2 * overlap_buffer_px + 1))
                A_dil = A_soft.filter(ImageFilter.MaxFilter(k))
                B_dil = B_soft.filter(ImageFilter.MaxFilter(k))
                overlap = ImageChops.darker(A_dil, B_dil)
            except Exception:
                logger.warning("Overlap buffer dilation failed, using direct overlap")
                overlap = ImageChops.darker(A_soft, B_soft)
        else:
            overlap = ImageChops.darker(A_soft, B_soft)
        
        a_only = ImageChops.subtract(A_soft, overlap)
        b_only = ImageChops.subtract(B_soft, overlap)
        
        # Compose colored result on white background
        # NOTE: Colors match reference - RED for old (removed), GREEN for new (added)
        base = Image.new("RGB", (w, h), color=(255, 255, 255))
        red = Image.new("RGB", (w, h), color=(255, 0, 0))      # Pure RED
        green = Image.new("RGB", (w, h), color=(0, 255, 0))  # Pure GREEN
        gray_color = Image.new("RGB", (w, h), color=overlap_color)
        
        base = Image.composite(red, base, a_only)      # Old/removed elements → RED
        base = Image.composite(green, base, b_only)    # New/added elements → GREEN
        base = Image.composite(gray_color, base, overlap)  # Overlap → GRAY
        
        # Edge-preserving line overlay to keep strokes visible
        if draw_lines:
            gray_a = img_a.convert("L")
            gray_b = img_b.convert("L")
            
            # Edge detection and emphasis
            edges_a = ImageOps.autocontrast(gray_a.filter(ImageFilter.FIND_EDGES))
            edges_b = ImageOps.autocontrast(gray_b.filter(ImageFilter.FIND_EDGES))
            
            # Weight edges by ink presence to avoid noise from backgrounds
            edges_a = ImageChops.multiply(edges_a, ImageOps.autocontrast(A_soft))
            edges_b = ImageChops.multiply(edges_b, ImageOps.autocontrast(B_soft))
            
            # Threshold edges
            def _edge_threshold(img_l: Image.Image, th: int):
                th = max(0, min(255, int(th)))
                return img_l.point(lambda v: 0 if v < th else v)
            
            edge_mask_a = _edge_threshold(edges_a, edge_threshold)
            edge_mask_b = _edge_threshold(edges_b, edge_threshold)
            
            # Combine both line masks - use lighter to get all lines from both images
            line_mask = ImageChops.lighter(edge_mask_a, edge_mask_b)
            
            # Draw lines on top with variable alpha from line_mask
            base_rgba = base.convert("RGBA")
            lines_rgb = Image.new("RGB", (w, h), color=line_color)
            lines_rgba = lines_rgb.convert("RGBA")
            lines_rgba.putalpha(line_mask)
            base_rgba = Image.alpha_composite(base_rgba, lines_rgba)
            base = base_rgba.convert("RGB")
        
        # Convert back to numpy array and BGR for OpenCV compatibility
        result_array = np.array(base)
        overlay_bgr = cv2.cvtColor(result_array, cv2.COLOR_RGB2BGR)
        
        return overlay_bgr
        
    except Exception as e:
        logger.warning(f"PIL overlay creation failed: {e}, using simple fallback", exc_info=True)
        return _create_overlay_simple(old_img, new_img)

def _create_overlay_simple(old_img: np.ndarray, new_img: np.ndarray) -> np.ndarray:
    """Simple fallback overlay method using OpenCV only"""
    try:
        if old_img.shape != new_img.shape:
            new_img = cv2.resize(new_img, (old_img.shape[1], old_img.shape[0]), interpolation=cv2.INTER_AREA)

        old_gray = cv2.cvtColor(old_img, cv2.COLOR_BGR2GRAY)
        new_gray = cv2.cvtColor(new_img, cv2.COLOR_BGR2GRAY)
        
        old_content = old_gray < 240
        new_content = new_gray < 240
        
        old_only = old_content & ~new_content
        new_only = new_content & ~old_content
        overlap = old_content & new_content
        
        h, w = old_gray.shape
        overlay = np.full((h, w, 3), 255, dtype=np.uint8)
        
        overlay[old_only] = [0, 0, 255]  # BGR red
        overlay[new_only] = [0, 255, 0]  # BGR green
        overlay[overlap] = [200, 200, 200]  # BGR gray
        
        return overlay
    except Exception as e:
        logger.error(f"Fallback overlay failed: {e}")
        h, w = old_img.shape[:2]
        overlay = np.full((h, w, 3), 255, dtype=np.uint8)
        overlay[:] = (128, 128, 128)
        return overlay

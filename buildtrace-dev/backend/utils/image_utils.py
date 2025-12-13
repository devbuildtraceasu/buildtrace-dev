"""
Image Utilities for Drawing Processing
Handles image loading, grayscale conversion, and overlay creation

Synced with buildtrace-overlay- for consistent overlay generation
"""

import cv2
import numpy as np
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


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


def create_overlay_image(old_img: np.ndarray, new_img: np.ndarray) -> np.ndarray:
    """
    Create overlay comparison image showing changes between old and new drawings.
    
    Colors (BGR format):
    - GREEN (0, 255, 0): New elements (additions)
    - RED (0, 0, 255): Old elements (removals)  
    - YELLOW (0, 255, 255): Overlap (modifications/unchanged)
    - WHITE (255, 255, 255): Background
    
    Args:
        old_img: Aligned old drawing image (BGR from OpenCV)
        new_img: New drawing image (BGR from OpenCV)
        
    Returns:
        Overlay image (BGR) with vibrant color-coded changes
    """
    try:
        # Resize images if they're extremely large
        max_dimension = 15000
        if old_img.shape[0] > max_dimension or old_img.shape[1] > max_dimension:
            scale = max_dimension / max(old_img.shape[0], old_img.shape[1])
            new_size = (int(old_img.shape[1] * scale), int(old_img.shape[0] * scale))
            old_img = cv2.resize(old_img, new_size, interpolation=cv2.INTER_AREA)
            new_img = cv2.resize(new_img, new_size, interpolation=cv2.INTER_AREA)

        # Ensure images match in size
        if old_img.shape != new_img.shape:
            logger.warning(f"Image size mismatch: old {old_img.shape} vs new {new_img.shape}, resizing")
            new_img = cv2.resize(new_img, (old_img.shape[1], old_img.shape[0]), interpolation=cv2.INTER_AREA)

        # Convert to grayscale for content detection
        old_gray = cv2.cvtColor(old_img, cv2.COLOR_BGR2GRAY)
        new_gray = cv2.cvtColor(new_img, cv2.COLOR_BGR2GRAY)

        # Create content masks (pixels with drawing content, not white background)
        old_content_mask = old_gray < 240
        new_content_mask = new_gray < 240

        h, w = old_gray.shape
        # Start with white background
        overlay = np.full((h, w, 3), 255, dtype=np.uint8)

        # Identify regions:
        # - old_only: content in old but not new = REMOVED (RED)
        # - new_only: content in new but not old = ADDED (GREEN)
        # - common: content in both = MODIFIED/UNCHANGED (YELLOW)
        old_only_mask = old_content_mask & ~new_content_mask
        new_only_mask = new_content_mask & ~old_content_mask
        common_mask = old_content_mask & new_content_mask

        # Apply vibrant colors (BGR format):
        # RED for removals (old only) - vibrant red
        overlay[old_only_mask] = (0, 0, 255)  # BGR: pure red
        
        # GREEN for additions (new only) - vibrant green  
        overlay[new_only_mask] = (0, 255, 0)  # BGR: pure green
        
        # YELLOW for modifications/overlap (common) - vibrant yellow
        overlay[common_mask] = (0, 255, 255)  # BGR: pure yellow (red + green)

        # Clean up intermediate arrays
        del old_gray, new_gray, old_content_mask, new_content_mask
        del old_only_mask, new_only_mask, common_mask

        return overlay
        
    except Exception as e:
        logger.error(f"Overlay creation failed: {e}", exc_info=True)
        # Fallback to simple approach if any issues
        h, w = old_img.shape[:2]
        overlay = np.full((h, w, 3), 255, dtype=np.uint8)
        return overlay


def create_overlay_image_alternative(old_img: np.ndarray, new_img: np.ndarray) -> np.ndarray:
    """
    Alternative approach using channel-based overlay for cleaner results
    """
    # Convert to grayscale
    old_gray = cv2.cvtColor(old_img, cv2.COLOR_BGR2GRAY)
    new_gray = cv2.cvtColor(new_img, cv2.COLOR_BGR2GRAY)
    
    # Create content masks
    old_content = old_gray < 240
    new_content = new_gray < 240
    
    # Create RGB channels
    height, width = old_gray.shape
    red_channel = np.ones((height, width), dtype=np.uint8) * 255
    green_channel = np.ones((height, width), dtype=np.uint8) * 255  
    blue_channel = np.ones((height, width), dtype=np.uint8) * 255
    
    # Apply colors to channels
    # Old content: Reduce green and blue (make red)
    green_channel[old_content] = 100
    blue_channel[old_content] = 100

    # New content: Reduce red and blue (make green)
    red_channel[new_content] = 100
    blue_channel[new_content] = 100
    
    # Combine channels
    overlay = cv2.merge([blue_channel, green_channel, red_channel])
    
    return overlay

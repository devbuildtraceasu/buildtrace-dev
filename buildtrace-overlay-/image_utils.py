import cv2
import numpy as np


def load_image(path: str) -> np.ndarray:
    img = cv2.imread(path)
    if img is None:
        raise FileNotFoundError(f"Could not load images from {path}")
    return img


def image_to_grayscale(img: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.bitwise_not(gray)
    return gray


def create_overlay_image(old_img, new_img):
    # Memory-efficient overlay creation
    try:
        # Resize images if they're extremely large (only for very large images)
        max_dimension = 15000  # Much higher limit to preserve quality
        if old_img.shape[0] > max_dimension or old_img.shape[1] > max_dimension:
            scale = max_dimension / max(old_img.shape[0], old_img.shape[1])
            new_size = (int(old_img.shape[1] * scale), int(old_img.shape[0] * scale))
            old_img = cv2.resize(old_img, new_size, interpolation=cv2.INTER_AREA)
            new_img = cv2.resize(new_img, new_size, interpolation=cv2.INTER_AREA)

        # Grayscale for content masks
        old_gray = cv2.cvtColor(old_img, cv2.COLOR_BGR2GRAY)
        new_gray = cv2.cvtColor(new_img, cv2.COLOR_BGR2GRAY)

        old_content_mask = old_gray < 240
        new_content_mask = new_gray < 240

        h, w = old_gray.shape
        overlay = np.full((h, w, 3), 255, dtype=np.uint8)

        old_only_mask = old_content_mask & ~new_content_mask
        new_only_mask = new_content_mask & ~old_content_mask
        common_mask   = old_content_mask &  new_content_mask

        # Tint using uint8, no float32 buffers
        overlay[old_only_mask] = (100, 100, 255)   # BGR light red (old elements that were removed)
        overlay[new_only_mask] = (100, 255, 100)   # BGR light green (new elements that were added)
        overlay[common_mask]   = (150, 150, 150)   # gray (unchanged elements)

        # Clean up intermediate arrays
        del old_gray, new_gray, old_content_mask, new_content_mask
        del old_only_mask, new_only_mask, common_mask

        return overlay
    except Exception as e:
        # Fallback to simple approach if memory issues
        h, w = old_img.shape[:2]
        overlay = np.full((h, w, 3), 255, dtype=np.uint8)
        overlay[:] = (128, 128, 128)  # Gray fallback
        return overlay


def create_overlay_image_alternative(old_img, new_img):
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
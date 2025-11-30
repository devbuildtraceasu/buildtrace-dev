"""
Drawing Alignment Utility
Aligns two versions of the same drawing using computer vision (SIFT)
"""

import cv2
import numpy as np
from typing import Optional, Tuple
from dataclasses import dataclass
import logging
from utils.estimate_affine import estimate_affine_partial_2d_constrained
from utils.image_utils import image_to_grayscale

logger = logging.getLogger(__name__)

@dataclass
class AlignConfig:
    """Configuration for alignment algorithm"""
    n_features: int = 10_000
    exclude_margin: float = 0.2
    ratio_threshold: float = 0.75
    ransac_reproj_threshold: float = 15.0  # More lenient for difficult alignments
    max_iters: int = 5000  # More iterations
    confidence: float = 0.95  # Lower confidence
    scale_min: float = 0.3
    scale_max: float = 2.5
    rotation_deg_min: float = -30  # More lenient rotation
    rotation_deg_max: float = 30

class AlignDrawings:
    """
    Aligns two images using SIFT feature matching and constrained affine transformation
    """
    
    def __init__(self, config: Optional[AlignConfig] = None, debug: bool = False):
        self.config = config or AlignConfig()
        self.debug = debug
    
    def __call__(self, old_img: np.ndarray, new_img: np.ndarray) -> Optional[np.ndarray]:
        """
        Align old image to match new image (callable interface)
        
        Args:
            old_img: Old drawing image (BGR)
            new_img: New drawing image (BGR)
            
        Returns:
            Aligned old image, or None if alignment fails
        """
        return self.align(old_img, new_img)
    
    def align(self, old_img: np.ndarray, new_img: np.ndarray) -> Optional[np.ndarray]:
        """
        Align old image to match new image
        
        Args:
            old_img: Old drawing image (BGR)
            new_img: New drawing image (BGR)
            
        Returns:
            Aligned old image, or None if alignment fails
        """
        old_gray = image_to_grayscale(old_img)
        new_gray = image_to_grayscale(new_img)

        logger.info("Extracting SIFT features...")
        kp1, desc1 = self.extract_features_sift(old_gray)
        kp2, desc2 = self.extract_features_sift(new_gray)
        logger.info(f"Found {len(kp1)} keypoints in old image and {len(kp2)} in new image")

        if desc1 is None or desc2 is None or len(kp1) < 2 or len(kp2) < 2:
            logger.warning("Not enough features detected in one of the images.")
            return None

        logger.info("Matching features with Ratio Test...")
        good_matches = self.match_features_ratio_test(desc1, desc2)
        logger.info(f"Found {len(good_matches)} good matches after ratio test")

        logger.info("Finding transformation...")
        matrix, mask = self.find_transformation(kp1, kp2, good_matches)

        if matrix is None:
            raise RuntimeError("Failed to find a valid transformation.")

        output_shape = (new_img.shape[1], new_img.shape[0])
        transformed_img = self.apply_transformation(old_img, matrix, output_shape)

        return transformed_img

    def extract_features_sift(self, img_gray: np.ndarray) -> Tuple[list, Optional[np.ndarray]]:
        """Extract SIFT features from grayscale image"""
        detector = cv2.SIFT_create(nfeatures=self.config.n_features)

        # Create mask to exclude margin area if specified
        mask = None
        if self.config.exclude_margin:
            h, w = img_gray.shape
            margin = int(min(h, w) * self.config.exclude_margin)
            mask = np.zeros((h, w), dtype=np.uint8)
            mask[margin : h - margin, margin : w - margin] = 255

        keypoints, descriptors = detector.detectAndCompute(img_gray, mask)
        return keypoints, descriptors

    def match_features_ratio_test(self, desc1: np.ndarray, desc2: np.ndarray, ratio_threshold: float = None) -> list:
        """Match SIFT features using Brute-Force and Lowe's Ratio Test"""
        if ratio_threshold is None:
            ratio_threshold = self.config.ratio_threshold
            
        matcher = cv2.BFMatcher(cv2.NORM_L2, crossCheck=False)
        matches_knn = matcher.knnMatch(desc1, desc2, k=2)

        good_matches = []
        for m, n in matches_knn:
            if m.distance < ratio_threshold * n.distance:
                good_matches.append(m)

        good_matches = sorted(good_matches, key=lambda x: x.distance)
        return good_matches

    def find_transformation(self, kp1: list, kp2: list, matches: list) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """Find a transformation matrix for transformations without shear and perspective."""
        if len(matches) < 3:
            logger.warning(f"Not enough good matches found: {len(matches)}")
            return None, None

        src_pts = np.float32([kp1[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)

        matrix, mask = estimate_affine_partial_2d_constrained(
            from_points=src_pts.reshape(-1, 2),
            to_points=dst_pts.reshape(-1, 2),
            ransac_reproj_threshold=self.config.ransac_reproj_threshold,
            max_iters=self.config.max_iters,
            confidence=self.config.confidence,
            scale_min=self.config.scale_min,
            scale_max=self.config.scale_max,
            rotation_deg_min=self.config.rotation_deg_min,
            rotation_deg_max=self.config.rotation_deg_max,
        )
        return matrix, mask

    def apply_transformation(self, img: np.ndarray, matrix: np.ndarray, output_shape: Tuple[int, int]) -> np.ndarray:
        """Apply an affine transformation to the image."""
        if matrix is None:
            return img
        return cv2.warpAffine(img, matrix, output_shape)


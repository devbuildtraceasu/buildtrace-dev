"""
Drawing Alignment Utility
Aligns two versions of the same drawing using computer vision (SIFT)
"""

import cv2
import numpy as np
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class AlignDrawings:
    """
    Aligns two images using SIFT feature matching and constrained affine transformation
    """
    
    def __init__(self, n_features: int = 10000, debug: bool = False):
        self.n_features = n_features
        self.debug = debug
    
    def align(self, old_img: np.ndarray, new_img: np.ndarray) -> Optional[np.ndarray]:
        """
        Align old image to match new image
        
        Args:
            old_img: Old drawing image (BGR)
            new_img: New drawing image (BGR)
            
        Returns:
            Aligned old image, or None if alignment fails
        """
        old_gray = cv2.cvtColor(old_img, cv2.COLOR_BGR2GRAY)
        new_gray = cv2.cvtColor(new_img, cv2.COLOR_BGR2GRAY)
        
        # Extract SIFT features
        sift = cv2.SIFT_create(nfeatures=self.n_features)
        kp1, desc1 = sift.detectAndCompute(old_gray, None)
        kp2, desc2 = sift.detectAndCompute(new_gray, None)
        
        if desc1 is None or desc2 is None or len(kp1) < 4 or len(kp2) < 4:
            logger.warning("Not enough features detected")
            return None
        
        # Match features
        matcher = cv2.BFMatcher(cv2.NORM_L2, crossCheck=False)
        matches_knn = matcher.knnMatch(desc1, desc2, k=2)
        
        # Apply ratio test
        good_matches = []
        for m, n in matches_knn:
            if m.distance < 0.75 * n.distance:
                good_matches.append(m)
        
        if len(good_matches) < 4:
            logger.warning("Not enough good matches")
            return None
        
        # Find transformation
        src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        
        # Use RANSAC to find affine transformation
        matrix, mask = cv2.estimateAffinePartial2D(
            src_pts, dst_pts,
            method=cv2.RANSAC,
            ransacReprojThreshold=15.0,
            confidence=0.95,
            maxIters=5000
        )
        
        if matrix is None:
            logger.warning("Failed to find transformation")
            return None
        
        # Apply transformation
        output_shape = (new_img.shape[1], new_img.shape[0])
        aligned_img = cv2.warpAffine(old_img, matrix, output_shape)
        
        return aligned_img
    
    def create_overlay(self, aligned_old: np.ndarray, new_img: np.ndarray) -> np.ndarray:
        """
        Create overlay image showing differences
        
        Args:
            aligned_old: Aligned old image
            new_img: New image
            
        Returns:
            Overlay image
        """
        # Simple overlay: blend images
        overlay = cv2.addWeighted(aligned_old, 0.5, new_img, 0.5, 0)
        return overlay


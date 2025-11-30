"""Diff pipeline implementation for BuildTrace.

Creates alignment overlays by comparing two drawing versions using SIFT feature matching.
"""

from __future__ import annotations

import logging
import os
import uuid
import tempfile

import cv2
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple, List

from gcp.database import get_db_session
from gcp.database.models import DiffResult, DrawingVersion, Job
from gcp.storage import StorageService
from utils.alignment import AlignDrawings, AlignConfig
from utils.image_utils import load_image, create_overlay_image
from PIL import Image
from utils.pdf_parser import pdf_to_png, get_pdf_page_count
from utils.drawing_extraction import extract_drawing_names

logger = logging.getLogger(__name__)


class DiffPipeline:
    """Generates machine overlays by aligning and comparing two drawing versions."""

    def __init__(
        self,
        storage_service: Optional[StorageService] = None,
        session_factory=None,
        dpi: int = 220,
    ) -> None:
        self.storage = storage_service or StorageService()
        self.session_factory = session_factory or get_db_session

        default_dpi = dpi or 220
        self.dpi = int(os.environ.get("DIFF_RENDER_DPI", default_dpi))
        self.max_image_dimension = int(os.environ.get("DIFF_MAX_IMAGE_DIMENSION", 5000))
        align_features = int(os.environ.get("DIFF_ALIGNMENT_FEATURES", 4000))
        self.aligner = AlignDrawings(
            config=AlignConfig(
                n_features=align_features,
                exclude_margin=0.15,
                ratio_threshold=0.75,
            ),
            debug=False,
        )

    def run(self, job_id: str, old_version_id: str, new_version_id: str) -> Dict:
        logger.info(
            "Starting diff pipeline",
            extra={"job_id": job_id, "old_version_id": old_version_id, "new_version_id": new_version_id},
        )

        with self.session_factory() as db:
            job = db.query(Job).filter_by(id=job_id).first()
            if not job:
                raise ValueError(f"Job {job_id} not found")

            old_version = db.query(DrawingVersion).filter_by(id=old_version_id).first()
            new_version = db.query(DrawingVersion).filter_by(id=new_version_id).first()
            if not old_version or not new_version:
                raise ValueError("Drawing versions missing for diff computation")
            if not old_version.ocr_result_ref or not new_version.ocr_result_ref:
                raise ValueError("OCR must complete before running diff")

            # Download PDFs from storage
            old_pdf_bytes = self.storage.download_file(old_version.drawing.storage_path)
            new_pdf_bytes = self.storage.download_file(new_version.drawing.storage_path)
            
            # Save to temp files
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_old:
                tmp_old.write(old_pdf_bytes)
                tmp_old_path = tmp_old.name
            
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_new:
                tmp_new.write(new_pdf_bytes)
                tmp_new_path = tmp_new.name
            
            try:
                with tempfile.TemporaryDirectory() as temp_dir:
                    old_pages = self._prepare_pdf_pages(tmp_old_path, temp_dir, prefix="old")
                    new_pages = self._prepare_pdf_pages(tmp_new_path, temp_dir, prefix="new")

                    if not old_pages or not new_pages:
                        raise RuntimeError("Unable to extract pages from one or both PDFs")

                    page_pairs = list(zip(old_pages, new_pages))
                    if len(old_pages) != len(new_pages):
                        logger.warning(
                            "PDF page counts differ",
                            extra={
                                "job_id": job_id,
                                "old_pages": len(old_pages),
                                "new_pages": len(new_pages),
                                "pairs_processed": len(page_pairs),
                            },
                        )

                    diff_results: List[Dict] = []

                    for pair_index, (old_page, new_page) in enumerate(page_pairs, start=1):
                        logger.info(
                            "Processing page pair",
                            extra={
                                "job_id": job_id,
                                "pair_index": pair_index,
                                "old_page": old_page["page_number"],
                                "new_page": new_page["page_number"],
                                "drawing_name": new_page["drawing_name"],
                            },
                        )

                        old_img = self._load_page_image(old_page["png_path"])
                        new_img = self._load_page_image(new_page["png_path"])

                        logger.info("Aligning images using SIFT...")
                        aligned_old_img = self.aligner.align(old_img, new_img)

                        if aligned_old_img is None:
                            raise RuntimeError(f"Failed to align images for page {pair_index}")

                        logger.info("Creating overlay image...")
                        overlay_img = create_overlay_image(aligned_old_img, new_img)

                        overlay_path = str(Path(temp_dir) / f"overlay_{pair_index}.png")
                        overlay_rgb = cv2.cvtColor(overlay_img, cv2.COLOR_BGR2RGB)
                        Image.fromarray(overlay_rgb).save(overlay_path, "PNG", optimize=False)

                        with open(overlay_path, "rb") as overlay_file:
                            overlay_bytes = overlay_file.read()

                        overlay_ref = self.storage.upload_diff_overlay(
                            f"{job_id}/page-{pair_index:03d}/overlay.png",
                            overlay_bytes,
                        )

                        # Upload baseline and revised PNGs so the frontend can render them directly
                        with open(old_page["png_path"], "rb") as baseline_file:
                            baseline_bytes = baseline_file.read()
                        baseline_image_ref = self.storage.upload_diff_overlay(
                            f"{job_id}/page-{pair_index:03d}/baseline.png",
                            baseline_bytes,
                        )

                        with open(new_page["png_path"], "rb") as revised_file:
                            revised_bytes = revised_file.read()
                        revised_image_ref = self.storage.upload_diff_overlay(
                            f"{job_id}/page-{pair_index:03d}/revised.png",
                            revised_bytes,
                        )

                        alignment_score = self._calculate_alignment_score(old_img, new_img, aligned_old_img)
                        changes_detected = alignment_score < 0.95
                        change_count = 1 if changes_detected else 0

                        diff_payload = {
                            "job_id": job_id,
                            "old_version_id": old_version_id,
                            "new_version_id": new_version_id,
                            "overlay_ref": overlay_ref,
                            "baseline_image_ref": baseline_image_ref,
                            "revised_image_ref": revised_image_ref,
                            "alignment_score": alignment_score,
                            "changes_detected": changes_detected,
                            "change_count": change_count,
                            "generated_at": datetime.utcnow().isoformat(),
                            "page_number": pair_index,
                            "drawing_name": new_page["drawing_name"],
                            "old_page_number": old_page["page_number"],
                            "new_page_number": new_page["page_number"],
                            "total_pages": len(page_pairs),
                        }

                        diff_result_id = str(uuid.uuid4())
                        diff_ref = self.storage.upload_diff_result(diff_result_id, diff_payload)

                        diff_result = DiffResult(
                            id=diff_result_id,
                            job_id=job_id,
                            old_drawing_version_id=old_version_id,
                            new_drawing_version_id=new_version_id,
                            machine_generated_overlay_ref=diff_ref,
                            changes_detected=bool(changes_detected),
                            change_count=int(change_count),
                            alignment_score=float(alignment_score),
                            created_at=datetime.utcnow(),
                            created_by=job.created_by,
                            diff_metadata={
                                "auto_generated": True,
                                "overlay_image_ref": overlay_ref,
                                "baseline_image_ref": baseline_image_ref,
                                "revised_image_ref": revised_image_ref,
                                "page_number": pair_index,
                                "drawing_name": new_page["drawing_name"],
                                "total_pages": len(page_pairs),
                            },
                        )
                        db.add(diff_result)
                        db.commit()

                        logger.info(
                            "Diff page processed",
                            extra={
                                "job_id": job_id,
                                "diff_result_id": diff_result_id,
                                "page_number": pair_index,
                                "change_count": change_count,
                                "alignment_score": alignment_score,
                            },
                        )

                        diff_results.append(
                            {
                                "diff_result_id": diff_result_id,
                                "result_ref": diff_ref,
                                "overlay_ref": overlay_ref,
                                "change_count": change_count,
                                "alignment_score": alignment_score,
                                "page_number": pair_index,
                                "drawing_name": new_page["drawing_name"],
                                "total_pages": len(page_pairs),
                            }
                        )

                        # Release large arrays before moving to the next page
                        del old_img, new_img, aligned_old_img, overlay_img

                    return {
                        "diff_results": diff_results,
                        "total_pages": len(page_pairs),
                    }
                    
            finally:
                # Cleanup temp files
                Path(tmp_old_path).unlink(missing_ok=True)
                Path(tmp_new_path).unlink(missing_ok=True)
    
    def _prepare_pdf_pages(self, pdf_path: str, temp_dir: str, prefix: str) -> List[Dict]:
        """Convert every PDF page to PNG and attach drawing metadata."""
        drawing_info = extract_drawing_names(pdf_path)
        if not drawing_info:
            total_pages = get_pdf_page_count(pdf_path)
            drawing_info = [
                {'page': idx + 1, 'drawing_name': f"{prefix.title()}_Page_{idx + 1}"}
                for idx in range(total_pages)
            ]
        
        pages: List[Dict] = []
        for info in drawing_info:
            page_number = info.get('page') or (len(pages) + 1)
            drawing_name = info.get('drawing_name') or f"{prefix.title()}_Page_{page_number}"
            output_path = Path(temp_dir) / f"{prefix}_page_{page_number:03d}.png"
            pdf_to_png(pdf_path, str(output_path), self.dpi, page_number - 1)
            pages.append(
                {
                    "png_path": str(output_path),
                    "drawing_name": drawing_name,
                    "page_number": page_number,
                }
            )
        return pages
    
    def _load_page_image(self, path: str):
        """Load image from disk and downscale to keep memory bounded."""
        img = load_image(path)
        h, w = img.shape[:2]
        longest = max(h, w)
        if longest <= self.max_image_dimension:
            return img

        scale = self.max_image_dimension / float(longest)
        new_size = (int(w * scale), int(h * scale))
        logger.info(
            "Downscaling page image",
            extra={"path": path, "original_shape": (h, w), "new_shape": new_size[::-1]},
        )
        return cv2.resize(img, new_size, interpolation=cv2.INTER_AREA)

    def _calculate_alignment_score(self, old_img, new_img, aligned_old_img) -> float:
        """Calculate alignment quality score (0-1, higher is better)"""
        try:
            # Simple score based on image similarity
            # Can be enhanced with more sophisticated metrics
            import numpy as np
            
            # Convert to grayscale for comparison
            old_gray = cv2.cvtColor(aligned_old_img, cv2.COLOR_BGR2GRAY)
            new_gray = cv2.cvtColor(new_img, cv2.COLOR_BGR2GRAY)
            
            # Calculate structural similarity (simplified)
            # In production, use SSIM or other metrics
            diff = np.abs(old_gray.astype(float) - new_gray.astype(float))
            similarity = 1.0 - (np.mean(diff) / 255.0)
            
            return max(0.0, min(1.0, similarity))
        except Exception as e:
            logger.warning(f"Error calculating alignment score: {e}")
            return 0.5  # Default score


__all__ = ["DiffPipeline"]

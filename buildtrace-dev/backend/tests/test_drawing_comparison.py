"""
Tests for Drawing Comparison Pipeline

Tests the migrated drawing comparison functionality from buildtrace-overlay-
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import cv2
import numpy as np

from processing.drawing_comparison import (
    find_matching_png_files,
    create_drawing_overlay,
    compare_drawing_sets,
    compare_pdf_drawing_sets
)
from utils.local_output_manager import LocalOutputManager


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_images(temp_dir):
    """Create sample PNG images for testing"""
    old_dir = temp_dir / "old"
    new_dir = temp_dir / "new"
    old_dir.mkdir()
    new_dir.mkdir()
    
    def _draw_base(name: str) -> np.ndarray:
        img = np.full((256, 256, 3), 255, dtype=np.uint8)
        cv2.rectangle(img, (20, 20), (120, 120), (0, 0, 0), 3)
        cv2.line(img, (0, 200), (255, 200), (50, 50, 50), 2)
        cv2.putText(img, name, (30, 170), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2, cv2.LINE_AA)
        return img

    # Create sample images with detectable features
    for name in ["A-101", "A-102", "A-103"]:
        base_img = _draw_base(name)
        new_img = base_img.copy()
        cv2.circle(new_img, (180, 60), 20, (0, 255, 0), 3)
        cv2.line(new_img, (150, 180), (230, 180), (255, 0, 0), 2)

        cv2.imwrite(str(old_dir / f"{name}.png"), base_img)
        cv2.imwrite(str(new_dir / f"{name}.png"), new_img)

    # Add one extra unmatched file in old/new
    extra_old = _draw_base("A-999")
    extra_new = _draw_base("A-888")
    cv2.imwrite(str(old_dir / "A-999.png"), extra_old)
    cv2.imwrite(str(new_dir / "A-888.png"), extra_new)
    
    return old_dir, new_dir


class TestFindMatchingPNGFiles:
    """Test finding matching PNG files"""
    
    def test_find_matching_files(self, sample_images):
        """Test finding matching files between folders"""
        old_dir, new_dir = sample_images
        
        matches = find_matching_png_files(str(old_dir), str(new_dir))
        
        assert len(matches) == 3
        assert all(name in ["A-101", "A-102", "A-103"] for name, _, _ in matches)
    
    def test_no_matches(self, temp_dir):
        """Test when no matches exist"""
        old_dir = temp_dir / "old"
        new_dir = temp_dir / "new"
        old_dir.mkdir()
        new_dir.mkdir()
        
        # Create non-matching files
        img = np.ones((100, 100, 3), dtype=np.uint8) * 255
        cv2.imwrite(str(old_dir / "A-101.png"), img)
        cv2.imwrite(str(new_dir / "A-999.png"), img)
        
        matches = find_matching_png_files(str(old_dir), str(new_dir))
        assert len(matches) == 0
    
    def test_missing_folder(self, temp_dir):
        """Test error when folder doesn't exist"""
        with pytest.raises(FileNotFoundError):
            find_matching_png_files(str(temp_dir / "nonexistent"), str(temp_dir / "new"))


class TestCreateDrawingOverlay:
    """Test creating drawing overlays"""
    
    def test_create_overlay(self, sample_images, temp_dir):
        """Test creating an overlay"""
        old_dir, new_dir = sample_images
        output_dir = temp_dir / "output"
        
        old_path = old_dir / "A-101.png"
        new_path = new_dir / "A-101.png"
        
        overlay_path = create_drawing_overlay(
            str(old_path),
            str(new_path),
            str(output_dir),
            "A-101",
            debug=False
        )
        
        assert overlay_path is not None
        assert Path(overlay_path).exists()
        
        # Check that all three files were created
        assert (output_dir / "A-101_old.png").exists()
        assert (output_dir / "A-101_new.png").exists()
        assert (output_dir / "A-101_overlay.png").exists()
    
    def test_create_overlay_with_output_manager(self, sample_images, temp_dir):
        """Test creating overlay with output manager"""
        old_dir, new_dir = sample_images
        output_dir = temp_dir / "output"
        output_manager = LocalOutputManager(base_path=str(temp_dir / "outputs"))
        
        old_path = old_dir / "A-101.png"
        new_path = new_dir / "A-101.png"
        
        overlay_path = create_drawing_overlay(
            str(old_path),
            str(new_path),
            str(output_dir),
            "A-101",
            debug=False,
            output_manager=output_manager
        )
        
        assert overlay_path is not None


class TestCompareDrawingSets:
    """Test comparing drawing sets"""
    
    def test_compare_png_folders(self, sample_images, temp_dir):
        """Test comparing PNG folders"""
        old_dir, new_dir = sample_images
        output_base = temp_dir / "results"
        
        results = compare_drawing_sets(
            str(old_dir),
            str(new_dir),
            str(output_base),
            debug=False
        )
        
        assert results['matches_found'] == 3
        assert results['successful_overlays'] == 3
        assert results['failed_overlays'] == 0
        assert len(results['output_folders']) == 3
    
    def test_compare_empty_folders(self, temp_dir):
        """Test comparing empty folders"""
        old_dir = temp_dir / "old"
        new_dir = temp_dir / "new"
        old_dir.mkdir()
        new_dir.mkdir()
        
        results = compare_drawing_sets(
            str(old_dir),
            str(new_dir),
            str(temp_dir / "results"),
            debug=False
        )
        
        assert results['matches_found'] == 0
        assert results['successful_overlays'] == 0


class TestComparePDFDrawingSets:
    """Test PDF comparison pipeline"""
    
    @pytest.mark.skip(reason="Requires actual PDF files")
    def test_compare_pdfs(self):
        """Test comparing PDF files (requires actual PDFs)"""
        # This test would require actual PDF files
        # Skip for now, add when test PDFs are available
        pass


@pytest.mark.integration
class TestIntegration:
    """Integration tests for drawing comparison"""
    
    def test_full_workflow(self, sample_images, temp_dir):
        """Test full workflow from PNG folders to overlays"""
        old_dir, new_dir = sample_images
        output_base = temp_dir / "results"
        output_manager = LocalOutputManager(base_path=str(temp_dir / "outputs"))
        
        # Find matches
        matches = find_matching_png_files(str(old_dir), str(new_dir))
        assert len(matches) == 3
        
        # Create overlays
        results = compare_drawing_sets(
            str(old_dir),
            str(new_dir),
            str(output_base),
            debug=False,
            output_manager=output_manager
        )
        
        assert results['successful_overlays'] == 3
        
        # Verify output structure
        for folder in results['output_folders']:
            folder_path = Path(folder)
            assert folder_path.exists()
            assert (folder_path / f"{folder_path.stem.replace('_overlay_results', '')}_overlay.png").exists()
@pytest.fixture(autouse=True)
def stub_aligner(monkeypatch):
    """Use a deterministic aligner to avoid OpenCV feature variability in tests."""
    from processing import drawing_comparison as dc

    class _IdentityAligner:
        def __call__(self, old_img, new_img):
            return new_img.copy()

    monkeypatch.setattr(dc, "AlignDrawings", lambda *args, **kwargs: _IdentityAligner())

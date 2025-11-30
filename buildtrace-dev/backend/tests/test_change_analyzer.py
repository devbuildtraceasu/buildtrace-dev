"""
Tests for Change Analyzer

Tests the migrated change analyzer functionality with Gemini API
"""

import pytest
import tempfile
import shutil
from pathlib import Path
import cv2
import numpy as np
from unittest.mock import Mock, patch, MagicMock

from processing.change_analyzer import (
    ChangeAnalyzer,
    ChangeAnalysisResult
)
from utils.local_output_manager import LocalOutputManager


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_overlay_folder(temp_dir):
    """Create a sample overlay folder with test images"""
    overlay_dir = temp_dir / "A-101_overlay_results"
    overlay_dir.mkdir()
    
    # Create sample PNG files
    img = np.ones((100, 100, 3), dtype=np.uint8) * 255
    cv2.imwrite(str(overlay_dir / "A-101_old.png"), img)
    cv2.imwrite(str(overlay_dir / "A-101_new.png"), img)
    cv2.imwrite(str(overlay_dir / "A-101_overlay.png"), img)
    
    return str(overlay_dir)


class TestChangeAnalysisResult:
    """Test ChangeAnalysisResult dataclass"""
    
    def test_to_dict(self):
        """Test converting result to dictionary"""
        result = ChangeAnalysisResult(
            drawing_name="A-101",
            overlay_folder="/path/to/overlay",
            changes_found=["Change 1", "Change 2"],
            critical_change="Critical change",
            analysis_summary="Summary text",
            recommendations=["Rec 1"],
            success=True
        )
        
        result_dict = result.to_dict()
        
        assert result_dict['drawing_name'] == "A-101"
        assert result_dict['success'] is True
        assert len(result_dict['changes_found']) == 2
        assert result_dict['critical_change'] == "Critical change"


class TestChangeAnalyzer:
    """Test ChangeAnalyzer class"""
    
    @patch('processing.change_analyzer.genai')
    def test_init_with_api_key(self, mock_genai):
        """Test initializing analyzer with API key"""
        mock_genai.configure = Mock()
        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model
        
        analyzer = ChangeAnalyzer(api_key="test-key", model="models/gemini-2.5-pro")
        
        assert analyzer.model == mock_model
        mock_genai.configure.assert_called_once_with(api_key="test-key")
    
    @patch('processing.change_analyzer.genai')
    @patch.dict('os.environ', {'GEMINI_API_KEY': 'env-key'})
    def test_init_from_env(self, mock_genai):
        """Test initializing analyzer from environment"""
        mock_genai.configure = Mock()
        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model
        
        analyzer = ChangeAnalyzer()
        
        assert analyzer.model == mock_model
        mock_genai.configure.assert_called_once_with(api_key="env-key")
    
    def test_init_missing_api_key(self):
        """Test error when API key is missing"""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="GEMINI_API_KEY"):
                ChangeAnalyzer()
    
    @patch('processing.change_analyzer.genai')
    def test_validate_overlay_folder(self, mock_genai, sample_overlay_folder):
        """Test validating overlay folder"""
        mock_genai.configure = Mock()
        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model
        
        analyzer = ChangeAnalyzer(api_key="test-key")
        
        old_png, new_png, overlay_png = analyzer._validate_overlay_folder(sample_overlay_folder)
        
        assert Path(old_png).exists()
        assert Path(new_png).exists()
        assert Path(overlay_png).exists()
        assert "_old.png" in old_png
        assert "_new.png" in new_png
        assert "_overlay.png" in overlay_png
    
    def test_validate_overlay_folder_missing(self, temp_dir):
        """Test error when overlay folder is missing"""
        with patch('processing.change_analyzer.genai'):
            analyzer = ChangeAnalyzer(api_key="test-key")
            
            with pytest.raises(FileNotFoundError):
                analyzer._validate_overlay_folder(str(temp_dir / "nonexistent"))
    
    @patch('processing.change_analyzer.genai')
    @patch('processing.change_analyzer.Image')
    def test_analyze_overlay_folder(self, mock_image, mock_genai, sample_overlay_folder):
        """Test analyzing overlay folder"""
        # Setup mocks
        mock_genai.configure = Mock()
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = """
        Most Critical Change: Room extended
        
        Change List:
        1. Room 101 extended by 10 feet
        2. Door relocated
        
        Recommendations:
        - Update foundation plans
        """
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        # Mock PIL Image
        mock_pil_image = MagicMock()
        mock_image.open.return_value = mock_pil_image
        
        analyzer = ChangeAnalyzer(api_key="test-key")
        result = analyzer.analyze_overlay_folder(sample_overlay_folder)
        
        assert result.success is True
        assert result.drawing_name == "A-101"
        assert len(result.changes_found) > 0
        assert result.critical_change is not None
    
    @patch('processing.change_analyzer.genai')
    def test_parse_analysis_response(self, mock_genai):
        """Test parsing Gemini response"""
        mock_genai.configure = Mock()
        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model
        
        analyzer = ChangeAnalyzer(api_key="test-key")
        
        analysis_text = """
        Most Critical Change: Major structural modification
        
        Change List:
        1. Room 101 extended by 10 feet
        2. Door relocated from north to west
        3. Window added to south wall
        
        Recommendations:
        - Update foundation plans
        - Coordinate with structural engineer
        """
        
        changes, critical, recommendations = analyzer._parse_analysis_response(analysis_text)
        
        assert len(changes) >= 3
        assert critical is not None
        assert len(recommendations) >= 2
    
    @patch('processing.change_analyzer.genai')
    def test_analyze_multiple_overlays(self, mock_genai, temp_dir):
        """Test analyzing multiple overlay folders"""
        # Create multiple overlay folders
        for name in ["A-101", "A-102"]:
            overlay_dir = temp_dir / f"{name}_overlay_results"
            overlay_dir.mkdir()
            
            img = np.ones((100, 100, 3), dtype=np.uint8) * 255
            cv2.imwrite(str(overlay_dir / f"{name}_old.png"), img)
            cv2.imwrite(str(overlay_dir / f"{name}_new.png"), img)
            cv2.imwrite(str(overlay_dir / f"{name}_overlay.png"), img)
        
        # Setup mocks
        mock_genai.configure = Mock()
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Analysis text"
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        with patch('processing.change_analyzer.Image'):
            analyzer = ChangeAnalyzer(api_key="test-key")
            results = analyzer.analyze_multiple_overlays(str(temp_dir))
            
            assert len(results) == 2
            assert all(r.drawing_name in ["A-101", "A-102"] for r in results)


@pytest.mark.integration
class TestIntegration:
    """Integration tests for change analyzer"""
    
    @pytest.mark.skip(reason="Requires actual Gemini API key")
    def test_real_analysis(self, sample_overlay_folder):
        """Test with real Gemini API (requires API key)"""
        # This test would require actual Gemini API key
        # Skip for unit tests, enable for integration tests
        pass


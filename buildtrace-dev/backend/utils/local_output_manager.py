#!/usr/bin/env python3
"""
Local Output Manager for Development Mode

Manages saving all processing outputs, logs, and intermediate files locally
for analysis and debugging in development mode.
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from config import config

logger = logging.getLogger(__name__)


class LocalOutputManager:
    """Manages local file output for development mode"""
    
    def __init__(self, base_path: Optional[str] = None):
        """
        Initialize local output manager
        
        Args:
            base_path: Base directory for outputs (defaults to config.LOCAL_OUTPUT_PATH)
        """
        if base_path:
            self.base_path = Path(base_path)
        else:
            self.base_path = Path(getattr(config, 'LOCAL_OUTPUT_PATH', 'outputs'))
        
        # Create base directory structure
        self._create_directory_structure()
    
    def _create_directory_structure(self):
        """Create the directory structure for outputs"""
        directories = [
            self.base_path,
            self.base_path / 'sessions',
            self.base_path / 'jobs',
            self.base_path / 'logs',
            self.base_path / 'temp'
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created/verified directory: {directory}")
    
    def get_session_path(self, session_id: str) -> Path:
        """Get the base path for a session"""
        session_path = self.base_path / 'sessions' / session_id
        session_path.mkdir(parents=True, exist_ok=True)
        return session_path
    
    def get_job_path(self, job_id: str) -> Path:
        """Get the base path for a job"""
        job_path = self.base_path / 'jobs' / job_id
        job_path.mkdir(parents=True, exist_ok=True)
        return job_path
    
    def save_png(self, file_path: str, content: bytes, session_id: Optional[str] = None, 
                 job_id: Optional[str] = None, subfolder: str = 'pngs') -> str:
        """
        Save a PNG file locally
        
        Args:
            file_path: Original file path or name
            content: PNG file content (bytes)
            session_id: Session ID (if session-based)
            job_id: Job ID (if job-based)
            subfolder: Subfolder name (default: 'pngs')
        
        Returns:
            Local file path
        """
        if session_id:
            base_path = self.get_session_path(session_id)
        elif job_id:
            base_path = self.get_job_path(job_id)
        else:
            base_path = self.base_path / 'temp'
        
        png_dir = base_path / subfolder
        png_dir.mkdir(parents=True, exist_ok=True)
        
        # Extract filename from path
        filename = Path(file_path).name
        if not filename.endswith('.png'):
            filename = f"{filename}.png"
        
        local_path = png_dir / filename
        
        with open(local_path, 'wb') as f:
            f.write(content)
        
        logger.info(f"Saved PNG to: {local_path}")
        return str(local_path)
    
    def save_overlay(self, overlay_path: str, content: bytes, session_id: Optional[str] = None,
                    job_id: Optional[str] = None, drawing_name: Optional[str] = None) -> str:
        """
        Save an overlay image locally
        
        Args:
            overlay_path: Original overlay path or name
            content: Overlay image content (bytes)
            session_id: Session ID
            job_id: Job ID
            drawing_name: Drawing name for better organization
        
        Returns:
            Local file path
        """
        if session_id:
            base_path = self.get_session_path(session_id)
        elif job_id:
            base_path = self.get_job_path(job_id)
        else:
            base_path = self.base_path / 'temp'
        
        overlay_dir = base_path / 'overlays'
        overlay_dir.mkdir(parents=True, exist_ok=True)
        
        # Use drawing name if provided, otherwise extract from path
        if drawing_name:
            filename = f"{drawing_name}_overlay.png"
        else:
            filename = Path(overlay_path).name
            if not filename.endswith('.png'):
                filename = f"{filename}_overlay.png"
        
        local_path = overlay_dir / filename
        
        with open(local_path, 'wb') as f:
            f.write(content)
        
        logger.info(f"Saved overlay to: {local_path}")
        return str(local_path)
    
    def save_ocr_result(self, ocr_data: Dict[str, Any], session_id: Optional[str] = None,
                       job_id: Optional[str] = None, drawing_name: Optional[str] = None) -> str:
        """
        Save OCR result JSON locally
        
        Args:
            ocr_data: OCR result data (dict)
            session_id: Session ID
            job_id: Job ID
            drawing_name: Drawing name
        
        Returns:
            Local file path
        """
        if session_id:
            base_path = self.get_session_path(session_id)
        elif job_id:
            base_path = self.get_job_path(job_id)
        else:
            base_path = self.base_path / 'temp'
        
        ocr_dir = base_path / 'ocr_results'
        ocr_dir.mkdir(parents=True, exist_ok=True)
        
        if drawing_name:
            filename = f"{drawing_name}_ocr.json"
        else:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"ocr_{timestamp}.json"
        
        local_path = ocr_dir / filename
        
        with open(local_path, 'w', encoding='utf-8') as f:
            json.dump(ocr_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved OCR result to: {local_path}")
        return str(local_path)
    
    def save_diff_result(self, diff_data: Dict[str, Any], session_id: Optional[str] = None,
                        job_id: Optional[str] = None, drawing_name: Optional[str] = None) -> str:
        """
        Save diff result JSON locally
        
        Args:
            diff_data: Diff result data (dict)
            session_id: Session ID
            job_id: Job ID
            drawing_name: Drawing name
        
        Returns:
            Local file path
        """
        if session_id:
            base_path = self.get_session_path(session_id)
        elif job_id:
            base_path = self.get_job_path(job_id)
        else:
            base_path = self.base_path / 'temp'
        
        diff_dir = base_path / 'diff_results'
        diff_dir.mkdir(parents=True, exist_ok=True)
        
        if drawing_name:
            filename = f"{drawing_name}_diff.json"
        else:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"diff_{timestamp}.json"
        
        local_path = diff_dir / filename
        
        with open(local_path, 'w', encoding='utf-8') as f:
            json.dump(diff_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved diff result to: {local_path}")
        return str(local_path)
    
    def save_summary(self, summary_data: Dict[str, Any], session_id: Optional[str] = None,
                    job_id: Optional[str] = None, drawing_name: Optional[str] = None) -> str:
        """
        Save summary JSON locally
        
        Args:
            summary_data: Summary data (dict)
            session_id: Session ID
            job_id: Job ID
            drawing_name: Drawing name
        
        Returns:
            Local file path
        """
        if session_id:
            base_path = self.get_session_path(session_id)
        elif job_id:
            base_path = self.get_job_path(job_id)
        else:
            base_path = self.base_path / 'temp'
        
        summary_dir = base_path / 'summaries'
        summary_dir.mkdir(parents=True, exist_ok=True)
        
        if drawing_name:
            filename = f"{drawing_name}_summary.json"
        else:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"summary_{timestamp}.json"
        
        local_path = summary_dir / filename
        
        with open(local_path, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved summary to: {local_path}")
        return str(local_path)
    
    def save_processing_log(self, log_data: Dict[str, Any], session_id: Optional[str] = None,
                           job_id: Optional[str] = None) -> str:
        """
        Save processing log JSON locally
        
        Args:
            log_data: Processing log data
            session_id: Session ID
            job_id: Job ID
        
        Returns:
            Local file path
        """
        if session_id:
            base_path = self.get_session_path(session_id)
        elif job_id:
            base_path = self.get_job_path(job_id)
        else:
            base_path = self.base_path / 'temp'
        
        log_dir = base_path / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"processing_log_{timestamp}.json"
        local_path = log_dir / filename
        
        with open(local_path, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved processing log to: {local_path}")
        return str(local_path)
    
    def list_session_files(self, session_id: str) -> Dict[str, List[str]]:
        """
        List all files for a session
        
        Args:
            session_id: Session ID
        
        Returns:
            Dictionary with file lists by category
        """
        session_path = self.get_session_path(session_id)
        
        result = {
            'pngs': [],
            'overlays': [],
            'ocr_results': [],
            'diff_results': [],
            'summaries': [],
            'logs': []
        }
        
        for category in result.keys():
            category_dir = session_path / category
            if category_dir.exists():
                result[category] = [
                    str(f.relative_to(session_path))
                    for f in category_dir.iterdir()
                    if f.is_file()
                ]
        
        return result
    
    def cleanup_session(self, session_id: str, keep_logs: bool = True):
        """
        Clean up session files (optional, for testing)
        
        Args:
            session_id: Session ID
            keep_logs: Whether to keep log files
        """
        session_path = self.get_session_path(session_id)
        
        if not session_path.exists():
            return
        
        import shutil
        
        for item in session_path.iterdir():
            if item.is_dir():
                if keep_logs and item.name == 'logs':
                    continue
                shutil.rmtree(item)
            elif item.is_file():
                if keep_logs and item.name.startswith('processing_log'):
                    continue
                item.unlink()
        
        logger.info(f"Cleaned up session files: {session_path}")
    
    def save_file(self, file_path: str, filename: Optional[str] = None, 
                 session_id: Optional[str] = None, job_id: Optional[str] = None,
                 subfolder: str = 'files') -> str:
        """
        Save a file locally (generic file saver)
        
        Args:
            file_path: Source file path
            filename: Optional custom filename (defaults to source filename)
            session_id: Session ID (if session-based)
            job_id: Job ID (if job-based)
            subfolder: Subfolder name (default: 'files')
        
        Returns:
            Local file path
        """
        if session_id:
            base_path = self.get_session_path(session_id)
        elif job_id:
            base_path = self.get_job_path(job_id)
        else:
            base_path = self.base_path / 'temp'
        
        file_dir = base_path / subfolder
        file_dir.mkdir(parents=True, exist_ok=True)
        
        # Use provided filename or extract from path
        if filename:
            target_filename = filename
        else:
            target_filename = Path(file_path).name
        
        local_path = file_dir / target_filename
        
        # Copy file if source exists
        if Path(file_path).exists():
            import shutil
            shutil.copy2(file_path, local_path)
        else:
            # Create empty file if source doesn't exist
            local_path.touch()
        
        logger.debug(f"Saved file to: {local_path}")
        return str(local_path)
    
    def save_json(self, data: Dict[str, Any], filename: str,
                 session_id: Optional[str] = None, job_id: Optional[str] = None,
                 subfolder: str = 'json') -> str:
        """
        Save JSON data locally
        
        Args:
            data: JSON data (dict)
            filename: Filename (should include .json extension)
            session_id: Session ID (if session-based)
            job_id: Job ID (if job-based)
            subfolder: Subfolder name (default: 'json')
        
        Returns:
            Local file path
        """
        if session_id:
            base_path = self.get_session_path(session_id)
        elif job_id:
            base_path = self.get_job_path(job_id)
        else:
            base_path = self.base_path / 'temp'
        
        json_dir = base_path / subfolder
        json_dir.mkdir(parents=True, exist_ok=True)
        
        # Ensure .json extension
        if not filename.endswith('.json'):
            filename = f"{filename}.json"
        
        local_path = json_dir / filename
        
        with open(local_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.debug(f"Saved JSON to: {local_path}")
        return str(local_path)


# Global instance (initialized when needed)
_output_manager: Optional[LocalOutputManager] = None


def get_output_manager() -> LocalOutputManager:
    """Get the global output manager instance"""
    global _output_manager
    if _output_manager is None:
        _output_manager = LocalOutputManager()
    return _output_manager


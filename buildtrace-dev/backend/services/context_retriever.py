"""
Context Retriever for Chatbot (Option 1)
Downloads OCR JSON and extracts relevant context
"""

import json
import logging
from typing import Dict, List, Optional
from gcp.database import get_db_session
from gcp.database.models import DrawingVersion
from gcp.storage import StorageService

logger = logging.getLogger(__name__)


class ContextRetriever:
    """Quick context retriever - downloads OCR JSON and extracts context"""
    
    def __init__(self, storage_service: Optional[StorageService] = None):
        self.storage = storage_service or StorageService()
    
    def get_drawing_context(self, drawing_version_id: str) -> Dict:
        """Get drawing context from OCR JSON"""
        with get_db_session() as db:
            drawing_version = db.query(DrawingVersion).filter_by(
                id=drawing_version_id
            ).first()
            
            if not drawing_version:
                return {'error': 'Drawing version not found'}
            
            if not drawing_version.ocr_result_ref:
                return {'error': 'OCR not completed for this drawing'}
            
            # Download OCR JSON
            try:
                ocr_data_bytes = self.storage.download_file(drawing_version.ocr_result_ref)
                ocr_data = json.loads(ocr_data_bytes.decode('utf-8'))
            except Exception as e:
                logger.error(f"Failed to download OCR data: {e}")
                return {'error': f'Failed to load OCR data: {str(e)}'}
            
            # Extract key information
            context = {
                'drawing': {
                    'id': drawing_version.id,
                    'drawing_name': drawing_version.drawing_name,
                    'version_number': drawing_version.version_number,
                    'project_id': drawing_version.project_id
                },
                'summary': ocr_data.get('summary', {}),
                'pages': []
            }
            
            # Extract page-by-page information
            for page_data in ocr_data.get('pages', []):
                extracted_info = page_data.get('extracted_info', {})
                sections = extracted_info.get('sections', {})
                
                page_context = {
                    'page_number': page_data.get('page_number'),
                    'drawing_name': page_data.get('drawing_name'),
                    'key_sections': {}
                }
                
                # Extract key sections for chatbot
                # Map OCR section keys (numbered format) to readable names
                section_mapping = {
                    '1_title_block_and_project_identification': 'TITLE BLOCK & PROJECT IDENTIFICATION',
                    '5_revision_history_and_change_tracking': 'REVISION HISTORY & CHANGE TRACKING',
                    '6_keynotes_and_annotations': 'KEYNOTES & ANNOTATIONS',
                    '7_dimensions_and_measurements': 'DIMENSIONS & MEASUREMENTS',
                    '15_general_notes_and_disclaimers': 'GENERAL NOTES & DISCLAIMERS',
                }
                
                # Extract all sections - use actual keys from OCR
                for section_key, section_data in sections.items():
                    # Map to readable name if available, otherwise use original key
                    readable_name = section_mapping.get(section_key, section_key)
                    page_context['key_sections'][readable_name] = section_data
                
                # Also store all sections with original keys for completeness
                page_context['all_sections'] = sections
                
                context['pages'].append(page_context)
            
            return context
    
    def get_multiple_drawings_context(self, drawing_version_ids: List[str]) -> Dict:
        """Get context from multiple drawings (for comparison questions)"""
        all_contexts = []
        for dv_id in drawing_version_ids:
            context = self.get_drawing_context(dv_id)
            if 'error' not in context:
                all_contexts.append(context)
        
        return {
            'drawings': all_contexts,
            'count': len(all_contexts)
        }
    
    def format_context_for_prompt(self, context: Dict) -> str:
        """Format context as text for GPT prompt - includes ALL available data"""
        lines = []
        
        # Drawing info
        if 'drawing' in context:
            drawing = context['drawing']
            lines.append(f"Drawing: {drawing.get('drawing_name')} (Version {drawing.get('version_number')})")
            lines.append("")
        
        # Summary - show full summary
        if 'summary' in context and context['summary']:
            summary = context['summary']
            if isinstance(summary, dict):
                lines.append("Summary:")
                import json
                # Show full summary as JSON for better context
                lines.append(json.dumps(summary, indent=2))
            elif isinstance(summary, str):
                lines.append(f"Summary: {summary}")
            lines.append("")
        
        # Page-by-page information - show ALL sections, not just key ones
        if 'pages' in context:
            for page in context['pages']:
                page_num = page.get('page_number', '?')
                drawing_name = page.get('drawing_name', '')
                lines.append(f"=== Page {page_num}: {drawing_name} ===")
                
                sections = page.get('key_sections', {})
                
                # If no key_sections, try to get from extracted_info directly
                if not sections and 'extracted_info' in page:
                    extracted_info = page.get('extracted_info', {})
                    sections = extracted_info.get('sections', {})
                
                # Show ALL sections found
                if sections:
                    for section_name, section_data in sections.items():
                        lines.append(f"\n--- {section_name} ---")
                        if isinstance(section_data, dict):
                            # Show all keys in the section
                            import json
                            lines.append(json.dumps(section_data, indent=2))
                        elif isinstance(section_data, str):
                            lines.append(section_data)
                        elif isinstance(section_data, list):
                            for item in section_data:
                                if isinstance(item, dict):
                                    lines.append(json.dumps(item, indent=2))
                                else:
                                    lines.append(str(item))
                        else:
                            lines.append(str(section_data))
                else:
                    # If no sections, show raw extracted_info
                    if 'extracted_info' in page:
                        extracted_info = page.get('extracted_info', {})
                        lines.append("\nRaw extracted information:")
                        import json
                        lines.append(json.dumps(extracted_info, indent=2))
                
                lines.append("")
        
        return "\n".join(lines)
    
    def format_multiple_context_for_prompt(self, contexts: Dict) -> str:
        """Format multiple drawings' context for prompt"""
        lines = []
        lines.append(f"Context from {contexts.get('count', 0)} drawing(s):")
        lines.append("")
        
        for i, drawing_context in enumerate(contexts.get('drawings', []), 1):
            drawing = drawing_context.get('drawing', {})
            lines.append(f"=== Drawing {i}: {drawing.get('drawing_name')} (v{drawing.get('version_number')}) ===")
            lines.append(self.format_context_for_prompt(drawing_context))
            lines.append("")
        
        return "\n".join(lines)


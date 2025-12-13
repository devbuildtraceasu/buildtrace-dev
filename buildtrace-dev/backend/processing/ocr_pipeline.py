"""OCR pipeline for BuildTrace.

Extracts drawing names, converts PDF to PNG, and extracts detailed information
from each page using Google Gemini 2.5 Pro (primary) or OpenAI Vision API (fallback).
Stores page-by-page logs and generates a summary for display during comparison.
"""

from __future__ import annotations

import hashlib
import logging
import tempfile
import json
import base64
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List

from gcp.database import get_db_session
from gcp.database.models import DrawingVersion
from gcp.storage import StorageService
from utils.drawing_extraction import extract_drawing_names
from utils.pdf_parser import pdf_to_png, process_pdf_with_drawing_names
from config import config

logger = logging.getLogger(__name__)

# Try to import Google Generative AI (Gemini)
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("Google Generative AI library not available - will try OpenAI fallback")

# Try to import OpenAI as fallback
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI library not available - detailed OCR will be limited")


class OCRPipeline:
    """Extracts drawing names, converts PDF to PNG, and extracts detailed information from each page."""

    def __init__(
        self,
        storage_service: Optional[StorageService] = None,
        session_factory=None,
        dpi: int = 300,
    ) -> None:
        self.storage = storage_service or StorageService()
        self.session_factory = session_factory or get_db_session
        self.dpi = dpi
        
        # Initialize Gemini client (primary) - using Gemini 2.5 Pro
        self.gemini_model = None
        gemini_api_key = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
        if GEMINI_AVAILABLE and gemini_api_key:
            try:
                genai.configure(api_key=gemini_api_key)
                # Use gemini-2.5-pro-preview or gemini-2.0-flash-exp for structured output
                model_name = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash-exp')
                self.gemini_model = genai.GenerativeModel(model_name)
                logger.info(f"Gemini client initialized with model: {model_name}")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini: {e}")
                self.gemini_model = None
        
        # Initialize OpenAI client as fallback
        self.openai_client = None
        self.model = None
        api_key = os.getenv('OPENAI_API_KEY') or config.OPENAI_API_KEY
        if OPENAI_AVAILABLE and api_key:
            self.openai_client = OpenAI(api_key=api_key, timeout=180.0)
            self.model = os.getenv('OPENAI_MODEL') or config.OPENAI_MODEL or "gpt-4o"
            logger.info(f"OpenAI client initialized as fallback with model: {self.model}")
        
        if not self.gemini_model and not self.openai_client:
            logger.warning("No AI client initialized - detailed OCR will be limited")

    def run(self, drawing_version_id: str) -> Dict:
        """Process a drawing version: extract names, convert to PNG, extract text."""
        logger.info("Starting OCR pipeline", extra={"drawing_version_id": drawing_version_id})

        with self.session_factory() as db:
            drawing_version = db.query(DrawingVersion).filter_by(id=drawing_version_id).first()
            if not drawing_version:
                raise ValueError(f"DrawingVersion {drawing_version_id} not found")

            drawing = drawing_version.drawing
            if not drawing or not drawing.storage_path:
                raise ValueError(f"Drawing storage missing for version {drawing_version_id}")

            # Download PDF from storage
            pdf_bytes = self.storage.download_file(drawing.storage_path)

            # Fast-path for automated tests to avoid heavyweight OCR work
            if os.getenv('FAST_TEST_MODE') == '1':
                drawing_name = drawing_version.drawing_name or drawing.filename or f"drawing-{drawing_version.version_number}"
                fake_page = {
                    'drawing_name': drawing_name,
                    'page_number': 1,
                    'png_path': None,
                    'extracted_info': {'sections': {}, 'extraction_method': 'fast-test'},
                    'processed_at': datetime.utcnow().isoformat()
                }
                ocr_payload = {
                    'drawing_version_id': drawing_version_id,
                    'drawing_name': drawing_name,
                    'drawing_names': [drawing_name],
                    'pages': [fake_page],
                    'total_pages': 1,
                    'hash': hashlib.sha256(pdf_bytes).hexdigest(),
                    'byte_length': len(pdf_bytes),
                    'generated_at': datetime.utcnow().isoformat(),
                    'log_file_ref': None,
                    'summary': {
                        'total_pages': 1,
                        'drawings_found': [drawing_name],
                        'project_info': {'projects': [], 'total_drawings': 1},
                        'architect_info': {'architects': []},
                        'revision_summary': {'total_revisions': 0, 'revisions_by_drawing': []},
                        'extraction_summary': {'pages_with_info': 0, 'extraction_methods': ['fast-test']}
                    },
                }
                result_ref = self.storage.upload_ocr_result(drawing_version_id, ocr_payload)
                drawing_version.ocr_status = "completed"
                drawing_version.ocr_result_ref = result_ref
                drawing_version.ocr_completed_at = datetime.utcnow()
                db.commit()
                logger.info(
                    "OCR fast-test mode completed",
                    extra={"drawing_version_id": drawing_version_id, "result_ref": result_ref},
                )
                return {
                    "result_ref": result_ref,
                    "drawing_names": [drawing_name],
                    "pages_processed": 1,
                    "summary": ocr_payload['summary'],
                }

            # Save to temp file for processing
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_pdf:
                tmp_pdf.write(pdf_bytes)
                tmp_pdf_path = tmp_pdf.name
            
            try:
                # Step 1: Extract drawing names from PDF
                logger.info("Extracting drawing names from PDF...")
                drawing_names_data = extract_drawing_names(tmp_pdf_path)
                drawing_names = [d.get('drawing_name') for d in drawing_names_data if d.get('drawing_name')]
                
                logger.info(f"Found {len(drawing_names)} drawing names: {drawing_names}")
                
                # Step 2: Convert PDF pages to PNG with drawing names
                logger.info("Converting PDF pages to PNG...")
                with tempfile.TemporaryDirectory() as temp_dir:
                    png_paths = process_pdf_with_drawing_names(tmp_pdf_path, dpi=self.dpi)
                    
                    # Step 3: Extract detailed information from each page using OpenAI Vision
                    logger.info("Extracting detailed information from each page...")
                    
                    ocr_log_file = Path(temp_dir) / f"ocr_log_{drawing_version_id}.json"
                    ocr_log = {
                        'drawing_version_id': drawing_version_id,
                        'started_at': datetime.utcnow().isoformat(),
                        'pages': [],
                        'summary': None
                    }
                    
                    ocr_results = []
                    for i, (png_path, drawing_info) in enumerate(zip(png_paths, drawing_names_data)):
                        drawing_name = drawing_info.get('drawing_name') or f"Page_{i+1}"
                        page_num = drawing_info.get('page', i + 1)
                        
                        logger.info(f"Processing page {page_num}/{len(png_paths)}: {drawing_name}")
                        
                        # Extract detailed information from this page
                        page_info = self._extract_page_information(png_path, drawing_name, page_num)
                        
                        ocr_result = {
                            'drawing_name': drawing_name,
                            'page_number': page_num,
                            'png_path': png_path,
                            'extracted_info': page_info,
                            'processed_at': datetime.utcnow().isoformat()
                        }
                        ocr_results.append(ocr_result)
                        
                        # Update log file after each page
                        ocr_log['pages'].append({
                            'page_number': page_num,
                            'drawing_name': drawing_name,
                            'extracted_info': page_info,
                            'processed_at': datetime.utcnow().isoformat()
                        })
                        
                        # Write log file after each page (for real-time updates)
                        with open(ocr_log_file, 'w') as f:
                            json.dump(ocr_log, f, indent=2)
                        
                        logger.info(f"✓ Page {page_num} processed: {len(page_info.get('sections', {}))} sections extracted")
                    
                    # Step 4: Generate summary after all pages are processed
                    logger.info("Generating summary from all pages...")
                    summary = self._generate_summary(ocr_results)
                    ocr_log['summary'] = summary
                    ocr_log['completed_at'] = datetime.utcnow().isoformat()
                    
                    # Final log file write
                    with open(ocr_log_file, 'w') as f:
                        json.dump(ocr_log, f, indent=2)
                    
                    logger.info("✓ Summary generated")
                
                # Calculate file hash
                fingerprint = hashlib.sha256(pdf_bytes).hexdigest()
                
                # Upload log file to storage
                log_file_ref = None
                if ocr_log_file.exists():
                    with open(ocr_log_file, 'rb') as f:
                        log_bytes = f.read()
                    log_file_ref = self.storage.upload_file(
                        log_bytes,
                        f"ocr_logs/{drawing_version_id}/ocr_log.json",
                        content_type='application/json'
                    )
                    logger.info(f"OCR log file uploaded: {log_file_ref}")
                
                # Prepare OCR payload
                ocr_payload = {
                    "drawing_version_id": drawing_version_id,
                    "drawing_name": drawing_version.drawing_name,
                    "drawing_names": drawing_names,
                    "pages": ocr_results,
                    "total_pages": len(drawing_names_data),
                    "hash": fingerprint,
                    "byte_length": len(pdf_bytes),
                    "generated_at": datetime.utcnow().isoformat(),
                    "log_file_ref": log_file_ref,
                    "summary": summary,  # Include summary for display
                }

                # Upload OCR results to storage
                result_ref = self.storage.upload_ocr_result(drawing_version_id, ocr_payload)
                
                # Update database
                drawing_version.ocr_status = "completed"
                drawing_version.ocr_result_ref = result_ref
                drawing_version.ocr_completed_at = datetime.utcnow()
                db.commit()

                logger.info(
                    "OCR pipeline completed",
                    extra={
                        "drawing_version_id": drawing_version_id,
                        "result_ref": result_ref,
                        "pages_processed": len(drawing_names_data),
                        "drawing_names": drawing_names,
                    },
                )

                return {
                    "drawing_version_id": drawing_version_id,
                    "result_ref": result_ref,
                    "hash": fingerprint,
                    "pages_processed": len(drawing_names_data),
                    "drawing_names": drawing_names,
                }
                
            finally:
                # Cleanup temp file
                Path(tmp_pdf_path).unlink(missing_ok=True)
    
    def _extract_page_information(self, png_path: str, drawing_name: str, page_num: int) -> Dict:
        """Extract detailed information from a single page using Gemini 2.5 Pro (primary) or OpenAI Vision API (fallback)"""
        try:
            # Read image bytes
            with open(png_path, 'rb') as f:
                image_bytes = f.read()
            
            # Try Gemini first (primary)
            gemini_api_key = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
            if GEMINI_AVAILABLE and gemini_api_key:
                try:
                    result = self._extract_with_gemini(image_bytes, drawing_name, page_num)
                    if result:
                        return result
                except Exception as e:
                    logger.warning(f"Gemini extraction failed, falling back to OpenAI: {e}")
            
            # Fallback to OpenAI
            api_key = os.getenv('OPENAI_API_KEY') or config.OPENAI_API_KEY
            if not api_key or not OPENAI_AVAILABLE:
                # Final fallback: return basic info
                return {
                    'drawing_name': drawing_name,
                    'page_number': page_num,
                    'sections': {},
                    'extraction_method': 'basic'
                }
            
            # Re-initialize OpenAI client with current API key if needed
            if not self.openai_client or api_key != getattr(self, '_last_api_key', None):
                self.openai_client = OpenAI(api_key=api_key, timeout=180.0)
                self._last_api_key = api_key
                logger.info(f"OpenAI client re-initialized with key length: {len(api_key)}")
            
            # Convert to base64 for OpenAI
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # Expert-level extraction prompt designed by prompt engineers for construction managers and architects
            extraction_prompt = f"""You are an expert architectural drawing analyst with deep expertise in construction documentation, building codes, and project management. Your task is to extract EVERY piece of information from this architectural drawing page ({drawing_name}, page {page_num}) that would be critical for construction managers, architects, engineers, and project stakeholders.

ANALYZE THE ENTIRE DRAWING SYSTEMATICALLY:

1. **TITLE BLOCK & PROJECT IDENTIFICATION** (Bottom-right corner, typically)
   - Project name (full legal name if visible)
   - Project address (street, city, state, ZIP, country)
   - Project number (job number, contract number)
   - Sheet/Drawing number (e.g., A-101, S-12, E-5.3)
   - Drawing title/description (what this sheet shows)
   - View type (plan, elevation, section, detail, schedule, etc.)
   - Scale (written scale, graphic scale, or "NTS" if not to scale)
   - Document type (Architectural, Structural, MEP, Civil, Landscape, etc.)
   - Sheet number and total sheets (e.g., "Sheet 1 of 15")
   - Date of issue/creation
   - Drawing size (A, B, C, D, E size or metric equivalent)

2. **CLIENT & OWNERSHIP INFORMATION**
   - Client name (full legal entity name)
   - Owner name and contact information
   - Developer information (if different from owner)
   - Property owner details
   - Any ownership or use restrictions noted

3. **DESIGN TEAM & CONSULTANTS** (Extract ALL names, addresses, phone numbers, emails)
   - Architectural firm (name, address, phone, email, license number if visible)
   - Principal architect/designer name
   - Civil engineer (firm, contact, license)
   - Structural engineer (firm, contact, license)
   - Mechanical engineer (firm, contact, license)
   - Electrical engineer (firm, contact, license)
   - Plumbing engineer (firm, contact, license)
   - Landscape architect (firm, contact, license)
   - Interior designer (firm, contact)
   - Survey company (firm, contact, survey date)
   - Geotechnical engineer (if present)
   - Environmental consultant (if present)
   - Code consultant (if present)
   - Any other consultants or specialists

4. **PROJECT TEAM & RESPONSIBILITIES**
   - Project Manager (name, contact)
   - Project Architect/Lead Designer
   - Job Captain/Project Leader
   - Drawn by (draftsperson name)
   - Checked by/Reviewed by
   - Approved by
   - Any other team members with roles

5. **REVISION HISTORY & CHANGE TRACKING** (Critical for version control)
   - ALL revision letters/numbers (A, B, C, 1, 2, 3, etc.)
   - Date for EACH revision
   - Description of changes for EACH revision
   - Revision cloud locations (if visible on this sheet)
   - Addendum numbers and dates
   - Change order references
   - RFI (Request for Information) references
   - Any "Issued for" notations (Bidding, Construction, Permit, etc.)

6. **KEYNOTES & ANNOTATIONS** (CRITICAL - Extract EVERY numbered or lettered note on the drawing)
   - ALL keynote numbers (1, 2, 3, A, B, C, etc.) and their EXACT corresponding text descriptions
   - Keynote locations (if visible, note where on the drawing they appear)
   - General notes (any text blocks with instructions, numbered lists, bullet points)
   - Detail callouts (section markers like "SECTION A-A", detail markers like "DETAIL 1")
   - Reference drawings (other sheets referenced, e.g., "SEE SHEET S-5", "REFER TO C-2")
   - Material callouts and specifications (any text describing materials)
   - Dimension callouts and measurements (any dimension text, even if in the drawing area)
   - Any numbered or lettered annotations with descriptions
   - Leader lines and their associated text
   - Any text annotations, labels, or callouts anywhere on the drawing

7. **DIMENSIONS & MEASUREMENTS** (Critical for construction)
   - Overall building dimensions
   - Room dimensions (if floor plan)
   - Wall thicknesses
   - Door and window sizes
   - Ceiling heights
   - Floor-to-floor heights
   - Any other dimensional information visible

8. **AREA SUMMARIES & CALCULATIONS** (If present)
   - Gross floor area (GFA)
   - Net floor area (NFA)
   - Usable area
   - Building area
   - Lot area
   - Setback dimensions
   - Coverage percentage
   - Floor area ratio (FAR)
   - Any area calculations or summaries in tables

9. **SYMBOLS & LEGENDS** (Extract ALL symbols and their meanings)
   - Door symbols and types
   - Window symbols and types
   - Material symbols and patterns
   - Equipment symbols
   - Electrical symbols
   - Plumbing symbols
   - HVAC symbols
   - Structural symbols
   - Any other symbols with their legends/meanings

10. **SPECIFICATIONS & MATERIAL CALLOUTS**
    - Material specifications (concrete strength, steel grade, etc.)
    - Finish specifications
    - Equipment specifications
    - Product model numbers
    - Manufacturer names
    - Installation notes
    - Performance requirements

11. **BUILDING CODE & COMPLIANCE INFORMATION**
    - Building code edition referenced (IBC, CBC, etc.)
    - Occupancy classification
    - Construction type
    - Fire rating requirements
    - Accessibility compliance notes (ADA, etc.)
    - Energy code compliance
    - Any code-related annotations

12. **GRID LINES & COORDINATE SYSTEMS**
    - Grid line labels (A, B, C, 1, 2, 3, etc.)
    - Grid spacing dimensions
    - Datum/elevation references
    - Coordinate system information (if present)
    - North arrow orientation

13. **SCHEDULES & TABLES** (Extract ALL tabular data)
    - Door schedules (door numbers, types, sizes, materials, hardware)
    - Window schedules (window numbers, types, sizes, materials)
    - Room finish schedules (room numbers, floor, wall, ceiling finishes)
    - Equipment schedules
    - Any other schedules or tables with data

14. **DETAILS & SECTIONS** (If this sheet contains details)
    - Detail markers and their locations
    - Section cut markers and their locations
    - Detail descriptions
    - Material callouts in details

15. **GENERAL NOTES & DISCLAIMERS** (Extract ALL text blocks)
    - General notes (any numbered or bulleted lists)
    - Disclaimers
    - Legal notices
    - Copyright information
    - Use restrictions
    - Liability disclaimers
    - Any other text blocks with important information

16. **VISUAL ELEMENTS & GRAPHICS**
    - Drawing type description (what is being shown)
    - View direction/orientation
    - Any special graphic elements or diagrams
    - Site context information (if site plan)
    - Adjacent building information (if relevant)

17. **QUALITY ASSURANCE & COORDINATION**
    - Coordination notes between disciplines
    - Quality control notes
    - Field verification requirements
    - As-built notation requirements

18. **ANY OTHER INFORMATION**
    - Any text, numbers, or symbols not covered above
    - Any annotations, markups, or handwritten notes (if legible)
    - Any special instructions or requirements
    - Any references to other documents, standards, or specifications

CRITICAL INSTRUCTIONS:
- Extract EVERY piece of text, number, and symbol visible on the drawing
- If information is partially visible or unclear, note it as "Partially visible: [text]" or "Unclear: [description]"
- Preserve exact formatting, capitalization, and punctuation where possible
- For dimensions, include units (feet, inches, meters, etc.)
- For dates, preserve exact format
- For contact information, extract complete addresses, phone numbers, emails
- If a section doesn't apply or isn't visible, use "N/A" or empty array/object as appropriate
- Be exhaustive - construction managers need EVERY detail for accurate cost estimation, scheduling, and coordination

OUTPUT FORMAT:
Return a comprehensive JSON object with all sections above. Use arrays for lists (revisions, keynotes, dimensions, etc.) and objects for structured data. Ensure the JSON is valid and complete."""
            
            # Call OpenAI Vision API
            model_to_use = os.getenv('OPENAI_MODEL') or self.model or 'gpt-4o'
            
            api_params = {
                "model": model_to_use,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert architectural drawing analyst with 20+ years of experience in construction documentation, building codes, and project management. You have worked extensively with construction managers, architects, engineers, and contractors. Your expertise includes reading and interpreting architectural drawings, construction documents, specifications, and technical drawings. You understand the critical information needed for cost estimation, scheduling, coordination, code compliance, and construction execution. Always extract information with the precision and thoroughness expected by construction professionals. Always respond with valid, comprehensive JSON."
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": extraction_prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}",
                                    "detail": "high"  # Use high detail for maximum accuracy
                                }
                            }
                        ]
                    }
                ],
                "response_format": {"type": "json_object"}  # Request JSON response
            }
            
            api_params["max_completion_tokens"] = 4000
            
            response = self.openai_client.chat.completions.create(**api_params)
            
            # Get full raw response (don't parse - store as-is in log file)
            response_text = response.choices[0].message.content
            
            # Parse response for structured data (but keep raw response intact)
            try:
                extracted_data = json.loads(response_text)
            except json.JSONDecodeError:
                # If JSON parsing fails, try to extract structured info from text
                extracted_data = self._parse_text_response(response_text)
            
            return {
                'drawing_name': drawing_name,
                'page_number': page_num,
                'sections': extracted_data,
                'extraction_method': 'openai_vision',
                'raw_response': response_text  # Store FULL raw response (not truncated)
            }
        except Exception as e:
            logger.error(f"Error extracting page information: {e}", exc_info=True)
            return {
                'drawing_name': drawing_name,
                'page_number': page_num,
                'sections': {},
                'extraction_method': 'error',
                'raw_response': f'Error: {str(e)}'
            }
    
    def _extract_with_gemini(self, image_bytes: bytes, drawing_name: str, page_num: int) -> Optional[Dict]:
        """Extract information using Google Gemini 2.5 Pro with structured output"""
        try:
            gemini_api_key = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
            if not gemini_api_key:
                return None
            
            # Re-configure if needed
            genai.configure(api_key=gemini_api_key)
            
            # Use the latest Gemini model with vision capabilities
            model_name = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash-exp')
            model = genai.GenerativeModel(model_name)
            
            # Create image part for Gemini
            import PIL.Image
            import io
            image = PIL.Image.open(io.BytesIO(image_bytes))
            
            # Structured extraction prompt
            extraction_prompt = f"""Analyze this architectural/construction drawing page ({drawing_name}, page {page_num}) and extract ALL information in a structured JSON format.

Extract the following information if present:

1. TITLE_BLOCK: project_name, project_address, project_number, sheet_number, drawing_title, scale, date, revision
2. DESIGN_TEAM: architect_firm, architect_name, engineer_firms, consultants (list all with names, addresses, phones, emails)
3. REVISIONS: list of {{revision_number, date, description}}
4. KEYNOTES: list of {{number, description}} - EXTRACT ALL numbered keynotes visible
5. DIMENSIONS: overall_dimensions, room_dimensions, key_measurements
6. SPECIFICATIONS: materials, finishes, equipment mentioned
7. SCHEDULES: any door/window/room schedules as structured data
8. GENERAL_NOTES: list of all general notes text
9. DRAWING_TYPE: floor_plan, elevation, section, detail, schedule, site_plan, etc.
10. GRID_LINES: list of grid line labels (A, B, C, 1, 2, 3, etc.)

Return ONLY valid JSON with these keys. If a section is not visible, use null or empty array.
Be thorough - construction managers need every detail for cost estimation and coordination."""

            # Generate with Gemini
            response = model.generate_content(
                [extraction_prompt, image],
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=4000,
                )
            )
            
            response_text = response.text
            
            # Try to parse as JSON
            try:
                # Clean up response if it has markdown code blocks
                if '```json' in response_text:
                    response_text = response_text.split('```json')[1].split('```')[0]
                elif '```' in response_text:
                    response_text = response_text.split('```')[1].split('```')[0]
                
                extracted_data = json.loads(response_text.strip())
            except json.JSONDecodeError:
                # If JSON parsing fails, wrap the text response
                extracted_data = {'raw_text': response_text}
            
            logger.info(f"Gemini extraction successful for page {page_num}")
            
            return {
                'drawing_name': drawing_name,
                'page_number': page_num,
                'sections': extracted_data,
                'extraction_method': 'gemini_2.5_pro',
                'raw_response': response_text
            }
            
        except Exception as e:
            logger.error(f"Gemini extraction error: {e}", exc_info=True)
            return None

    def _parse_text_response(self, text: str) -> Dict:
        """Parse text response into structured format if JSON parsing fails"""
        sections = {}
        current_section = None
        current_content = []
        
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detect section headers
            if line.startswith('**') and line.endswith('**'):
                if current_section:
                    sections[current_section] = '\n'.join(current_content)
                current_section = line.strip('*').strip()
                current_content = []
            else:
                current_content.append(line)
        
        if current_section:
            sections[current_section] = '\n'.join(current_content)
        
        return sections
    
    def _generate_summary(self, ocr_results: List[Dict]) -> Dict:
        """Generate a comprehensive summary from all page extractions"""
        try:
            # Collect all unique information across pages
            all_projects = set()
            all_drawings = set()
            all_architects = set()
            all_revisions = []
            all_consultants = {}
            
            for result in ocr_results:
                info = result.get('extracted_info', {})
                sections = info.get('sections', {})
                
                # Extract project info
                if 'Project & Drawing Identification' in sections:
                    proj_info = sections['Project & Drawing Identification']
                    if 'Project name' in proj_info:
                        all_projects.add(proj_info.split('Project name:')[1].split('\n')[0].strip() if 'Project name:' in proj_info else '')
                
                # Extract drawing names
                drawing_name = result.get('drawing_name')
                if drawing_name:
                    all_drawings.add(drawing_name)
                
                # Extract architect info
                if 'Architect & Consultants' in sections:
                    arch_info = sections['Architect & Consultants']
                    if 'Architectural firm' in arch_info or 'Firm:' in arch_info:
                        all_architects.add(arch_info)
                
                # Extract revisions
                if 'Drawing/Revision History' in sections:
                    rev_info = sections['Drawing/Revision History']
                    all_revisions.append({
                        'drawing': drawing_name,
                        'revisions': rev_info
                    })
            
            # Create summary
            summary = {
                'total_pages': len(ocr_results),
                'drawings_found': list(all_drawings),
                'project_info': {
                    'projects': list(all_projects) if all_projects else [],
                    'total_drawings': len(all_drawings)
                },
                'architect_info': {
                    'architects': list(all_architects) if all_architects else []
                },
                'revision_summary': {
                    'total_revisions': len(all_revisions),
                    'revisions_by_drawing': all_revisions
                },
                'extraction_summary': {
                    'pages_with_info': len([r for r in ocr_results if r.get('extracted_info', {}).get('sections')]),
                    'extraction_methods': list(set([r.get('extracted_info', {}).get('extraction_method', 'unknown') for r in ocr_results]))
                }
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}", exc_info=True)
            return {
                'total_pages': len(ocr_results),
                'error': str(e)
            }


    # =========================================================================
    # STREAMING MODE: Process single page from pre-extracted PNG
    # =========================================================================
    
    def run_page(self, page_gcs_path: str, page_identifier: str) -> Dict:
        """
        Process a single page image for OCR (streaming mode).
        
        Args:
            page_gcs_path: GCS path to the PNG image
            page_identifier: Identifier for this page (e.g., "old_page_1", "new_page_2")
            
        Returns:
            Dict with result_ref and extracted info
        """
        logger.info(
            "Running OCR on single page",
            extra={"page_gcs_path": page_gcs_path, "page_identifier": page_identifier}
        )
        
        # Download page image
        page_bytes = self.storage.download_file(page_gcs_path)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save locally for processing
            png_path = Path(temp_dir) / f"{page_identifier}.png"
            png_path.write_bytes(page_bytes)
            
            # Extract information from the page
            page_info = self._extract_page_information(
                str(png_path),
                page_identifier,
                1  # Single page
            )
            
            # Create OCR result payload
            ocr_payload = {
                "page_identifier": page_identifier,
                "page_gcs_path": page_gcs_path,
                "extracted_info": page_info,
                "processed_at": datetime.utcnow().isoformat(),
            }
            
            # Upload result to GCS
            result_ref = self.storage.upload_file(
                json.dumps(ocr_payload).encode('utf-8'),
                f"ocr_pages/{page_identifier}.json",
                content_type='application/json'
            )
            
            logger.info(
                "Page OCR complete",
                extra={"page_identifier": page_identifier, "result_ref": result_ref}
            )
            
            return {
                "result_ref": result_ref,
                "page_identifier": page_identifier,
                "extracted_info": page_info
            }


__all__ = ["OCRPipeline"]

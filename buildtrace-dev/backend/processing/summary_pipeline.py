"""Summary pipeline that generates AI-powered change summaries from diff results.

Generates DUAL AI summaries using both Gemini (AI-1) and GPT (AI-2) for comparison.
Uses enhanced prompts from prompts_v2.py for comprehensive analysis.
"""

from __future__ import annotations

import json
import logging
import uuid
import base64
import os
import io
from datetime import datetime
from typing import Dict, Optional, List, Tuple
from pathlib import Path

from gcp.database import get_db_session
from gcp.database.models import ChangeSummary, DiffResult
from gcp.storage import StorageService
from config import config
from processing.prompts_v2 import SYSTEM_PROMPT_V2, USER_PROMPT_V2_3IMAGE, USER_PROMPT_V2_OVERLAY_ONLY

logger = logging.getLogger(__name__)

# OpenAI availability
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI library not available - GPT summary generation will be limited")

# Gemini availability
try:
    import google.generativeai as genai
    import PIL.Image
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None
    logger.warning("google-generativeai or PIL not available - Gemini summary generation will be limited")


class SummaryPipeline:
    """Generate AI-powered summary text for a diff result using DUAL AI models (Gemini + GPT)."""

    def __init__(
        self,
        storage_service: Optional[StorageService] = None,
        session_factory=None,
    ) -> None:
        self.storage = storage_service or StorageService()
        self.session_factory = session_factory or get_db_session
        
        # Initialize OpenAI client if available (AI-2: GPT)
        if OPENAI_AVAILABLE and config.OPENAI_API_KEY:
            self.openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
            self.openai_model = config.OPENAI_MODEL or "gpt-4o"
            logger.info(f"OpenAI client initialized with model: {self.openai_model}")
        else:
            self.openai_client = None
            self.openai_model = None
            logger.warning("OpenAI client not initialized - GPT summaries will not be available")
        
        # Initialize Gemini client if available (AI-1: Gemini)
        self.gemini_model = None
        self.gemini_model_name = None
        gemini_api_key = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY') or getattr(config, 'GEMINI_API_KEY', None)
        if GEMINI_AVAILABLE and gemini_api_key:
            try:
                genai.configure(api_key=gemini_api_key)
                # Use gemini-2.5-pro for best results
                self.gemini_model_name = os.getenv('GEMINI_MODEL', 'gemini-2.5-pro')
                self.gemini_model = genai.GenerativeModel(self.gemini_model_name)
                logger.info(f"Gemini client initialized with model: {self.gemini_model_name}")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini client: {e}")
                self.gemini_model = None
        else:
            logger.warning("Gemini client not initialized - Gemini summaries will not be available")
        
        # Legacy compatibility
        self.model = self.openai_model

    def run(
        self,
        job_id: str,
        diff_result_id: str,
        *,
        overlay_ref: Optional[str] = None,
        metadata: Optional[Dict] = None,
        overlay_id: Optional[str] = None,
    ) -> Dict:
        """
        Generate DUAL AI summaries (Gemini as AI-1, GPT as AI-2).
        
        Both summaries are stored as separate ChangeSummary records.
        Gemini summary is set as active (is_active=True).
        GPT summary is stored as inactive (is_active=False) for frontend toggle.
        """
        logger.info(
            "Starting DUAL AI summary pipeline",
            extra={"job_id": job_id, "diff_result_id": diff_result_id, "overlay_override": bool(overlay_ref)},
        )

        with self.session_factory() as db:
            diff_result = db.query(DiffResult).filter_by(id=diff_result_id).first()
            if not diff_result:
                raise ValueError(f"DiffResult {diff_result_id} not found")

            # Download diff payload
            diff_payload = json.loads(
                self.storage.download_file(diff_result.machine_generated_overlay_ref).decode("utf-8")
            )
            
            change_count = diff_payload.get("change_count", 0)
            alignment_score = diff_payload.get("alignment_score", 1.0)
            
            # Deactivate all old summaries first
            db.query(ChangeSummary).filter_by(diff_result_id=diff_result_id, is_active=True).update({'is_active': False})
            
            summaries_created = []
            primary_summary_id = None
            primary_summary_text = None
            
            # ========== AI-1: GEMINI SUMMARY ==========
            gemini_summary = None
            if self.gemini_model and overlay_ref:
                try:
                    logger.info(f"Generating Gemini summary (AI-1) with model: {self.gemini_model_name}")
                    gemini_text, gemini_json = self._generate_gemini_summary(
                        diff_result, diff_payload, overlay_ref
                    )
                    
                    gemini_summary = ChangeSummary(
                        id=str(uuid.uuid4()),
                        diff_result_id=diff_result_id,
                        summary_text=gemini_text,
                        summary_json=gemini_json,
                        source="gemini",
                        ai_model_used=self.gemini_model_name,
                        created_by=diff_result.created_by,
                        summary_metadata=metadata or {},
                        overlay_id=overlay_id,
                        is_active=True,  # Gemini is the primary/active summary
                    )
                    db.add(gemini_summary)
                    summaries_created.append({"id": gemini_summary.id, "model": self.gemini_model_name})
                    primary_summary_id = gemini_summary.id
                    primary_summary_text = gemini_text
                    logger.info(f"Gemini summary (AI-1) created: {gemini_summary.id}")
                    
                except Exception as e:
                    logger.error(f"Gemini summary generation failed: {e}", exc_info=True)
                    # Create failed Gemini summary entry
                    gemini_summary = ChangeSummary(
                        id=str(uuid.uuid4()),
                        diff_result_id=diff_result_id,
                        summary_text=f"Gemini analysis failed: {str(e)}",
                        summary_json={
                            "ai_analysis_failed": True,
                            "error": str(e),
                            "change_count": change_count,
                            "alignment_score": alignment_score
                        },
                        source="gemini-failed",
                        ai_model_used=self.gemini_model_name,
                        created_by=diff_result.created_by,
                        summary_metadata=metadata or {},
                        overlay_id=overlay_id,
                        is_active=False,
                    )
                    db.add(gemini_summary)
            else:
                logger.warning("Gemini summary skipped - client not available or no overlay_ref")
            
            # ========== AI-2: GPT SUMMARY ==========
            gpt_summary = None
            if self.openai_client and overlay_ref:
                try:
                    logger.info(f"Generating GPT summary (AI-2) with model: {self.openai_model}")
                    gpt_text, gpt_json = self._generate_ai_summary(
                        diff_result, diff_payload, overlay_ref
                    )
                    
                    # GPT is inactive if Gemini succeeded, otherwise active
                    gpt_is_active = (gemini_summary is None or gemini_summary.source == "gemini-failed")
                    
                    gpt_summary = ChangeSummary(
                        id=str(uuid.uuid4()),
                        diff_result_id=diff_result_id,
                        summary_text=gpt_text,
                        summary_json=gpt_json,
                        source="gpt-4-vision",
                        ai_model_used=self.openai_model,
                        created_by=diff_result.created_by,
                        summary_metadata=metadata or {},
                        overlay_id=overlay_id,
                        is_active=gpt_is_active,
                    )
                    db.add(gpt_summary)
                    summaries_created.append({"id": gpt_summary.id, "model": self.openai_model})
                    
                    # If Gemini failed, use GPT as primary
                    if gpt_is_active:
                        primary_summary_id = gpt_summary.id
                        primary_summary_text = gpt_text
                    
                    logger.info(f"GPT summary (AI-2) created: {gpt_summary.id}, active: {gpt_is_active}")
                    
                except Exception as e:
                    logger.error(f"GPT summary generation failed: {e}", exc_info=True)
                    # Create failed GPT summary entry
                    gpt_summary = ChangeSummary(
                        id=str(uuid.uuid4()),
                        diff_result_id=diff_result_id,
                        summary_text=f"GPT analysis failed: {str(e)}",
                        summary_json={
                            "ai_analysis_failed": True,
                            "error": str(e),
                            "change_count": change_count,
                            "alignment_score": alignment_score
                        },
                        source="gpt-failed",
                        ai_model_used=self.openai_model,
                        created_by=diff_result.created_by,
                        summary_metadata=metadata or {},
                        overlay_id=overlay_id,
                        is_active=False,
                    )
                    db.add(gpt_summary)
            else:
                logger.warning("GPT summary skipped - client not available or no overlay_ref")
            
            # ========== FALLBACK: No AI available ==========
            if not summaries_created:
                logger.warning("No AI summaries could be generated - creating placeholder")
                placeholder_summary = ChangeSummary(
                    id=str(uuid.uuid4()),
                    diff_result_id=diff_result_id,
                    summary_text="Awaiting AI analysis. Please regenerate summary when AI service is available.",
                    summary_json={
                        "pending_ai_analysis": True,
                        "change_count": change_count,
                        "alignment_score": alignment_score
                    },
                    source="pending",
                    ai_model_used=None,
                    created_by=diff_result.created_by,
                    summary_metadata=metadata or {},
                    overlay_id=overlay_id,
                    is_active=True,
                )
                db.add(placeholder_summary)
                primary_summary_id = placeholder_summary.id
                primary_summary_text = placeholder_summary.summary_text
            
            db.commit()

            logger.info(
                "DUAL AI summary pipeline completed",
                extra={
                    "job_id": job_id, 
                    "diff_result_id": diff_result_id, 
                    "summaries_created": len(summaries_created),
                    "primary_summary_id": primary_summary_id
                },
            )

            return {
                "summary_id": primary_summary_id, 
                "summary_text": primary_summary_text,
                "summaries_created": summaries_created
            }
    
    def _generate_ai_summary(
        self, diff_result: DiffResult, diff_payload: Dict, overlay_ref: str
    ) -> Tuple[str, Dict]:
        """Generate AI summary using Vision API with 3 images (old, new, overlay)
        
        Uses all 3 images for better change detection like buildtrace-overlay
        Returns structured change data for better frontend display
        """
        try:
            # Download overlay image
            overlay_bytes = self.storage.download_file(overlay_ref)
            overlay_base64 = base64.b64encode(overlay_bytes).decode('utf-8')
            
            # Get drawing metadata
            metadata = diff_result.diff_metadata or {}
            drawing_name = metadata.get('drawing_name', 'Unknown')
            page_number = metadata.get('page_number', 1)
            
            # Try to get old and new page images for 3-image analysis
            old_page_ref = metadata.get('baseline_image_ref')
            new_page_ref = metadata.get('revised_image_ref')
            
            old_base64 = None
            new_base64 = None
            
            if old_page_ref and new_page_ref:
                try:
                    old_bytes = self.storage.download_file(old_page_ref)
                    new_bytes = self.storage.download_file(new_page_ref)
                    old_base64 = base64.b64encode(old_bytes).decode('utf-8')
                    new_base64 = base64.b64encode(new_bytes).decode('utf-8')
                    logger.info("Using 3-image analysis (old, new, overlay)")
                except Exception as e:
                    logger.warning(f"Could not load old/new images, using overlay only: {e}")
            
            # System prompt for structured output
            system_prompt = """You are an expert construction project manager analyzing architectural drawing changes.
Your task is to identify ALL changes between old and new drawing versions and provide structured, actionable output.
Be precise, specific, and focus on construction-relevant details like keynotes, general notes, and specific elements."""
            
            # User prompt - different based on whether we have 3 images or just overlay
            if old_base64 and new_base64:
                user_prompt = f"""Analyze these THREE architectural drawings for {drawing_name} (Page {page_number}):

1. BEFORE drawing - the original design
2. AFTER drawing - the updated design  
3. OVERLAY drawing - RED = removed (old only), GREEN = added (new only), GREY = unchanged

Provide a detailed analysis in this EXACT JSON format:

{{
  "drawing_code": "{drawing_name}",
  "page_number": {page_number},
  "ai_summary": "Brief 1-2 sentence summary with bullet points of main changes",
  "added_keynotes": [
    {{"number": "6", "description": "Description of new keynote"}}
  ],
  "removed_keynotes": [
    {{"number": "9", "description": "Description of removed keynote"}}
  ],
  "modified_keynotes": [
    {{"number": "8", "old_text": "Old text", "new_text": "New text"}}
  ],
  "general_notes_changes": [
    {{"note_number": "12", "change_type": "modified", "description": "What changed"}}
  ],
  "changes": [
    {{
      "id": "1",
      "title": "Short descriptive title",
      "description": "Detailed description",
      "change_type": "added|modified|removed",
      "location": "Specific grid/room reference",
      "trade_affected": "Electrical/Plumbing/HVAC/Structural/Architectural"
    }}
  ],
  "critical_change": {{
    "title": "Most impactful change",
    "reason": "Why this is critical"
  }},
  "recommendations": ["Recommendation 1", "Recommendation 2"],
  "total_changes": 0
}}

Be thorough - identify EVERY keynote change, general note change, and visual change."""
            else:
                user_prompt = f"""Analyze this drawing overlay comparing old vs new versions.
Drawing: {drawing_name} (Page {page_number})
Color coding: RED = removed (old only), GREEN = added (new only), GREY = unchanged.

Provide your analysis as a JSON object with this structure:

{{
  "drawing_code": "{drawing_name}",
  "page_number": {page_number},
  "overall_summary": "Brief summary of all changes",
  "changes": [
    {{
      "id": "1",
      "title": "Short descriptive title",
      "description": "Detailed description",
      "change_type": "added|modified|removed",
      "location": "Specific location reference",
      "trade_affected": "Primary trade affected"
    }}
  ],
  "critical_change": {{"title": "Most impactful change", "reason": "Why critical"}},
  "recommendations": ["Recommendation 1"],
  "total_changes": 0
}}

Analyze the image and return ONLY valid JSON."""
            
            # Build message content with images
            message_content = [{"type": "text", "text": user_prompt}]
            
            if old_base64 and new_base64:
                # 3-image mode: old, new, overlay
                message_content.extend([
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{old_base64}"}
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{new_base64}"}
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{overlay_base64}"}
                    }
                ])
            else:
                # Single overlay image mode
                message_content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{overlay_base64}"}
                })
            
            # Call OpenAI Vision API with higher token limit
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message_content}
                ],
                max_completion_tokens=16000,  # Increased from 4000 to handle larger responses
                response_format={"type": "json_object"}
            )
            
            # Log full response details for debugging
            choice = response.choices[0]
            finish_reason = choice.finish_reason
            response_text = choice.message.content
            
            logger.info(f"OpenAI response - model: {response.model}, finish_reason: {finish_reason}, "
                       f"content_length: {len(response_text) if response_text else 0}")
            
            # Check for content filter or other issues
            if finish_reason != "stop":
                logger.warning(f"OpenAI finish_reason was '{finish_reason}' (expected 'stop')")
                if hasattr(choice.message, 'refusal') and choice.message.refusal:
                    logger.warning(f"OpenAI refusal: {choice.message.refusal}")
            
            if response_text:
                logger.debug(f"OpenAI response (first 500 chars): {response_text[:500]}")
            
            # Parse JSON response
            try:
                # Handle None or empty response
                if not response_text:
                    raise json.JSONDecodeError("Empty response", "", 0)
                
                # Clean response - remove any markdown code blocks if present
                cleaned_response = response_text.strip()
                if cleaned_response.startswith('```'):
                    # Remove markdown code blocks
                    lines = cleaned_response.split('\n')
                    if lines[0].startswith('```'):
                        lines = lines[1:]
                    if lines and lines[-1].strip() == '```':
                        lines = lines[:-1]
                    cleaned_response = '\n'.join(lines)
                
                summary_json = json.loads(cleaned_response)
                
                # Ensure required fields exist
                if 'changes' not in summary_json:
                    summary_json['changes'] = []
                if 'total_changes' not in summary_json:
                    summary_json['total_changes'] = len(summary_json.get('changes', []))
                
                # Generate readable summary text from structured data
                changes = summary_json.get('changes', [])
                ai_summary = summary_json.get('ai_summary') or summary_json.get('overall_summary', 'Changes detected.')
                
                summary_lines = []
                
                # AI Summary section
                summary_lines.append(f'**"{drawing_name}":**')
                summary_lines.append(f"**AI Summary:** {ai_summary}")
                
                # Added Keynotes
                added_keynotes = summary_json.get('added_keynotes', [])
                if added_keynotes:
                    summary_lines.append("")
                    summary_lines.append("**Added Keynotes:**")
                    for kn in added_keynotes:
                        num = kn.get('number', '?')
                        desc = kn.get('description', '')
                        summary_lines.append(f"{num}. {desc}")
                
                # Removed Keynotes
                removed_keynotes = summary_json.get('removed_keynotes', [])
                if removed_keynotes:
                    summary_lines.append("")
                    summary_lines.append("**Removed Keynotes:**")
                    for kn in removed_keynotes:
                        num = kn.get('number', '?')
                        desc = kn.get('description', '')
                        summary_lines.append(f"{num}. {desc}")
                
                # Modified Keynotes
                modified_keynotes = summary_json.get('modified_keynotes', [])
                if modified_keynotes:
                    summary_lines.append("")
                    summary_lines.append("**Modified Keynotes:**")
                    for kn in modified_keynotes:
                        num = kn.get('number', '?')
                        old_text = kn.get('old_text', '')
                        new_text = kn.get('new_text', '')
                        summary_lines.append(f"{num}. Changed from \"{old_text}\" to \"{new_text}\"")
                
                # General Notes Changes
                general_notes = summary_json.get('general_notes_changes', [])
                if general_notes:
                    summary_lines.append("")
                    summary_lines.append("**General Notes:**")
                    for note in general_notes:
                        num = note.get('note_number', '?')
                        change_type = note.get('change_type', 'modified')
                        desc = note.get('description', '')
                        summary_lines.append(f"{num}) [{change_type.upper()}] {desc}")
                
                # Changes list
                if changes:
                    summary_lines.append("")
                    summary_lines.append(f"**{len(changes)} Changes Detected:**")
                    for i, change in enumerate(changes, 1):
                        title = change.get('title', 'Change')
                        desc = change.get('description', '')
                        change_type = change.get('change_type', 'modified').capitalize()
                        summary_lines.append(f"{i}. [{change_type}] {title}: {desc}")
                
                # Critical Change
                if summary_json.get('critical_change'):
                    crit = summary_json['critical_change']
                    summary_lines.append("")
                    summary_lines.append(f"**Critical Change:** {crit.get('title', 'N/A')} - {crit.get('reason', '')}")
                
                # Recommendations
                if summary_json.get('recommendations'):
                    summary_lines.append("")
                    summary_lines.append("**Recommendations:**")
                    for rec in summary_json['recommendations']:
                        summary_lines.append(f"• {rec}")
                
                summary_text = "\n".join(summary_lines)
                
                # Add legacy fields for backward compatibility
                summary_json['changes_found'] = [c.get('title', '') for c in changes]
                summary_json['analysis_summary'] = summary_text
                summary_json['change_count'] = len(changes)
                
                return summary_text, summary_json
                
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON response: {e}")
                logger.warning(f"Response was: {response_text[:1000] if response_text else 'None'}...")
                # Fallback to text parsing
                changes_found, critical_change, recommendations = self._parse_analysis_response(response_text)
                summary_json = {
                    "changes_found": changes_found,
                    "critical_change": critical_change,
                    "recommendations": recommendations,
                    "analysis_summary": response_text,
                    "change_count": len(changes_found),
                }
                return response_text, summary_json
            
        except Exception as e:
            logger.error(f"AI summary generation failed: {e}", exc_info=True)
            # Re-raise to indicate AI analysis failed - caller should retry or handle
            # Don't fall back to manual count, user wants AI-only summary
            raise RuntimeError(f"AI summary generation failed: {e}")
    
    def _parse_analysis_response(self, analysis_text: str) -> Tuple[List[str], str, List[str]]:
        """Parse OpenAI response to extract structured information
        
        Synced with buildtrace-overlay- parsing logic
        """
        changes_found = []
        critical_change = ""
        recommendations = []
        
        lines = analysis_text.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Detect sections
            line_lower = line.lower()
            if "critical change" in line_lower or "most significant" in line_lower or "most critical" in line_lower:
                current_section = "critical"
                continue
            elif "change list" in line_lower or "changes found" in line_lower or "changes:" in line_lower:
                current_section = "changes"
                continue
            elif "recommendation" in line_lower:
                current_section = "recommendations"
                continue
            
            # Extract numbered changes
            if line and (line[0].isdigit() or line.startswith("-") or line.startswith("*")):
                if current_section == "changes":
                    changes_found.append(line)
            
            # Extract critical change
            elif current_section == "critical" and line:
                critical_change = line
            
            # Extract recommendations
            elif current_section == "recommendations" and line:
                recommendations.append(line)
        
        return changes_found, critical_change, recommendations
    
    def _generate_gemini_summary(
        self, diff_result: DiffResult, diff_payload: Dict, overlay_ref: str
    ) -> Tuple[str, Dict]:
        """Generate AI summary using Gemini Vision API with 3 images (old, new, overlay)
        
        Uses enhanced prompts from prompts_v2.py for comprehensive analysis.
        Returns structured change data for better frontend display.
        """
        if not self.gemini_model:
            raise RuntimeError("Gemini client not initialized")
        
        try:
            # Download overlay image
            overlay_bytes = self.storage.download_file(overlay_ref)
            
            # Get drawing metadata
            metadata = diff_result.diff_metadata or {}
            drawing_name = metadata.get('drawing_name', 'Unknown')
            page_number = metadata.get('page_number', 1)
            
            # Try to get old and new page images for 3-image analysis
            old_page_ref = metadata.get('baseline_image_ref')
            new_page_ref = metadata.get('revised_image_ref')
            
            # Load images with PIL and resize if needed (Gemini has size limits)
            MAX_DIMENSION = 1600
            PIL.Image.MAX_IMAGE_PIXELS = 200000000
            
            def load_and_resize_image(img_bytes: bytes) -> 'PIL.Image.Image':
                """Load image and resize if too large for Gemini"""
                img = PIL.Image.open(io.BytesIO(img_bytes))
                if max(img.size) > MAX_DIMENSION:
                    ratio = MAX_DIMENSION / max(img.size)
                    new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                    img = img.resize(new_size, PIL.Image.Resampling.LANCZOS)
                    logger.info(f"Resized image to {new_size}")
                return img
            
            overlay_img = load_and_resize_image(overlay_bytes)
            
            old_img = None
            new_img = None
            
            if old_page_ref and new_page_ref:
                try:
                    old_bytes = self.storage.download_file(old_page_ref)
                    new_bytes = self.storage.download_file(new_page_ref)
                    old_img = load_and_resize_image(old_bytes)
                    new_img = load_and_resize_image(new_bytes)
                    logger.info("Using 3-image analysis (old, new, overlay) with Gemini")
                except Exception as e:
                    logger.warning(f"Could not load old/new images for Gemini, using overlay only: {e}")
            
            # Build prompt using prompts_v2.py
            if old_img and new_img:
                user_prompt = USER_PROMPT_V2_3IMAGE.format(
                    drawing_name=drawing_name,
                    page_number=page_number
                )
                full_prompt = f"{SYSTEM_PROMPT_V2}\n\n{user_prompt}"
                
                # Send all 3 images to Gemini
                response = self.gemini_model.generate_content(
                    [full_prompt, old_img, new_img, overlay_img],
                    generation_config=genai.types.GenerationConfig(
                        response_mime_type="application/json",
                        temperature=0.1,
                    )
                )
            else:
                user_prompt = USER_PROMPT_V2_OVERLAY_ONLY.format(
                    drawing_name=drawing_name,
                    page_number=page_number
                )
                full_prompt = f"{SYSTEM_PROMPT_V2}\n\n{user_prompt}"
                
                # Send overlay only
                response = self.gemini_model.generate_content(
                    [full_prompt, overlay_img],
                    generation_config=genai.types.GenerationConfig(
                        response_mime_type="application/json",
                        temperature=0.1,
                    )
                )
            
            # Check response
            response_text = response.text
            finish_reason = getattr(response.candidates[0], 'finish_reason', 'unknown') if response.candidates else 'no_candidates'
            
            logger.info(f"Gemini response - model: {self.gemini_model_name}, finish_reason: {finish_reason}, "
                       f"content_length: {len(response_text) if response_text else 0}")
            
            # Parse JSON response
            try:
                if not response_text:
                    raise json.JSONDecodeError("Empty response", "", 0)
                
                # Clean response - remove any markdown code blocks if present
                cleaned_response = response_text.strip()
                if cleaned_response.startswith('```'):
                    lines = cleaned_response.split('\n')
                    if lines[0].startswith('```'):
                        lines = lines[1:]
                    if lines and lines[-1].strip() == '```':
                        lines = lines[:-1]
                    cleaned_response = '\n'.join(lines)
                
                summary_json = json.loads(cleaned_response)
                
                # Ensure required fields exist
                if 'changes' not in summary_json:
                    summary_json['changes'] = []
                if 'total_changes' not in summary_json:
                    summary_json['total_changes'] = len(summary_json.get('changes', []))
                
                # Generate readable summary text from structured data
                summary_text = self._format_summary_text(summary_json, drawing_name)
                
                # Add legacy fields for backward compatibility
                changes = summary_json.get('changes', [])
                summary_json['changes_found'] = [c.get('title', '') for c in changes]
                summary_json['analysis_summary'] = summary_text
                summary_json['change_count'] = len(changes)
                
                return summary_text, summary_json
                
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse Gemini JSON response: {e}")
                logger.warning(f"Response was: {response_text[:1000] if response_text else 'None'}...")
                # Fallback to text parsing
                changes_found, critical_change, recommendations = self._parse_analysis_response(response_text or "")
                summary_json = {
                    "changes_found": changes_found,
                    "critical_change": critical_change,
                    "recommendations": recommendations,
                    "analysis_summary": response_text or "",
                    "change_count": len(changes_found),
                }
                return response_text or "Analysis completed.", summary_json
            
        except Exception as e:
            logger.error(f"Gemini summary generation failed: {e}", exc_info=True)
            raise RuntimeError(f"Gemini summary generation failed: {e}")
    
    def _format_summary_text(self, summary_json: Dict, drawing_name: str) -> str:
        """Format structured JSON summary into readable text"""
        summary_lines = []
        
        # AI Summary section
        ai_summary = summary_json.get('ai_summary') or summary_json.get('overall_summary', 'Changes detected.')
        summary_lines.append(f'**"{drawing_name}":**')
        summary_lines.append(f"**AI Summary:** {ai_summary}")
        
        # Added Keynotes
        added_keynotes = summary_json.get('added_keynotes', [])
        if added_keynotes:
            summary_lines.append("")
            summary_lines.append("**Added Keynotes:**")
            for kn in added_keynotes:
                num = kn.get('number', '?')
                desc = kn.get('description', '')
                summary_lines.append(f"{num}. {desc}")
        
        # Removed Keynotes
        removed_keynotes = summary_json.get('removed_keynotes', [])
        if removed_keynotes:
            summary_lines.append("")
            summary_lines.append("**Removed Keynotes:**")
            for kn in removed_keynotes:
                num = kn.get('number', '?')
                desc = kn.get('description', '')
                summary_lines.append(f"{num}. {desc}")
        
        # Modified Keynotes
        modified_keynotes = summary_json.get('modified_keynotes', [])
        if modified_keynotes:
            summary_lines.append("")
            summary_lines.append("**Modified Keynotes:**")
            for kn in modified_keynotes:
                num = kn.get('number', '?')
                old_text = kn.get('old_text', '')
                new_text = kn.get('new_text', '')
                summary_lines.append(f"{num}. Changed from \"{old_text}\" to \"{new_text}\"")
        
        # General Notes Changes
        general_notes = summary_json.get('general_notes_changes', [])
        if general_notes:
            summary_lines.append("")
            summary_lines.append("**General Notes:**")
            for note in general_notes:
                num = note.get('note_number', '?')
                change_type = note.get('change_type', 'modified')
                desc = note.get('description', '')
                summary_lines.append(f"{num}) [{change_type.upper()}] {desc}")
        
        # Changes list
        changes = summary_json.get('changes', [])
        if changes:
            summary_lines.append("")
            summary_lines.append(f"**{len(changes)} Changes Detected:**")
            for i, change in enumerate(changes, 1):
                title = change.get('title', 'Change')
                desc = change.get('description', '')
                change_type = change.get('change_type', 'modified').capitalize()
                summary_lines.append(f"{i}. [{change_type}] {title}: {desc}")
        
        # Critical Change
        if summary_json.get('critical_change'):
            crit = summary_json['critical_change']
            summary_lines.append("")
            summary_lines.append(f"**Critical Change:** {crit.get('title', 'N/A')} - {crit.get('reason', '')}")
        
        # Recommendations
        if summary_json.get('recommendations'):
            summary_lines.append("")
            summary_lines.append("**Recommendations:**")
            for rec in summary_json['recommendations']:
                summary_lines.append(f"• {rec}")
        
        return "\n".join(summary_lines)


__all__ = ["SummaryPipeline"]

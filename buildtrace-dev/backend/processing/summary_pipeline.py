"""Summary pipeline that generates AI-powered change summaries from diff results."""

from __future__ import annotations

import json
import logging
import uuid
import base64
import os
from datetime import datetime
from typing import Dict, Optional, List, Tuple
from pathlib import Path

from gcp.database import get_db_session
from gcp.database.models import ChangeSummary, DiffResult
from gcp.storage import StorageService
from config import config

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI library not available - summary generation will be limited")


class SummaryPipeline:
    """Generate AI-powered summary text for a diff result."""

    def __init__(
        self,
        storage_service: Optional[StorageService] = None,
        session_factory=None,
    ) -> None:
        self.storage = storage_service or StorageService()
        self.session_factory = session_factory or get_db_session
        
        # Initialize OpenAI client if available
        if OPENAI_AVAILABLE and config.OPENAI_API_KEY:
            self.openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
            self.model = config.OPENAI_MODEL or "gpt-5"
        else:
            self.openai_client = None
            self.model = None
            logger.warning("OpenAI client not initialized - will use fallback summary")

    def run(
        self,
        job_id: str,
        diff_result_id: str,
        *,
        overlay_ref: Optional[str] = None,
        metadata: Optional[Dict] = None,
        overlay_id: Optional[str] = None,
    ) -> Dict:
        logger.info(
            "Starting summary pipeline",
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
            
            # Generate summary using OpenAI if available
            if self.openai_client and overlay_ref:
                summary_text, summary_json = self._generate_ai_summary(
                    diff_result, diff_payload, overlay_ref
                )
                source = "human_corrected" if overlay_id else "machine"
                ai_model = self.model
            else:
                # Fallback to simple text summary
                changes = diff_payload.get("changes", [])
                change_count = diff_payload.get("change_count", 0)
                alignment_score = diff_payload.get("alignment_score", 1.0)
                
                if change_count > 0 or alignment_score < 0.95:
                    summary_text = f"Detected {change_count} change(s) between drawing versions. Alignment score: {alignment_score:.2f}."
                else:
                    summary_text = "No material changes detected between drawing versions."
                
                summary_json = {
                    "changes": changes,
                    "change_count": change_count,
                    "alignment_score": alignment_score
                }
                source = "rules-engine"
                ai_model = None

            # Deactivate old summaries
            db.query(ChangeSummary).filter_by(diff_result_id=diff_result_id, is_active=True).update({'is_active': False})

            summary = ChangeSummary(
                id=str(uuid.uuid4()),
                diff_result_id=diff_result_id,
                summary_text=summary_text,
                summary_json=summary_json,
                source=source,
                ai_model_used=ai_model,
                created_by=diff_result.created_by,
                metadata=metadata or {},
                overlay_id=overlay_id,
            )
            db.add(summary)
            db.commit()

            logger.info(
                "Summary pipeline completed",
                extra={"job_id": job_id, "diff_result_id": diff_result_id, "summary_id": summary.id},
            )

            return {"summary_id": summary.id, "summary_text": summary_text}
    
    def _generate_ai_summary(
        self, diff_result: DiffResult, diff_payload: Dict, overlay_ref: str
    ) -> Tuple[str, Dict]:
        """Generate AI summary using OpenAI Vision API"""
        try:
            # Download overlay image
            overlay_bytes = self.storage.download_file(overlay_ref)
            overlay_base64 = base64.b64encode(overlay_bytes).decode('utf-8')
            
            # Prepare prompt
            system_prompt = """You are an expert project manager at a general contractor company. 
Analyze the provided architectural drawing overlay and identify all changes between the old and new versions.
Focus on practical construction implications and cost impacts.
Provide a clear summary with:
1. List of changes found
2. Most critical change
3. Recommendations for the construction team"""
            
            user_prompt = """Analyze this drawing overlay showing differences between old (red) and new (green) versions.
Identify all changes, highlight the most critical change, and provide recommendations."""
            
            # Call OpenAI Vision API
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{overlay_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=2000,
                temperature=0.7
            )
            
            analysis_text = response.choices[0].message.content
            
            # Parse response to extract structured information
            changes_found, critical_change, recommendations = self._parse_analysis_response(analysis_text)
            
            summary_json = {
                "changes_found": changes_found,
                "critical_change": critical_change,
                "recommendations": recommendations,
                "analysis_summary": analysis_text,
                "change_count": len(changes_found),
            }
            
            return analysis_text, summary_json
            
        except Exception as e:
            logger.error(f"AI summary generation failed: {e}", exc_info=True)
            # Fallback to simple summary
            change_count = diff_payload.get("change_count", 0)
            return f"AI analysis unavailable. Detected {change_count} change(s).", {"change_count": change_count}
    
    def _parse_analysis_response(self, analysis_text: str) -> Tuple[List[str], str, List[str]]:
        """Parse OpenAI response to extract structured information"""
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
            if "critical change" in line.lower() or "most significant" in line.lower():
                current_section = "critical"
            elif "change list" in line.lower() or "changes found" in line.lower():
                current_section = "changes"
            elif "recommendation" in line.lower():
                current_section = "recommendations"
            
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


__all__ = ["SummaryPipeline"]

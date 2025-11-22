"""Summary pipeline that turns diff payloads into human-readable text."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Optional

from gcp.database import get_db_session
from gcp.database.models import ChangeSummary, DiffResult
from gcp.storage import StorageService

logger = logging.getLogger(__name__)


class SummaryPipeline:
    """Generate summary text for a diff result."""

    def __init__(
        self,
        storage_service: Optional[StorageService] = None,
        session_factory=None,
    ) -> None:
        self.storage = storage_service or StorageService()
        self.session_factory = session_factory or get_db_session

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

            diff_payload = json.loads(
                self.storage.download_file(diff_result.machine_generated_overlay_ref).decode("utf-8")
            )
            changes = diff_payload.get("changes", [])
            change_lines = [f"- {c['field']} changed" for c in changes] or ["- No material changes detected"]
            summary_text = "Summary of detected changes:\n" + "\n".join(change_lines)

            db.query(ChangeSummary).filter_by(diff_result_id=diff_result_id, is_active=True).update({'is_active': False})

            summary = ChangeSummary(
                id=str(uuid.uuid4()),
                diff_result_id=diff_result_id,
                summary_text=summary_text,
                summary_json={"changes": changes},
                source="human_corrected" if overlay_ref or overlay_id else "machine",
                ai_model_used="rules-engine",
                created_by=diff_result.created_by,
                metadata=metadata or {},
                overlay_id=overlay_id,
            )
            db.add(summary)

            logger.info(
                "Summary pipeline completed",
                extra={"job_id": job_id, "diff_result_id": diff_result_id, "summary_id": summary.id},
            )

            return {"summary_id": summary.id, "summary_text": summary_text}


__all__ = ["SummaryPipeline"]

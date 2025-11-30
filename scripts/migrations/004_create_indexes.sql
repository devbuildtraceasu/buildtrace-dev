-- Migration 004: Create additional performance indexes
-- Creates indexes for common query patterns

BEGIN;

-- Jobs table indexes
CREATE INDEX IF NOT EXISTS idx_jobs_old_drawing_version ON jobs(old_drawing_version_id);
CREATE INDEX IF NOT EXISTS idx_jobs_new_drawing_version ON jobs(new_drawing_version_id);
CREATE INDEX IF NOT EXISTS idx_jobs_project_status ON jobs(project_id, status);

-- Job stages indexes
CREATE INDEX IF NOT EXISTS idx_job_stages_job_stage ON job_stages(job_id, stage);
CREATE INDEX IF NOT EXISTS idx_job_stages_drawing_stage ON job_stages(drawing_version_id, stage);

-- Diff results indexes
CREATE INDEX IF NOT EXISTS idx_diff_results_job_created ON diff_results(job_id, created_at);
CREATE INDEX IF NOT EXISTS idx_diff_results_changes_detected ON diff_results(changes_detected) WHERE changes_detected = true;

-- Manual overlays indexes
CREATE INDEX IF NOT EXISTS idx_manual_overlays_diff_active ON manual_overlays(diff_result_id, is_active);
CREATE INDEX IF NOT EXISTS idx_manual_overlays_created_at ON manual_overlays(created_at);

-- Change summaries indexes
CREATE INDEX IF NOT EXISTS idx_change_summaries_diff_active ON change_summaries(diff_result_id, is_active);
CREATE INDEX IF NOT EXISTS idx_change_summaries_source_created ON change_summaries(source, created_at);
CREATE INDEX IF NOT EXISTS idx_change_summaries_overlay ON change_summaries(overlay_id) WHERE overlay_id IS NOT NULL;

-- Audit logs indexes
CREATE INDEX IF NOT EXISTS idx_audit_logs_entity_action ON audit_logs(entity_type, entity_id, action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_created ON audit_logs(user_id, created_at);

COMMIT;

-- Verify indexes
DO $$
BEGIN
    RAISE NOTICE 'Migration 004 complete: Performance indexes created';
    RAISE NOTICE 'Indexes created for: jobs, job_stages, diff_results, manual_overlays, change_summaries, audit_logs';
END $$;


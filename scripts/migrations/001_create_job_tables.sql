-- Migration 001: Create Job-Based Processing Tables
-- This migration creates new tables for the scalable job-based architecture
-- Run this first as it's non-breaking (adds new tables only)

BEGIN;

-- Table: organizations (optional, for future multi-tenant support)
CREATE TABLE IF NOT EXISTS organizations (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    name VARCHAR(255) NOT NULL,
    domain VARCHAR(255),
    plan VARCHAR(50) DEFAULT 'free',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_organizations_domain ON organizations(domain);

-- Table: jobs (replaces generic processing_jobs)
CREATE TABLE IF NOT EXISTS jobs (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    project_id VARCHAR(36) REFERENCES projects(id) ON DELETE CASCADE NOT NULL,
    old_drawing_version_id VARCHAR(36) REFERENCES drawing_versions(id),
    new_drawing_version_id VARCHAR(36) REFERENCES drawing_versions(id) NOT NULL,
    status VARCHAR(50) DEFAULT 'created',
    created_by VARCHAR(36) REFERENCES users(id) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    cancelled_at TIMESTAMP,
    cancelled_by VARCHAR(36) REFERENCES users(id),
    error_message TEXT,
    job_metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_jobs_project ON jobs(project_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_created_by ON jobs(created_by);
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at);

-- Table: job_stages (tracks individual processing stages)
CREATE TABLE IF NOT EXISTS job_stages (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    job_id VARCHAR(36) REFERENCES jobs(id) ON DELETE CASCADE NOT NULL,
    stage VARCHAR(50) NOT NULL,
    drawing_version_id VARCHAR(36) REFERENCES drawing_versions(id),
    status VARCHAR(50) DEFAULT 'pending',
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    result_ref TEXT,
    retry_count INTEGER DEFAULT 0,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(job_id, stage, drawing_version_id)
);

CREATE INDEX IF NOT EXISTS idx_job_stages_job ON job_stages(job_id);
CREATE INDEX IF NOT EXISTS idx_job_stages_status ON job_stages(status);
CREATE INDEX IF NOT EXISTS idx_job_stages_stage ON job_stages(stage);
CREATE INDEX IF NOT EXISTS idx_job_stages_drawing_version ON job_stages(drawing_version_id);

-- Table: diff_results (stores diff calculation results)
CREATE TABLE IF NOT EXISTS diff_results (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    job_id VARCHAR(36) REFERENCES jobs(id) ON DELETE CASCADE NOT NULL,
    old_drawing_version_id VARCHAR(36) REFERENCES drawing_versions(id) NOT NULL,
    new_drawing_version_id VARCHAR(36) REFERENCES drawing_versions(id) NOT NULL,
    machine_generated_overlay_ref TEXT NOT NULL,
    alignment_score FLOAT,
    changes_detected BOOLEAN DEFAULT false,
    change_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(36) REFERENCES users(id),
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_diff_results_job ON diff_results(job_id);
CREATE INDEX IF NOT EXISTS idx_diff_results_versions ON diff_results(old_drawing_version_id, new_drawing_version_id);
CREATE INDEX IF NOT EXISTS idx_diff_results_created_at ON diff_results(created_at);

-- Table: manual_overlays (human-corrected overlays)
CREATE TABLE IF NOT EXISTS manual_overlays (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    diff_result_id VARCHAR(36) REFERENCES diff_results(id) ON DELETE CASCADE NOT NULL,
    overlay_ref TEXT NOT NULL,
    created_by VARCHAR(36) REFERENCES users(id) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    parent_overlay_id VARCHAR(36) REFERENCES manual_overlays(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_manual_overlays_diff ON manual_overlays(diff_result_id);
CREATE INDEX IF NOT EXISTS idx_manual_overlays_active ON manual_overlays(diff_result_id, is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_manual_overlays_created_by ON manual_overlays(created_by);

-- Table: change_summaries (AI-generated summaries with versioning)
CREATE TABLE IF NOT EXISTS change_summaries (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    diff_result_id VARCHAR(36) REFERENCES diff_results(id) ON DELETE CASCADE NOT NULL,
    overlay_id VARCHAR(36) REFERENCES manual_overlays(id),
    summary_text TEXT NOT NULL,
    summary_json JSONB,
    source VARCHAR(50) NOT NULL,
    ai_model_used VARCHAR(50),
    created_by VARCHAR(36) REFERENCES users(id),
    is_active BOOLEAN DEFAULT true,
    parent_summary_id VARCHAR(36) REFERENCES change_summaries(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_change_summaries_diff ON change_summaries(diff_result_id);
CREATE INDEX IF NOT EXISTS idx_change_summaries_active ON change_summaries(diff_result_id, is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_change_summaries_source ON change_summaries(source);
CREATE INDEX IF NOT EXISTS idx_change_summaries_created_at ON change_summaries(created_at);

-- Table: audit_logs (audit trail for compliance)
CREATE TABLE IF NOT EXISTS audit_logs (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id VARCHAR(36) REFERENCES users(id),
    entity_type VARCHAR(50) NOT NULL,
    entity_id VARCHAR(36) NOT NULL,
    action VARCHAR(50) NOT NULL,
    changes JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created ON audit_logs(created_at);

COMMIT;

-- Verify tables were created
DO $$
BEGIN
    RAISE NOTICE 'Migration 001 complete: Job-based tables created';
    RAISE NOTICE 'Tables created: organizations, jobs, job_stages, diff_results, manual_overlays, change_summaries, audit_logs';
END $$;


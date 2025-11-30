-- Migration: Create new tables for async architecture
-- This migration adds new tables alongside existing ones (non-breaking)

-- Organizations table
CREATE TABLE IF NOT EXISTS organizations (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    name VARCHAR(255) NOT NULL,
    domain VARCHAR(255),
    plan VARCHAR(50) DEFAULT 'free',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_organizations_domain ON organizations(domain);

-- Jobs table (replaces processing_jobs for comparison workflow)
CREATE TABLE IF NOT EXISTS jobs (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    project_id VARCHAR(36) REFERENCES projects(id) ON DELETE CASCADE NOT NULL,
    old_drawing_version_id VARCHAR(36) REFERENCES drawing_versions(id) NOT NULL,
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

-- Job stages table
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

-- Diff results table
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

-- Manual overlays table
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

-- Change summaries table
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

-- Audit logs table
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

-- Enhance drawing_versions table with OCR fields
ALTER TABLE drawing_versions ADD COLUMN IF NOT EXISTS ocr_status VARCHAR(50) DEFAULT 'pending';
ALTER TABLE drawing_versions ADD COLUMN IF NOT EXISTS ocr_result_ref TEXT;
ALTER TABLE drawing_versions ADD COLUMN IF NOT EXISTS ocr_completed_at TIMESTAMP;
ALTER TABLE drawing_versions ADD COLUMN IF NOT EXISTS rasterized_image_ref TEXT;
ALTER TABLE drawing_versions ADD COLUMN IF NOT EXISTS file_hash VARCHAR(64);
ALTER TABLE drawing_versions ADD COLUMN IF NOT EXISTS file_size BIGINT;

CREATE INDEX IF NOT EXISTS idx_drawing_versions_ocr_status ON drawing_versions(ocr_status);

-- Add organization_id to projects (optional)
ALTER TABLE projects ADD COLUMN IF NOT EXISTS organization_id VARCHAR(36) REFERENCES organizations(id);

-- Add organization_id to users (optional)
ALTER TABLE users ADD COLUMN IF NOT EXISTS organization_id VARCHAR(36) REFERENCES organizations(id);


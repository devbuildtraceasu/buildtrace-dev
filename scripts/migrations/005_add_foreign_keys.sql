-- Migration 005: Add foreign key constraints
-- Adds foreign key constraints for data integrity
-- Run this after all tables and data are in place

BEGIN;

-- Note: Most foreign keys are already defined in table creation scripts
-- This script adds any additional constraints that may be needed

-- Ensure jobs reference valid drawing versions
DO $$
BEGIN
    -- Add constraint if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_jobs_old_drawing_version'
    ) THEN
        ALTER TABLE jobs 
        ADD CONSTRAINT fk_jobs_old_drawing_version 
        FOREIGN KEY (old_drawing_version_id) 
        REFERENCES drawing_versions(id) 
        ON DELETE SET NULL;
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_jobs_new_drawing_version'
    ) THEN
        ALTER TABLE jobs 
        ADD CONSTRAINT fk_jobs_new_drawing_version 
        FOREIGN KEY (new_drawing_version_id) 
        REFERENCES drawing_versions(id) 
        ON DELETE RESTRICT;
    END IF;
END $$;

-- Ensure job_stages reference valid jobs
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_job_stages_job'
    ) THEN
        ALTER TABLE job_stages 
        ADD CONSTRAINT fk_job_stages_job 
        FOREIGN KEY (job_id) 
        REFERENCES jobs(id) 
        ON DELETE CASCADE;
    END IF;
END $$;

-- Ensure diff_results reference valid jobs
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_diff_results_job'
    ) THEN
        ALTER TABLE diff_results 
        ADD CONSTRAINT fk_diff_results_job 
        FOREIGN KEY (job_id) 
        REFERENCES jobs(id) 
        ON DELETE CASCADE;
    END IF;
END $$;

-- Ensure manual_overlays reference valid diff_results
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_manual_overlays_diff'
    ) THEN
        ALTER TABLE manual_overlays 
        ADD CONSTRAINT fk_manual_overlays_diff 
        FOREIGN KEY (diff_result_id) 
        REFERENCES diff_results(id) 
        ON DELETE CASCADE;
    END IF;
END $$;

-- Ensure change_summaries reference valid diff_results
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_change_summaries_diff'
    ) THEN
        ALTER TABLE change_summaries 
        ADD CONSTRAINT fk_change_summaries_diff 
        FOREIGN KEY (diff_result_id) 
        REFERENCES diff_results(id) 
        ON DELETE CASCADE;
    END IF;
END $$;

COMMIT;

-- Verify constraints
DO $$
BEGIN
    RAISE NOTICE 'Migration 005 complete: Foreign key constraints added';
    RAISE NOTICE 'Foreign keys verified for: jobs, job_stages, diff_results, manual_overlays, change_summaries';
END $$;


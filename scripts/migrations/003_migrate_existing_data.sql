-- Migration 003: Migrate existing data to new schema
-- Migrates data from old tables (sessions, comparisons, analysis_results) to new tables (jobs, diff_results, change_summaries)
-- Run this AFTER Phase 1 migrations and application code update

BEGIN;

-- Migrate processing_jobs to jobs (if processing_jobs table exists)
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'processing_jobs') THEN
        INSERT INTO jobs (
            id, 
            project_id, 
            status, 
            created_by, 
            created_at, 
            started_at, 
            completed_at, 
            error_message, 
            job_metadata
        )
        SELECT 
            pj.id,
            COALESCE(
                (SELECT project_id FROM sessions WHERE id = pj.session_id LIMIT 1),
                (SELECT id FROM projects LIMIT 1)  -- Fallback to first project
            ) as project_id,
            pj.status,
            COALESCE(
                (SELECT user_id FROM sessions WHERE id = pj.session_id LIMIT 1),
                (SELECT id FROM users LIMIT 1)  -- Fallback to first user
            ) as created_by,
            pj.created_at,
            pj.started_at,
            pj.completed_at,
            pj.error_message,
            pj.job_metadata
        FROM processing_jobs pj
        WHERE pj.job_type = 'comparison'
        ON CONFLICT (id) DO NOTHING;
        
        RAISE NOTICE 'Migrated data from processing_jobs to jobs';
    ELSE
        RAISE NOTICE 'processing_jobs table does not exist, skipping migration';
    END IF;
END $$;

-- Migrate comparisons to diff_results (if comparisons table exists)
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'comparisons') THEN
        INSERT INTO diff_results (
            id,
            job_id,
            old_drawing_version_id,
            new_drawing_version_id,
            machine_generated_overlay_ref,
            alignment_score,
            changes_detected,
            created_at
        )
        SELECT 
            c.id,
            COALESCE(
                (SELECT id FROM jobs WHERE old_drawing_version_id = c.old_drawing_id 
                 AND new_drawing_version_id = c.new_drawing_id LIMIT 1),
                (SELECT id FROM jobs ORDER BY created_at DESC LIMIT 1)  -- Fallback
            ) as job_id,
            c.old_drawing_id as old_drawing_version_id,
            c.new_drawing_id as new_drawing_version_id,
            COALESCE(c.overlay_path, '') as machine_generated_overlay_ref,
            c.alignment_score,
            COALESCE(c.changes_detected, false) as changes_detected,
            c.created_at
        FROM comparisons c
        ON CONFLICT (id) DO NOTHING;
        
        RAISE NOTICE 'Migrated data from comparisons to diff_results';
    ELSE
        RAISE NOTICE 'comparisons table does not exist, skipping migration';
    END IF;
END $$;

-- Migrate analysis_results to change_summaries (if analysis_results table exists)
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'analysis_results') THEN
        INSERT INTO change_summaries (
            id,
            diff_result_id,
            summary_text,
            summary_json,
            source,
            created_by,
            created_at
        )
        SELECT 
            ar.id,
            COALESCE(
                (SELECT id FROM diff_results WHERE job_id = 
                    (SELECT id FROM jobs WHERE old_drawing_version_id = 
                        (SELECT old_drawing_id FROM comparisons WHERE id = ar.comparison_id LIMIT 1)
                    LIMIT 1)
                LIMIT 1),
                (SELECT id FROM diff_results ORDER BY created_at DESC LIMIT 1)  -- Fallback
            ) as diff_result_id,
            COALESCE(ar.analysis_summary, '') as summary_text,
            COALESCE(ar.changes_found, ar.recommendations, '{}'::jsonb) as summary_json,
            'machine' as source,
            COALESCE(
                (SELECT created_by FROM jobs WHERE id = 
                    (SELECT job_id FROM diff_results WHERE id = 
                        (SELECT id FROM diff_results LIMIT 1) LIMIT 1) LIMIT 1),
                (SELECT id FROM users LIMIT 1)  -- Fallback
            ) as created_by,
            ar.created_at
        FROM analysis_results ar
        ON CONFLICT (id) DO NOTHING;
        
        RAISE NOTICE 'Migrated data from analysis_results to change_summaries';
    ELSE
        RAISE NOTICE 'analysis_results table does not exist, skipping migration';
    END IF;
END $$;

COMMIT;

-- Verify migration
DO $$
DECLARE
    jobs_count INTEGER;
    diff_results_count INTEGER;
    summaries_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO jobs_count FROM jobs;
    SELECT COUNT(*) INTO diff_results_count FROM diff_results;
    SELECT COUNT(*) INTO summaries_count FROM change_summaries;
    
    RAISE NOTICE 'Migration 003 complete: Data migration finished';
    RAISE NOTICE 'Jobs: %', jobs_count;
    RAISE NOTICE 'Diff Results: %', diff_results_count;
    RAISE NOTICE 'Change Summaries: %', summaries_count;
END $$;


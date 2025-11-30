-- Check if session_id column exists, if not add it
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'analysis_results'
        AND column_name = 'session_id'
    ) THEN
        -- Add the session_id column
        ALTER TABLE analysis_results ADD COLUMN session_id VARCHAR(36);

        -- Add foreign key constraint
        ALTER TABLE analysis_results ADD CONSTRAINT fk_analysis_results_session_id
        FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE;

        -- Update existing records to get session_id from comparisons table
        UPDATE analysis_results
        SET session_id = c.session_id
        FROM comparisons c
        WHERE analysis_results.comparison_id = c.id;

        -- Make the column NOT NULL after populating data
        ALTER TABLE analysis_results ALTER COLUMN session_id SET NOT NULL;

        RAISE NOTICE 'session_id column added successfully to analysis_results table';
    ELSE
        RAISE NOTICE 'session_id column already exists in analysis_results table';
    END IF;
END $$;
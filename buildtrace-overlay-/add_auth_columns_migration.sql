-- Migration: Add authentication columns to users table and create project_users table
-- Run this against the BuildTrace database

-- Add authentication columns to users table
ALTER TABLE users
ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255),
ADD COLUMN IF NOT EXISTS last_login TIMESTAMP,
ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE;

-- Create project_users junction table if it doesn't exist
CREATE TABLE IF NOT EXISTS project_users (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    project_id VARCHAR(36) NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) DEFAULT 'member',
    invited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    joined_at TIMESTAMP,
    invited_by VARCHAR(36) REFERENCES users(id),
    CONSTRAINT unique_project_user UNIQUE (project_id, user_id)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_project_users_project_id ON project_users(project_id);
CREATE INDEX IF NOT EXISTS idx_project_users_user_id ON project_users(user_id);
CREATE INDEX IF NOT EXISTS idx_project_users_role ON project_users(role);

-- Migrate existing data: add all existing users as owners of all their projects
INSERT INTO project_users (project_id, user_id, role, joined_at, invited_by)
SELECT p.id, p.user_id, 'owner', p.created_at, p.user_id
FROM projects p
WHERE p.user_id IS NOT NULL
ON CONFLICT (project_id, user_id) DO NOTHING;

-- Add session user_id and project_id columns if they don't exist
ALTER TABLE sessions
ADD COLUMN IF NOT EXISTS user_id VARCHAR(36) REFERENCES users(id),
ADD COLUMN IF NOT EXISTS project_id VARCHAR(36) REFERENCES projects(id);

-- Create indexes for sessions
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_project_id ON sessions(project_id);

-- Update existing sessions to have user_id and project_id based on legacy data
-- This assumes we can derive project from existing sessions somehow
-- For now, we'll set them to NULL and they can be set during normal operation
UPDATE sessions
SET user_id = NULL, project_id = NULL
WHERE user_id IS NULL AND project_id IS NULL;

COMMIT;
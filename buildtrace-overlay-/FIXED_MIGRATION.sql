-- Fixed Migration: Add authentication columns and tables with proper UUID handling
-- Run this against the BuildTrace database

-- First, ensure uuid-ossp extension is enabled for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Add authentication columns to users table
ALTER TABLE users
ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255),
ADD COLUMN IF NOT EXISTS last_login TIMESTAMP,
ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE;

-- Create project_users junction table with proper UUID default
CREATE TABLE IF NOT EXISTS project_users (
    id VARCHAR(36) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
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

-- Migrate existing data: add all existing users as owners of their projects
-- Use explicit UUID generation for the id column
INSERT INTO project_users (id, project_id, user_id, role, joined_at, invited_by)
SELECT
    uuid_generate_v4()::text,
    p.id,
    p.user_id,
    'owner',
    p.created_at,
    p.user_id
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
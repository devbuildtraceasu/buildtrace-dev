-- BuildTrace Database Schema Creation Script
-- Run this in your Cloud SQL database to create all required tables

-- Create Users table
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    name VARCHAR(255),
    company VARCHAR(255),
    role VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    last_login TIMESTAMP,
    email_verified BOOLEAN DEFAULT false
);

-- Create Projects table
CREATE TABLE IF NOT EXISTS projects (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id VARCHAR(36) REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    project_number VARCHAR(100),
    client_name VARCHAR(255),
    location VARCHAR(255),
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_default BOOLEAN DEFAULT false
);

-- Create Project Users junction table (if it doesn't exist yet)
CREATE TABLE IF NOT EXISTS project_users (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    project_id VARCHAR(36) REFERENCES projects(id) ON DELETE CASCADE NOT NULL,
    user_id VARCHAR(36) REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    role VARCHAR(50) DEFAULT 'member',
    invited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    joined_at TIMESTAMP,
    invited_by VARCHAR(36) REFERENCES users(id),
    user_name VARCHAR(255),
    email_add VARCHAR(255),
    company_name VARCHAR(255),
    UNIQUE(project_id, user_id)
);

-- Create Sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id VARCHAR(36) REFERENCES users(id),
    project_id VARCHAR(36) REFERENCES projects(id),
    session_type VARCHAR(50) DEFAULT 'comparison',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'active',
    total_time FLOAT,
    session_metadata JSONB
);

-- Create Drawings table
CREATE TABLE IF NOT EXISTS drawings (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    session_id VARCHAR(36) REFERENCES sessions(id) ON DELETE CASCADE NOT NULL,
    drawing_type VARCHAR(20) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    storage_path TEXT,
    drawing_name VARCHAR(100),
    page_number INTEGER,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    drawing_metadata JSONB,
    UNIQUE(session_id, drawing_name, drawing_type)
);

-- Create Drawing Versions table
CREATE TABLE IF NOT EXISTS drawing_versions (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    project_id VARCHAR(36) REFERENCES projects(id) ON DELETE CASCADE NOT NULL,
    drawing_name VARCHAR(100) NOT NULL,
    version_number INTEGER NOT NULL,
    version_label VARCHAR(50),
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    drawing_id VARCHAR(36) REFERENCES drawings(id) NOT NULL,
    comments TEXT,
    UNIQUE(project_id, drawing_name, version_number)
);

-- Create Comparisons table
CREATE TABLE IF NOT EXISTS comparisons (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    session_id VARCHAR(36) REFERENCES sessions(id) ON DELETE CASCADE NOT NULL,
    old_drawing_id VARCHAR(36) REFERENCES drawings(id) NOT NULL,
    new_drawing_id VARCHAR(36) REFERENCES drawings(id) NOT NULL,
    drawing_name VARCHAR(100) NOT NULL,
    overlay_path TEXT,
    old_image_path TEXT,
    new_image_path TEXT,
    alignment_score FLOAT,
    changes_detected BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(session_id, drawing_name)
);

-- Create Analysis Results table
CREATE TABLE IF NOT EXISTS analysis_results (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    comparison_id VARCHAR(36) REFERENCES comparisons(id) ON DELETE CASCADE NOT NULL,
    session_id VARCHAR(36) REFERENCES sessions(id) ON DELETE CASCADE NOT NULL,
    drawing_name VARCHAR(100) NOT NULL,
    changes_found JSONB,
    critical_change TEXT,
    analysis_summary TEXT,
    recommendations JSONB,
    success BOOLEAN DEFAULT true,
    error_message TEXT,
    ai_model_used VARCHAR(50) DEFAULT 'gpt-4-vision-preview',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(session_id, drawing_name)
);

-- Create Chat Conversations table
CREATE TABLE IF NOT EXISTS chat_conversations (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    session_id VARCHAR(36) REFERENCES sessions(id) ON DELETE CASCADE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create Chat Messages table
CREATE TABLE IF NOT EXISTS chat_messages (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    conversation_id VARCHAR(36) REFERENCES chat_conversations(id) ON DELETE CASCADE NOT NULL,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    message_metadata JSONB
);

-- Create Processing Jobs table
CREATE TABLE IF NOT EXISTS processing_jobs (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    session_id VARCHAR(36) REFERENCES sessions(id) ON DELETE CASCADE NOT NULL,
    job_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    job_metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create Chunked Uploads table
CREATE TABLE IF NOT EXISTS chunked_uploads (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    session_id VARCHAR(36) REFERENCES sessions(id) ON DELETE CASCADE NOT NULL,
    file_type VARCHAR(10) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    file_size INTEGER NOT NULL,
    chunk_size INTEGER DEFAULT 26214400,
    total_chunks INTEGER NOT NULL,
    chunks_uploaded INTEGER DEFAULT 0,
    storage_path TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    UNIQUE(session_id, file_type)
);

-- Create Chunked Upload Chunks table
CREATE TABLE IF NOT EXISTS chunked_upload_chunks (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    upload_id VARCHAR(36) REFERENCES chunked_uploads(id) ON DELETE CASCADE NOT NULL,
    chunk_index INTEGER NOT NULL,
    chunk_size INTEGER NOT NULL,
    storage_path TEXT NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    checksum VARCHAR(64),
    UNIQUE(upload_id, chunk_index)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_user_project ON projects(user_id, name);
CREATE INDEX IF NOT EXISTS idx_project_status ON projects(status);
CREATE INDEX IF NOT EXISTS idx_project_drawing_version ON drawing_versions(project_id, drawing_name, version_number);
CREATE INDEX IF NOT EXISTS idx_session_drawing ON drawings(session_id, drawing_name);
CREATE INDEX IF NOT EXISTS idx_session_upload ON chunked_uploads(session_id, file_type);
CREATE INDEX IF NOT EXISTS idx_upload_chunk ON chunked_upload_chunks(upload_id, chunk_index);

-- Add triggers for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers to tables with updated_at columns
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_projects_updated_at ON projects;
CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_sessions_updated_at ON sessions;
CREATE TRIGGER update_sessions_updated_at BEFORE UPDATE ON sessions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_chat_conversations_updated_at ON chat_conversations;
CREATE TRIGGER update_chat_conversations_updated_at BEFORE UPDATE ON chat_conversations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Show created tables
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;
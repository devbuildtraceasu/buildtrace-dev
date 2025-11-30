# Database Migration Instructions

You have several options to run the authentication migration:

## Option 1: Using Google Cloud Console SQL (EASIEST)

1. Go to [Google Cloud Console SQL](https://console.cloud.google.com/sql/instances)
2. Click on your `buildtrace-postgres` instance
3. Go to the "Query" tab
4. Copy and paste the following SQL:

```sql
-- Add authentication columns to users table
ALTER TABLE users
ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255),
ADD COLUMN IF NOT EXISTS last_login TIMESTAMP,
ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE;

-- Create project_users junction table
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

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_project_users_project_id ON project_users(project_id);
CREATE INDEX IF NOT EXISTS idx_project_users_user_id ON project_users(user_id);
CREATE INDEX IF NOT EXISTS idx_project_users_role ON project_users(role);

-- Migrate existing data
INSERT INTO project_users (project_id, user_id, role, joined_at, invited_by)
SELECT p.id, p.user_id, 'owner', p.created_at, p.user_id
FROM projects p
WHERE p.user_id IS NOT NULL
ON CONFLICT (project_id, user_id) DO NOTHING;

-- Add session columns
ALTER TABLE sessions
ADD COLUMN IF NOT EXISTS user_id VARCHAR(36) REFERENCES users(id),
ADD COLUMN IF NOT EXISTS project_id VARCHAR(36) REFERENCES projects(id);

-- Create session indexes
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_project_id ON sessions(project_id);
```

5. Click "Run" to execute the migration

## Option 2: Using Python Script (if you have the password)

```bash
export DB_PASS='your-database-password'
python run_auth_migration_local.py
```

## Option 3: Deploy first, then use migration endpoint

```bash
# Deploy latest code with database environment variables
./deploy-with-db.sh

# Then run migration via endpoint
curl -X POST https://buildtrace-overlay-lioa4ql2nq-uc.a.run.app/admin/migrate-auth
```

## After Migration

1. **Deploy latest code** (if not done already):
   ```bash
   ./deploy-with-db.sh
   ```

2. **Visit your service URL** and sign up for an account

3. **Create a project** - you should now see the project creation form

4. **Test "New Comparison"** - you should see project selection instead of "Development Mode" message

## Verification

After migration, you can verify it worked by checking:
- Tables exist: `project_users`, and `users` has new columns
- You can sign up and create projects
- Upload page shows project selection
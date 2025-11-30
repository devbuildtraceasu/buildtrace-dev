# Database Migration Scripts

This directory contains SQL migration scripts to update the database schema from the current session-based system to the new job-based scalable architecture.

## Migration Overview

The migration transforms the database from:
- **Current**: Session-based processing with `sessions`, `comparisons`, `analysis_results`
- **Target**: Job-based processing with `jobs`, `job_stages`, `diff_results`, `manual_overlays`, `change_summaries`

## Migration Scripts

### `001_create_job_tables.sql`
Creates new tables for job-based processing:
- `jobs` - Main job tracking
- `job_stages` - Individual stage tracking (OCR, diff, summary)
- `diff_results` - Diff calculation results
- `manual_overlays` - Human-corrected overlays
- `change_summaries` - AI-generated summaries with versioning
- `audit_logs` - Audit trail
- `organizations` - Multi-tenant support (optional)

### `002_enhance_drawing_versions.sql`
Adds new columns to `drawing_versions` table:
- `ocr_status` - OCR processing status
- `ocr_result_ref` - GCS path to OCR JSON
- `ocr_completed_at` - OCR completion timestamp
- `rasterized_image_ref` - GCS path to rasterized image
- `file_hash` - SHA-256 for deduplication
- `file_size` - File size in bytes

### `003_migrate_existing_data.sql`
Migrates existing data from old schema to new schema:
- `processing_jobs` → `jobs`
- `comparisons` → `diff_results`
- `analysis_results` → `change_summaries`

### `004_create_indexes.sql`
Creates performance indexes on new tables.

### `005_add_foreign_keys.sql`
Adds foreign key constraints for data integrity.

## Migration Strategy

### Phase 1: Add New Tables (Non-Breaking)
Run scripts 001, 002, 004, 005. This adds new tables and columns without breaking existing functionality.

### Phase 2: Migrate Data
Run script 003 to migrate existing data to new tables.

### Phase 3: Update Application Code
Update application to use new tables while keeping old tables for backward compatibility.

### Phase 4: Deprecate Old Tables (After Validation)
After validating new system works correctly, deprecate old tables.

## Usage

### Run All Migrations

```bash
# Connect to database
gcloud sql connect buildtrace-dev-db --user=buildtrace_user --database=buildtrace_db

# Or using Cloud SQL Proxy
psql "host=127.0.0.1 port=5432 dbname=buildtrace_db user=buildtrace_user" < scripts/migrations/001_create_job_tables.sql
```

### Run Individual Migration

```bash
# Run specific migration
psql "host=127.0.0.1 port=5432 dbname=buildtrace_db user=buildtrace_user" < scripts/migrations/001_create_job_tables.sql
```

### Using Python Migration Script

```bash
# Run migration via Python (handles errors better)
python scripts/migrations/run_migration.py
```

## Rollback

If migration fails, you can rollback:

```bash
# Rollback script (to be created if needed)
psql "host=127.0.0.1 port=5432 dbname=buildtrace_db user=buildtrace_user" < scripts/migrations/rollback.sql
```

## Safety Checks

Before running migrations:
1. ✅ Backup database
2. ✅ Test on development/staging first
3. ✅ Verify all scripts are correct
4. ✅ Run during maintenance window
5. ✅ Have rollback plan ready

## Notes

- Migrations are designed to be idempotent where possible
- Use `IF NOT EXISTS` for tables and `IF EXISTS` for drops
- Test each migration script individually
- Keep old tables during transition period for safety


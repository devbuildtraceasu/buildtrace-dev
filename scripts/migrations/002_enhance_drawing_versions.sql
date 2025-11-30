-- Migration 002: Enhance drawing_versions table
-- Adds new columns for OCR status tracking and file metadata
-- This is non-breaking (only adds columns)

BEGIN;

-- Add OCR status tracking columns
ALTER TABLE drawing_versions 
ADD COLUMN IF NOT EXISTS ocr_status VARCHAR(50) DEFAULT 'pending';

ALTER TABLE drawing_versions 
ADD COLUMN IF NOT EXISTS ocr_result_ref TEXT;

ALTER TABLE drawing_versions 
ADD COLUMN IF NOT EXISTS ocr_completed_at TIMESTAMP;

-- Add file metadata columns
ALTER TABLE drawing_versions 
ADD COLUMN IF NOT EXISTS rasterized_image_ref TEXT;

ALTER TABLE drawing_versions 
ADD COLUMN IF NOT EXISTS file_hash VARCHAR(64);

ALTER TABLE drawing_versions 
ADD COLUMN IF NOT EXISTS file_size BIGINT;

-- Create indexes on new columns
CREATE INDEX IF NOT EXISTS idx_drawing_versions_ocr_status ON drawing_versions(ocr_status);
CREATE INDEX IF NOT EXISTS idx_drawing_versions_file_hash ON drawing_versions(file_hash);

-- Add comment to columns
COMMENT ON COLUMN drawing_versions.ocr_status IS 'OCR processing status: pending, in_progress, completed, failed';
COMMENT ON COLUMN drawing_versions.ocr_result_ref IS 'GCS path to OCR JSON result';
COMMENT ON COLUMN drawing_versions.rasterized_image_ref IS 'GCS path to rasterized PNG image';
COMMENT ON COLUMN drawing_versions.file_hash IS 'SHA-256 hash for file deduplication';
COMMENT ON COLUMN drawing_versions.file_size IS 'File size in bytes';

COMMIT;

-- Verify columns were added
DO $$
BEGIN
    RAISE NOTICE 'Migration 002 complete: drawing_versions table enhanced';
    RAISE NOTICE 'Added columns: ocr_status, ocr_result_ref, ocr_completed_at, rasterized_image_ref, file_hash, file_size';
END $$;


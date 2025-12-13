// API Response Types
export interface ApiResponse<T = any> {
  success?: boolean
  data?: T
  error?: string
  message?: string
}

export interface ApiError {
  message: string
  code?: string
  details?: any
}

// Job Types (new async architecture)
export interface Job {
  job_id: string
  project_id: string
  status: 'created' | 'in_progress' | 'completed' | 'failed' | 'cancelled'
  old_drawing_version_id: string
  new_drawing_version_id: string
  created_at: string
  started_at?: string
  completed_at?: string
  error_message?: string
}

export interface JobSummaryRow {
  job_id: string
  project_id: string
  status: string
  created_at?: string
  completed_at?: string
  baseline_name?: string
  revised_name?: string
  change_count?: number
}

export interface DiffResultEntry {
  diff_result_id: string
  changes_detected: boolean
  change_count: number
  alignment_score: number
  overlay_ref?: string
  created_at?: string
  page_number?: number
  drawing_name?: string
  total_pages?: number
  diff_metadata?: {
    baseline_image_ref?: string
    revised_image_ref?: string
    overlay_image_ref?: string
    [key: string]: any
  }
  summary?: {
    summary_id: string
    summary_text: string
    summary_json?: any  // Structured JSON from AI analysis
    source?: string
    created_at?: string
  }
  change_types?: {
    added: number
    modified: number
    removed: number
  }
  categories?: Record<string, number>
}

export interface JobResults {
  job_id: string
  status: string
  completed_at?: string
  created_at?: string
  message?: string
  diffs?: DiffResultEntry[]
  diff?: DiffResultEntry
  baseline_file_name?: string
  revised_file_name?: string
  kpis?: {
    added: number
    modified: number
    removed: number
  }
  categories?: Record<string, number>
  // Project info for display
  project_name?: string
  project_location?: string
  project_id?: string
}

export interface JobStage {
  stage_id: string
  stage: 'ocr' | 'diff' | 'summary'
  drawing_version_id?: string
  status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'skipped'
  started_at?: string
  completed_at?: string
  error_message?: string
  result_ref?: string
  retry_count: number
}

export interface DrawingVersion {
  drawing_version_id: string
  drawing_name: string
  version_number: number
  version_label?: string
  project_id: string
  upload_date: string
  ocr_status: string
  file_size?: number
}

// Processing Types
export interface ProcessingStep {
  id: string
  name: string
  status: 'pending' | 'active' | 'completed' | 'failed'
  message?: string
  progress?: number
}

export interface Project {
  project_id: string
  name: string
  description?: string
  project_number?: string
  client_name?: string
  location?: string
  status?: string
  user_id?: string
  owner_id?: string
  organization_id?: string
  created_at?: string
  updated_at?: string
  document_count?: number
  drawing_count?: number
  comparison_count?: number
}

export interface OverlayRecord {
  overlay_id: string
  diff_result_id: string
  overlay_ref: string
  created_by: string
  is_active: boolean
  created_at?: string
  updated_at?: string
  metadata?: any
}

export interface SummaryRecord {
  summary_id: string
  diff_result_id: string
  summary_text: string
  source: string
  ai_model_used?: string
  created_by?: string
  is_active: boolean
  created_at?: string
  updated_at?: string
  metadata?: any
  overlay_id?: string
}

// File Upload Types
export interface FileUploadState {
  oldFile: File | null
  newFile: File | null
  uploadProgress: number
  isUploading: boolean
}

// Document type (uploaded PDF files)
export interface Document {
  document_id: string
  name: string
  project_id: string
  file_type: string
  file_size: number
  uploaded_at: string
  page_count: number
  status: 'pending' | 'processing' | 'ready' | 'error'
  version: 'baseline' | 'revised'
}

// Drawing type (individual pages extracted from documents)
export interface Drawing {
  drawing_id: string
  document_id: string
  project_id: string
  name: string
  page_number: number
  source_document: string
  version: 'baseline' | 'revised'
  auto_detected: boolean
  created_at: string
  thumbnail_url?: string
  ocr_status?: string
}

// Comparison type (comparison job between two drawings)
export interface Comparison {
  comparison_id: string
  project_id: string
  baseline_drawing_id: string
  revised_drawing_id: string
  baseline_drawing_name?: string
  revised_drawing_name?: string
  job_id: string
  status: 'pending' | 'processing' | 'in_progress' | 'completed' | 'failed'
  created_at: string
  completed_at?: string
  change_count: number
}

// =========================================================================
// STREAMING PIPELINE TYPES
// =========================================================================

/**
 * Per-page progress tracking for streaming pipeline.
 * Shows status of each stage (OCR, Diff, Summary) independently.
 */
export interface PageProgress {
  page_number: number
  drawing_name?: string
  
  // OCR Stage
  ocr_status: 'pending' | 'in_progress' | 'completed' | 'failed'
  ocr_result?: {
    drawing_name?: string
    revision?: string
    architect?: string
    extracted_text?: string
  }
  
  // Diff Stage
  diff_status: 'pending' | 'in_progress' | 'completed' | 'failed'
  diff_result?: {
    diff_result_id: string
    overlay_url: string
    changes_detected: boolean
    change_count: number
    alignment_score?: number
  }
  
  // Summary Stage
  summary_status: 'pending' | 'in_progress' | 'completed' | 'failed'
  summary?: {
    summary_id: string
    summary_text: string
    source?: string
  }
}

/**
 * Overall job progress for streaming pipeline.
 * Provides page-level granularity for real-time UI updates.
 */
export interface JobProgress {
  job_id: string
  status: 'created' | 'in_progress' | 'completed' | 'failed'
  total_pages: number
  progress: {
    ocr: { completed: number; total: number }
    diff: { completed: number; total: number }
    summary: { completed: number; total: number }
  }
  pages: PageProgress[]
  created_at?: string
  started_at?: string
  completed_at?: string
}

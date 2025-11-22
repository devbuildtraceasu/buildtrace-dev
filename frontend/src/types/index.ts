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
  status: string
  user_id: string
  organization_id?: string
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

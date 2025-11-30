// User and Authentication Types
export interface User {
  id: string
  email: string
  name?: string
  avatar?: string
  email_verified: boolean
  last_login?: string
}

export interface AuthState {
  isAuthenticated: boolean
  user: User | null
  isLoading: boolean
}

// Session and Processing Types
export interface ProcessingSession {
  id: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  created_at: string
  updated_at: string
  baseline_filename?: string
  revised_filename?: string
  processing_progress?: number
  error_message?: string
  user_id?: string
  project_id?: string
}

export interface ProcessingStep {
  id: string
  name: string
  status: 'pending' | 'active' | 'completed' | 'failed'
  message?: string
  progress?: number
}

// Drawing and Comparison Types
export interface DrawingComparison {
  drawing_name: string
  overlay_url?: string
  old_image_url?: string
  new_image_url?: string
  has_changes: boolean
  change_count?: number
  processing_status: 'pending' | 'completed' | 'failed'
  error_message?: string
}

export interface ChangeDetail {
  id: string
  drawing_number: string
  change_type: string
  description: string
  severity: 'low' | 'medium' | 'high'
  impact_area: string
  confidence_score: number
  coordinates?: {
    x: number
    y: number
    width: number
    height: number
  }
  ai_analysis?: string
  recommendations?: string[]
  cost_impact?: {
    estimated_cost: number
    cost_category: string
    confidence: number
  }
  schedule_impact?: {
    estimated_days: number
    critical_path_affected: boolean
  }
}

// API Response Types
export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  error?: string
  message?: string
}

export interface UploadResponse {
  session_id: string
  message: string
}

export interface DrawingImagesResponse {
  drawings: DrawingComparison[]
  summary: {
    total_drawings: number
    drawings_with_changes: number
    total_changes: number
  }
}

export interface ChangeDetailsResponse {
  changes: ChangeDetail[]
  summary: {
    total_changes: number
    high_severity: number
    medium_severity: number
    low_severity: number
  }
}

// Chat Types
export interface ChatMessage {
  id: string
  content: string
  role: 'user' | 'assistant'
  timestamp: string
  session_id: string
}

export interface ChatHistory {
  messages: ChatMessage[]
}

// File Upload Types
export interface FileUploadState {
  oldFile: File | null
  newFile: File | null
  uploadProgress: number
  isUploading: boolean
}

// UI State Types
export interface ViewMode {
  type: 'overlay' | 'side-by-side'
}

export interface ZoomState {
  level: number
  offsetX: number
  offsetY: number
}

// Error Types
export interface ApiError {
  message: string
  code?: string
  details?: any
}

// Form Types
export interface LoginForm {
  email: string
  password: string
}

export interface SignupForm {
  email: string
  password: string
  confirmPassword: string
  name?: string
}

// Project Types (for future use)
export interface Project {
  id: string
  name: string
  description?: string
  created_at: string
  updated_at: string
  user_id: string
}

// Component Props Types
export interface BaseComponentProps {
  className?: string
  children?: React.ReactNode
}

export interface ButtonProps extends BaseComponentProps {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost'
  size?: 'sm' | 'md' | 'lg'
  disabled?: boolean
  loading?: boolean
  onClick?: () => void
  type?: 'button' | 'submit' | 'reset'
}

export interface InputProps extends BaseComponentProps {
  type?: 'text' | 'email' | 'password' | 'file'
  placeholder?: string
  value?: string
  onChange?: (value: string) => void
  error?: string
  disabled?: boolean
  required?: boolean
}
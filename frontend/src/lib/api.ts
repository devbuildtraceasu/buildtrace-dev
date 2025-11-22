import axios, { AxiosInstance, AxiosResponse, AxiosError, InternalAxiosRequestConfig } from 'axios'
import { ApiResponse, ApiError, Job, JobStage, DrawingVersion } from '@/types'
import { useAuthStore } from '@/store/authStore'

export interface User {
  user_id: string
  email: string
  name: string
  company?: string
  role?: string
  organization_id?: string
  email_verified: boolean
  is_active: boolean
}

class ApiClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001',
      timeout: 60000,
      withCredentials: true,  // Required for session cookies to be sent (fallback)
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // Request interceptor - add JWT token to Authorization header
    this.client.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        // Get token from auth store
        const token = useAuthStore.getState().token
        if (token && config.headers) {
          config.headers.Authorization = `Bearer ${token}`
        }
        return config
      },
      (error) => {
        return Promise.reject(error)
      }
    )

    // Response interceptor
    this.client.interceptors.response.use(
      (response: AxiosResponse) => {
        return response.data
      },
      (error: AxiosError) => {
        const apiError: ApiError = {
          message: 'An unexpected error occurred',
          code: error.code,
          details: error.response?.data
        }

        if (error.response?.data) {
          const data = error.response.data as any
          apiError.message = data.error || data.message || apiError.message
        } else if (error.request) {
          apiError.message = 'Network error - please check your connection'
        } else {
          apiError.message = error.message
        }

        // If 401, clear auth state (token expired or invalid)
        if (error.response?.status === 401) {
          useAuthStore.getState().clearUser()
        }

        return Promise.reject(apiError)
      }
    )
  }

  // Generic GET request
  async get<T = any>(endpoint: string): Promise<T> {
    return this.client.get(endpoint)
  }

  // Generic POST request
  async post<T = any>(endpoint: string, data?: any): Promise<T> {
    return this.client.post(endpoint, data)
  }

  async put<T = any>(endpoint: string, data?: any): Promise<T> {
    return this.client.put(endpoint, data)
  }

  async delete<T = any>(endpoint: string): Promise<T> {
    return this.client.delete(endpoint)
  }

  // File upload with progress tracking
  async uploadFiles(
    endpoint: string,
    formData: FormData,
    onProgress?: (progress: number) => void
  ): Promise<ApiResponse> {
    return this.client.post(endpoint, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total && onProgress) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          onProgress(progress)
        }
      },
    })
  }

  // Auth methods
  async googleLogin(): Promise<ApiResponse<{ auth_url: string; state: string }>> {
    return this.get('/api/v1/auth/google/login')
  }

  async getCurrentUser(): Promise<ApiResponse<User>> {
    return this.get('/api/v1/auth/me')
  }

  async logout(): Promise<ApiResponse> {
    return this.post('/api/v1/auth/logout')
  }

  // Drawing upload
  async uploadDrawing(
    file: File,
    projectId: string,
    oldVersionId?: string,
    userId?: string,
    onProgress?: (progress: number) => void
  ): Promise<ApiResponse<{ drawing_version_id: string; job_id?: string }>> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('project_id', projectId)
    if (oldVersionId) {
      formData.append('old_version_id', oldVersionId)
    }
    if (userId) {
      formData.append('user_id', userId)
    }

    return this.uploadFiles('/api/v1/drawings/upload', formData, onProgress)
  }

  // Job management
  async getJob(jobId: string): Promise<Job> {
    return this.get(`/api/v1/jobs/${jobId}`)
  }

  async getJobStages(jobId: string): Promise<{ job_id: string; stages: JobStage[] }> {
    return this.get(`/api/v1/jobs/${jobId}/stages`)
  }

  async getJobResults(jobId: string): Promise<ApiResponse<{
    job_id: string
    status: string
    completed_at?: string
    diff?: {
      diff_result_id: string
      changes_detected: boolean
      change_count: number
      alignment_score: number
      overlay_ref: string
      created_at: string
    }
    summary?: {
      summary_id: string
      summary_text: string
      source: string
      created_at: string
    }
  }>> {
    return this.get(`/api/v1/jobs/${jobId}/results`)
  }

  async createJob(
    oldVersionId: string,
    newVersionId: string,
    projectId: string,
    userId?: string
  ): Promise<ApiResponse<{ job_id: string }>> {
    return this.post('/api/v1/jobs', {
      old_drawing_version_id: oldVersionId,
      new_drawing_version_id: newVersionId,
      project_id: projectId,
      user_id: userId || 'ash-system-0000000000001'
    })
  }

  // Drawing management
  async getDrawing(drawingVersionId: string): Promise<DrawingVersion> {
    return this.get(`/api/v1/drawings/${drawingVersionId}`)
  }

  async listVersions(drawingVersionId: string): Promise<{ drawing_name: string; versions: DrawingVersion[] }> {
    return this.get(`/api/v1/drawings/${drawingVersionId}/versions`)
  }

  // Projects
  async listProjects(userId?: string): Promise<ApiResponse<{ projects: any[] }>> {
    const suffix = userId ? `?user_id=${encodeURIComponent(userId)}` : ''
    return this.get(`/api/v1/projects${suffix}`)
  }

  async createProject(data: { name: string; user_id: string; organization_id?: string; description?: string }): Promise<ApiResponse<{ project: any }>> {
    return this.post('/api/v1/projects', data)
  }

  // Overlays
  async getOverlay(diffId: string): Promise<ApiResponse<any>> {
    return this.get(`/api/v1/overlays/${diffId}`)
  }

  async createManualOverlay(diffId: string, payload: { overlay_data: any; user_id?: string; metadata?: any; auto_regenerate?: boolean }): Promise<ApiResponse<any>> {
    return this.post(`/api/v1/overlays/${diffId}/manual`, payload)
  }

  async updateManualOverlay(diffId: string, overlayId: string, payload: { overlay_data?: any; is_active?: boolean; metadata?: any }): Promise<ApiResponse<any>> {
    return this.put(`/api/v1/overlays/${diffId}/manual/${overlayId}`, payload)
  }

  async deleteManualOverlay(diffId: string, overlayId: string): Promise<ApiResponse<any>> {
    return this.delete(`/api/v1/overlays/${diffId}/manual/${overlayId}`)
  }

  // Summaries
  async getSummaries(diffId: string): Promise<ApiResponse<any>> {
    return this.get(`/api/v1/summaries/${diffId}`)
  }

  async regenerateSummary(diffId: string, overlayId?: string): Promise<ApiResponse<any>> {
    return this.post(`/api/v1/summaries/${diffId}/regenerate`, overlayId ? { overlay_id: overlayId } : {})
  }

  async updateSummary(summaryId: string, summaryText: string, metadata?: any): Promise<ApiResponse<any>> {
    return this.put(`/api/v1/summaries/${summaryId}`, {
      summary_text: summaryText,
      metadata,
    })
  }
}

// Export singleton instance
export const apiClient = new ApiClient()

// Export class for testing
export { ApiClient }

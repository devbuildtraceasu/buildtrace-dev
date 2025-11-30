import axios, { AxiosInstance, AxiosResponse, AxiosError, InternalAxiosRequestConfig } from 'axios'
import { ApiResponse, ApiError, Job, JobStage, DrawingVersion, DiffResultEntry, JobSummaryRow } from '@/types'
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
        // Get token from auth store (also check localStorage as fallback)
        let token = useAuthStore.getState().token
        if (!token && typeof window !== 'undefined') {
          // Fallback to localStorage if store doesn't have it yet
          token = localStorage.getItem('buildtrace-token')
        }
        if (token && config.headers) {
          config.headers.Authorization = `Bearer ${token}`
          console.log('API request with token:', config.url, token.substring(0, 20) + '...')
        } else {
          console.warn('API request without token:', config.url)
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

  async getJobResults(jobId: string): Promise<{
    job_id: string
    status: string
    completed_at?: string
    message?: string
    diff?: DiffResultEntry
    diffs?: DiffResultEntry[]
    summary?: DiffResultEntry['summary']
  }> {
    return this.get(`/api/v1/jobs/${jobId}/results`)
  }

  async getOcrLog(jobId: string): Promise<ApiResponse<{
    job_id: string
    ocr_logs: Array<{
      drawing_version_id: string
      drawing_name: string
      log: {
        summary?: any
        pages?: Array<{
          page_number: number
          drawing_name: string
          extracted_info?: any
          processed_at: string
        }>
        started_at?: string
        completed_at?: string
      }
    }>
  }>> {
    return this.get(`/api/v1/jobs/${jobId}/ocr-log`)
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

  async listJobs(params?: { userId?: string; status?: string; limit?: number }): Promise<{ jobs: JobSummaryRow[] }> {
    const search = new URLSearchParams()
    if (params?.userId) search.append('user_id', params.userId)
    if (params?.status) search.append('status', params.status)
    if (params?.limit) search.append('limit', params.limit.toString())
    const suffix = search.toString() ? `?${search.toString()}` : ''
    return this.get(`/api/v1/jobs${suffix}`)
  }

  async createProject(data: { name: string; user_id: string; organization_id?: string; description?: string }): Promise<ApiResponse<{ project: any }>> {
    return this.post('/api/v1/projects', data)
  }

  // Overlays
  async getOverlay(diffId: string): Promise<ApiResponse<any>> {
    return this.get(`/api/v1/overlays/${diffId}`)
  }

  async getOverlayImageUrl(diffId: string): Promise<{
    diff_result_id: string
    overlay_image_url: string
    page_number?: number
    drawing_name?: string
  }> {
    return this.get(`/api/v1/overlays/${diffId}/image-url`)
  }

  async getAllImageUrls(diffId: string): Promise<{
    diff_result_id: string
    overlay_image_url?: string
    baseline_image_url?: string
    revised_image_url?: string
    baseline_pdf_url?: string
    revised_pdf_url?: string
    page_number?: number
    drawing_name?: string
  }> {
    return this.get(`/api/v1/overlays/${diffId}/images`)
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

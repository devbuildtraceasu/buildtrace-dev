import axios, { AxiosInstance, AxiosResponse, AxiosError } from 'axios'
import { ApiResponse, ApiError } from '@/types'

class ApiClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: process.env.NEXT_PUBLIC_API_URL || 'https://buildtrace-overlay-lioa4ql2nq-uc.a.run.app',
      timeout: 60000, // Increased for Cloud Run cold starts
      headers: {
        'Content-Type': 'application/json',
      },
      withCredentials: true // Important for session-based auth
    })

    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        // Add any auth tokens or custom headers here
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

        return Promise.reject(apiError)
      }
    )
  }

  // Generic GET request
  async get<T = any>(endpoint: string): Promise<ApiResponse<T>> {
    return this.client.get(endpoint)
  }

  // Generic POST request
  async post<T = any>(endpoint: string, data?: any): Promise<ApiResponse<T>> {
    return this.client.post(endpoint, data)
  }

  // Generic PUT request
  async put<T = any>(endpoint: string, data?: any): Promise<ApiResponse<T>> {
    return this.client.put(endpoint, data)
  }

  // Generic DELETE request
  async delete<T = any>(endpoint: string): Promise<ApiResponse<T>> {
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

  // Specific API methods

  // Authentication
  async login(email: string, password: string) {
    return this.post('/auth/login', { email, password })
  }

  async logout() {
    return this.post('/auth/logout')
  }

  async signup(email: string, password: string, name?: string) {
    return this.post('/auth/signup', { email, password, name })
  }

  async checkAuth() {
    return this.get('/auth/me')
  }

  // File uploads and processing
  async submitComparison(formData: FormData, onProgress?: (progress: number) => void) {
    return this.uploadFiles('/upload', formData, onProgress)
  }

  async processSession(sessionId: string) {
    return this.post(`/process/${sessionId}`)
  }

  // Drawing and analysis data
  async getDrawingImages(sessionId: string) {
    return this.get(`/api/drawings/${sessionId}`)
  }

  async getChangeDetails(sessionId: string) {
    return this.get(`/api/changes/${sessionId}`)
  }

  async getSessionStatus(sessionId: string) {
    return this.get(`/api/sessions/${sessionId}/status`)
  }

  // Chat functionality
  async sendChatMessage(sessionId: string, message: string) {
    return this.post('/api/chat', { session_id: sessionId, message })
  }

  async getChatHistory(sessionId: string) {
    return this.get(`/api/chat/${sessionId}/history`)
  }

  // Session management
  async getRecentSessions() {
    return this.get('/api/sessions/recent')
  }

  async deleteSession(sessionId: string) {
    return this.delete(`/api/sessions/${sessionId}`)
  }

  // Project management (for future use)
  async getProjects() {
    return this.get('/api/projects')
  }

  async createProject(name: string, description?: string) {
    return this.post('/api/projects', { name, description })
  }

  async getProject(projectId: string) {
    return this.get(`/api/projects/${projectId}`)
  }

  async updateProject(projectId: string, data: any) {
    return this.put(`/api/projects/${projectId}`, data)
  }

  async deleteProject(projectId: string) {
    return this.delete(`/api/projects/${projectId}`)
  }
}

// Export singleton instance
export const apiClient = new ApiClient()

// Export class for testing
export { ApiClient }
import { useAuthStore } from '@/store/authStore'
import { ApiResponse, Job, JobResults, JobStage, JobSummaryRow, Project, Document, Drawing, Comparison } from '@/types'
import {
  mockUser,
  mockProjects,
  mockProjectsExtended,
  mockJobs,
  mockJobDetails,
  mockJobStages,
  mockJobResults,
  mockSummaries,
  mockImageMap,
  mockOcrLogs,
  mockDocuments,
  mockDrawings,
  mockComparisons
} from './data'

const delay = (ms = 350) => new Promise((resolve) => setTimeout(resolve, ms))

const deepClone = <T>(value: T): T => JSON.parse(JSON.stringify(value))

// Track job processing state
const jobProcessingState: Record<string, {
  createdAt: number
  ocrCompleted: boolean
  diffCompleted: boolean
  summaryCompleted: boolean
}> = {}

const getJobProcessingState = (jobId: string) => {
  if (!jobProcessingState[jobId]) {
    jobProcessingState[jobId] = {
      createdAt: Date.now(),
      ocrCompleted: false,
      diffCompleted: false,
      summaryCompleted: false
    }
  }
  return jobProcessingState[jobId]
}

const updateJobProcessingState = (jobId: string, elapsedSeconds: number) => {
  const state = getJobProcessingState(jobId)
  if (elapsedSeconds >= 5) state.ocrCompleted = true
  if (elapsedSeconds >= 10) state.diffCompleted = true
  if (elapsedSeconds >= 15) state.summaryCompleted = true
}

const ensureJobExists = (jobId: string) => {
  if (!mockJobResults[jobId]) {
    const template = deepClone(mockJobResults['job-mock-001'])
    template.job_id = jobId
    mockJobResults[jobId] = template
  }
  if (!mockJobStages[jobId]) {
    mockJobStages[jobId] = deepClone(mockJobStages['job-mock-001'])
  }
  if (!mockJobDetails[jobId]) {
    mockJobDetails[jobId] = deepClone(mockJobDetails['job-mock-001'])
    mockJobDetails[jobId].job_id = jobId
  }
  if (!mockJobs.find((job) => job.job_id === jobId)) {
    mockJobs.unshift({ job_id: jobId, project_id: mockProjects[0].project_id, status: 'in_progress', created_at: new Date().toISOString() })
  }
  // Ensure processing state is initialized
  getJobProcessingState(jobId)
}

const respond = async <T>(data: T): Promise<T> => {
  await delay()
  return deepClone(data)
}

export const mockApiClient = {
  async googleLogin() {
    const store = useAuthStore.getState()
    store.setUser(mockUser)
    store.setToken('mock-token')
    return respond({ auth_url: '#mock-login', message: 'Using mock login', success: true })
  },

  async logout() {
    useAuthStore.getState().clearUser()
    return respond({ success: true })
  },

  async getCurrentUser(): Promise<{ data: typeof mockUser }> {
    return respond({ data: mockUser })
  },

  async listProjects(userId?: string): Promise<{ projects: Project[] }> {
    const filtered = userId ? mockProjects.filter((p) => p.user_id === userId) : mockProjects
    return respond({ projects: filtered })
  },

  async listJobs(): Promise<{ jobs: JobSummaryRow[] }> {
    return respond({ jobs: mockJobs })
  },

  async getJob(jobId: string): Promise<Job> {
    ensureJobExists(jobId)
    const job = deepClone(mockJobDetails[jobId])
    
    // job-mock-001 is always completed for testing
    if (jobId === 'job-mock-001') {
      job.status = 'completed'
      job.completed_at = new Date().toISOString()
      return respond(job)
    }
    
    const state = getJobProcessingState(jobId)
    const elapsedSeconds = (Date.now() - state.createdAt) / 1000
    updateJobProcessingState(jobId, elapsedSeconds)
    
    // Update job status based on elapsed time
    if (state.summaryCompleted) {
      job.status = 'completed'
      job.completed_at = new Date().toISOString()
    } else if (state.diffCompleted) {
      job.status = 'in_progress'
    } else if (state.ocrCompleted) {
      job.status = 'in_progress'
    } else {
      job.status = 'in_progress'
    }
    
    return respond(job)
  },

  async getJobStages(jobId: string): Promise<{ job_id: string; stages: JobStage[] }> {
    ensureJobExists(jobId)
    const state = getJobProcessingState(jobId)
    const elapsedSeconds = (Date.now() - state.createdAt) / 1000
    updateJobProcessingState(jobId, elapsedSeconds)
    
    const baseStages = deepClone(mockJobStages['job-mock-001'])
    
    // Update stages based on elapsed time
    if (!state.ocrCompleted) {
      // OCR in progress (0-5 seconds)
      baseStages[0].status = 'in_progress'
      baseStages[1].status = 'in_progress'
      baseStages[2].status = 'pending'
      baseStages[3].status = 'pending'
      console.log(`[Mock API] Job ${jobId}: OCR in progress (${elapsedSeconds.toFixed(1)}s)`)
    } else if (!state.diffCompleted) {
      // OCR done, diff in progress (5-10 seconds)
      baseStages[0].status = 'completed'
      baseStages[1].status = 'completed'
      baseStages[2].status = 'in_progress'
      baseStages[3].status = 'pending'
      console.log(`[Mock API] Job ${jobId}: Diff in progress (${elapsedSeconds.toFixed(1)}s)`)
    } else if (!state.summaryCompleted) {
      // Diff done, summary in progress (10-15 seconds)
      baseStages[0].status = 'completed'
      baseStages[1].status = 'completed'
      baseStages[2].status = 'completed'
      baseStages[3].status = 'in_progress'
      console.log(`[Mock API] Job ${jobId}: Summary in progress (${elapsedSeconds.toFixed(1)}s)`)
    } else {
      // All completed (15+ seconds)
      baseStages[0].status = 'completed'
      baseStages[1].status = 'completed'
      baseStages[2].status = 'completed'
      baseStages[3].status = 'completed'
      console.log(`[Mock API] Job ${jobId}: All completed (${elapsedSeconds.toFixed(1)}s)`)
    }
    
    return respond({ job_id: jobId, stages: baseStages })
  },

  async getJobResults(jobId: string): Promise<JobResults> {
    ensureJobExists(jobId)
    const results = deepClone(mockJobResults['job-mock-001'])
    results.job_id = jobId
    
    // job-mock-001 is always completed for testing
    if (jobId === 'job-mock-001') {
      results.status = 'completed'
      return respond(results)
    }
    
    const state = getJobProcessingState(jobId)
    const elapsedSeconds = (Date.now() - state.createdAt) / 1000
    updateJobProcessingState(jobId, elapsedSeconds)
    
    if (!state.summaryCompleted) {
      results.status = 'in_progress'
      if (!state.diffCompleted) {
        results.message = 'Comparing drawings...'
        results.diffs = results.diffs?.slice(0, 2) // Partial results
      } else {
        results.message = 'Generating summary...'
      }
    } else {
      results.status = 'completed'
    }
    
    return respond(results)
  },

  /**
   * Get streaming pipeline progress for a job.
   * Returns per-page status for OCR, Diff, and Summary stages.
   */
  async getJobProgress(jobId: string): Promise<any> {
    ensureJobExists(jobId)
    const state = getJobProcessingState(jobId)
    const elapsedSeconds = (Date.now() - state.createdAt) / 1000
    updateJobProcessingState(jobId, elapsedSeconds)
    
    // For mock purposes, simulate 3 pages with progressive completion
    const totalPages = 3
    const pages = []
    
    for (let pageNum = 1; pageNum <= totalPages; pageNum++) {
      // Each page takes ~15 seconds total (5s OCR + 5s Diff + 5s Summary)
      const pageStartTime = (pageNum - 1) * 5 // Staggered start
      const pageElapsed = Math.max(0, elapsedSeconds - pageStartTime)
      
      const ocrComplete = pageElapsed >= 5
      const diffComplete = pageElapsed >= 10
      const summaryComplete = pageElapsed >= 15
      
      pages.push({
        page_number: pageNum,
        drawing_name: `A-10${pageNum}`,
        ocr_status: ocrComplete ? 'completed' : (pageElapsed > 0 ? 'in_progress' : 'pending'),
        diff_status: diffComplete ? 'completed' : (ocrComplete ? 'in_progress' : 'pending'),
        summary_status: summaryComplete ? 'completed' : (diffComplete ? 'in_progress' : 'pending'),
        diff_result: diffComplete ? {
          diff_result_id: `diff-${jobId}-page-${pageNum}`,
          overlay_url: `/test-images/A-101.png`,
          changes_detected: true,
          change_count: 5 + pageNum,
          alignment_score: 0.92
        } : undefined,
        summary: summaryComplete ? {
          summary_id: `summary-${jobId}-page-${pageNum}`,
          summary_text: `Page ${pageNum} summary: Found ${5 + pageNum} changes including wall modifications.`
        } : undefined
      })
    }
    
    const completedOcr = pages.filter(p => p.ocr_status === 'completed').length
    const completedDiff = pages.filter(p => p.diff_status === 'completed').length
    const completedSummary = pages.filter(p => p.summary_status === 'completed').length
    
    const status = completedSummary >= totalPages ? 'completed' : 'in_progress'
    
    return respond({
      job_id: jobId,
      status,
      total_pages: totalPages,
      progress: {
        ocr: { completed: completedOcr, total: totalPages },
        diff: { completed: completedDiff, total: totalPages },
        summary: { completed: completedSummary, total: totalPages }
      },
      pages,
      created_at: new Date(state.createdAt).toISOString(),
      started_at: new Date(state.createdAt).toISOString(),
      completed_at: status === 'completed' ? new Date().toISOString() : undefined
    })
  },

  async getSummaries(diffId: string): Promise<any> {
    const entry = mockSummaries[diffId]
    return respond({
      active_summary: entry?.active,
      summaries: entry?.list || []
    })
  },

  async getOverlay(diffId: string): Promise<any> {
    return respond({
      active_overlay: {
        overlay_id: `overlay-${diffId}`,
        diff_result_id: diffId,
        overlay_ref: `/mock-overlays/${diffId}.json`,
        is_active: true,
        created_at: new Date().toISOString()
      },
      overlays: []
    })
  },

  async createManualOverlay(diffId: string, payload: any): Promise<any> {
    return respond({
      success: true,
      overlay_id: `overlay-manual-${Date.now()}`,
      diff_result_id: diffId,
      ...payload
    })
  },

  async regenerateSummary(diffId: string, overlayId?: string): Promise<any> {
    return respond({
      success: true,
      summary_id: `summary-regen-${Date.now()}`,
      summary_text: 'Regenerated summary for the drawing changes.',
      source: 'machine'
    })
  },

  async updateSummary(summaryId: string, summaryText: string, metadata?: any): Promise<any> {
    return respond({
      success: true,
      summary_id: summaryId,
      summary_text: summaryText,
      metadata
    })
  },

  async getOverlayImageUrl(diffId: string): Promise<{ diff_result_id: string; overlay_image_url: string; page_number?: number; drawing_name?: string }> {
    const images = mockImageMap[diffId] || {}
    return respond({
      diff_result_id: diffId,
      overlay_image_url: images.overlay_image_url || images.revised_image_url || '/test-images/A-101_revised.png',
      page_number: 1,
      drawing_name: diffId.replace('diff-', '')
    })
  },

  async getAllImageUrls(diffId: string): Promise<{ diff_result_id: string; overlay_image_url?: string; baseline_image_url?: string; revised_image_url?: string }> {
    return respond({ diff_result_id: diffId, ...mockImageMap[diffId] })
  },

  async getOcrLog(jobId: string): Promise<any> {
    const state = getJobProcessingState(jobId)
    const elapsedSeconds = (Date.now() - state.createdAt) / 1000
    updateJobProcessingState(jobId, elapsedSeconds)
    
    // Only return OCR logs if OCR is completed or in progress
    if (elapsedSeconds >= 0) {
      const logs = deepClone(mockOcrLogs['job-mock-001'] || { job_id: jobId, ocr_logs: [] })
      logs.job_id = jobId
      return respond(logs)
    }
    
    return respond({ job_id: jobId, ocr_logs: [] })
  },

  async uploadDrawing(): Promise<ApiResponse<{ drawing_version_id: string; job_id?: string }>> {
    const newJobId = `job-mock-${Math.floor(Math.random() * 900 + 100)}`
    ensureJobExists(newJobId)
    // Initialize processing state
    getJobProcessingState(newJobId)
    return respond({ success: true, drawing_version_id: `dv-${newJobId}`, job_id: newJobId })
  },

  async createJob(): Promise<ApiResponse<{ job_id: string }>> {
    const newJobId = `job-mock-${Math.floor(Math.random() * 900 + 100)}`
    ensureJobExists(newJobId)
    // Initialize processing state
    const state = getJobProcessingState(newJobId)
    console.log(`[Mock API] Created job ${newJobId} at ${new Date(state.createdAt).toISOString()}`)
    return respond({ success: true, job_id: newJobId })
  },

  async getProjects(userId?: string): Promise<Project[]> {
    const filtered = userId 
      ? mockProjectsExtended.filter(p => p.user_id === userId || p.owner_id === userId)
      : mockProjectsExtended
    return respond(filtered)
  },

  async getProject(projectId: string): Promise<Project | null> {
    const project = mockProjectsExtended.find(p => p.project_id === projectId)
    return respond(project || null)
  },

  async createProject(data: { name: string; description?: string; user_id: string }): Promise<Project> {
    const newProject: Project = {
      project_id: `proj-${Math.floor(Math.random() * 900 + 100)}`,
      name: data.name,
      description: data.description || '',
      owner_id: data.user_id,
      user_id: data.user_id,
      status: 'active',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      document_count: 0,
      drawing_count: 0,
      comparison_count: 0
    }
    mockProjectsExtended.push(newProject)
    return respond(newProject)
  },

  // Alias methods for backwards compatibility
  async getDocuments(projectId: string): Promise<Document[]> {
    return this.getProjectDocuments(projectId)
  },

  async getDrawings(projectId: string): Promise<Drawing[]> {
    return this.getProjectDrawings(projectId)
  },

  async getComparisons(projectId: string): Promise<Comparison[]> {
    return this.getProjectComparisons(projectId)
  },

  async getProjectDocuments(projectId: string): Promise<Document[]> {
    const docs = mockDocuments.filter(d => d.project_id === projectId)
    return respond(docs)
  },

  async getProjectDrawings(projectId: string): Promise<Drawing[]> {
    const drawings = mockDrawings.filter(d => d.project_id === projectId)
    return respond(drawings)
  },

  async getProjectComparisons(projectId: string): Promise<Comparison[]> {
    const comparisons = mockComparisons.filter(c => c.project_id === projectId)
    return respond(comparisons)
  },

  async uploadDocument(projectId: string, file: File): Promise<Document> {
    const newDoc: Document = {
      document_id: `doc-${Math.floor(Math.random() * 900 + 100)}`,
      project_id: projectId,
      name: file.name,
      file_type: file.type,
      file_size: file.size,
      uploaded_at: new Date().toISOString(),
      page_count: Math.floor(Math.random() * 10 + 1),
      status: 'processing',
      version: 'revised'
    }
    mockDocuments.push(newDoc)
    
    // Simulate processing completion after delay
    setTimeout(() => {
      const doc = mockDocuments.find(d => d.document_id === newDoc.document_id)
      if (doc) {
        doc.status = 'ready'
        // Create drawings for each page
        for (let i = 1; i <= newDoc.page_count; i++) {
          mockDrawings.push({
            drawing_id: `draw-${Math.floor(Math.random() * 9000 + 1000)}`,
            document_id: newDoc.document_id,
            project_id: projectId,
            name: `Page-${i}`,
            page_number: i,
            source_document: file.name,
            version: 'revised',
            auto_detected: true,
            created_at: new Date().toISOString()
          })
        }
        // Update project counts
        const project = mockProjectsExtended.find(p => p.project_id === projectId)
        if (project) {
          project.document_count = (project.document_count || 0) + 1
          project.drawing_count = (project.drawing_count || 0) + newDoc.page_count
          project.updated_at = new Date().toISOString()
        }
      }
    }, 2000)
    
    return respond(newDoc)
  },

  // Document/Drawing URL methods (mock returns null - real API provides GCS signed URLs)
  async getDocumentUrl(documentId: string): Promise<{ url: string } | null> {
    await delay(100)
    // In mock mode, return null (no real GCS URLs)
    return null
  },

  async getDrawingUrl(drawingVersionId: string): Promise<{ url: string } | null> {
    await delay(100)
    // In mock mode, return null (no real GCS URLs)
    return null
  }
}

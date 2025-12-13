import { Job, JobResults, JobStage, JobSummaryRow, Project, SummaryRecord, Document, Drawing, Comparison } from '@/types'

export const mockUser = {
  user_id: 'dev-user-001',
  email: 'designer@buildtrace.ai',
  name: 'BuildTrace Designer',
  email_verified: true,
  is_active: true,
  company: 'BuildTrace',
  role: 'Product Designer'
}

export const mockProjects: Project[] = [
  {
    project_id: 'project-my-tower',
    name: 'Mirage Tower Phase 2',
    description: '20-story mixed use tower',
    project_number: 'MT-002',
    client_name: 'Mirage Construction',
    location: 'Seattle, WA',
    status: 'active',
    user_id: mockUser.user_id,
    organization_id: 'org-buildtrace'
  },
  {
    project_id: 'project-campus',
    name: 'Lakeside Innovation Campus',
    description: 'Four building campus renovation',
    project_number: 'LIC-004',
    client_name: 'Lakeside Partners',
    location: 'Austin, TX',
    status: 'active',
    user_id: mockUser.user_id
  }
]

const now = new Date().toISOString()

export const mockJobs: JobSummaryRow[] = [
  {
    job_id: 'job-mock-001',
    project_id: 'project-my-tower',
    status: 'completed',
    created_at: now,
    completed_at: now
  },
  {
    job_id: 'job-mock-002',
    project_id: 'project-my-tower',
    status: 'in_progress',
    created_at: now
  },
  {
    job_id: 'job-mock-003',
    project_id: 'project-campus',
    status: 'failed',
    created_at: now
  }
]

export const mockJobDetails: Record<string, Job> = {
  'job-mock-001': {
    job_id: 'job-mock-001',
    project_id: 'project-my-tower',
    status: 'completed',
    created_at: now,
    started_at: now,
    completed_at: now,
    old_drawing_version_id: 'dv-old-001',
    new_drawing_version_id: 'dv-new-001'
  },
  'job-mock-002': {
    job_id: 'job-mock-002',
    project_id: 'project-my-tower',
    status: 'in_progress',
    created_at: now,
    started_at: now,
    old_drawing_version_id: 'dv-old-002',
    new_drawing_version_id: 'dv-new-002'
  },
  'job-mock-003': {
    job_id: 'job-mock-003',
    project_id: 'project-campus',
    status: 'failed',
    created_at: now,
    started_at: now,
    completed_at: now,
    error_message: 'Diff worker exceeded memory limits',
    old_drawing_version_id: 'dv-old-003',
    new_drawing_version_id: 'dv-new-003'
  }
}

const baseStages: JobStage[] = [
  {
    stage_id: 'stage-ocr-old',
    stage: 'ocr',
    drawing_version_id: 'dv-old-001',
    status: 'completed',
    started_at: now,
    completed_at: now,
    retry_count: 0
  },
  {
    stage_id: 'stage-ocr-new',
    stage: 'ocr',
    drawing_version_id: 'dv-new-001',
    status: 'completed',
    started_at: now,
    completed_at: now,
    retry_count: 0
  },
  {
    stage_id: 'stage-diff',
    stage: 'diff',
    status: 'completed',
    started_at: now,
    completed_at: now,
    retry_count: 0
  },
  {
    stage_id: 'stage-summary',
    stage: 'summary',
    status: 'completed',
    started_at: now,
    completed_at: now,
    retry_count: 0
  }
]

export const mockJobStages: Record<string, JobStage[]> = {
  'job-mock-001': baseStages,
  'job-mock-002': baseStages.map((stage) => stage.stage === 'summary'
    ? { ...stage, status: 'pending', completed_at: undefined }
    : stage.stage === 'diff'
      ? { ...stage, status: 'in_progress', completed_at: undefined }
      : stage
  ),
  'job-mock-003': baseStages.map((stage) => stage.stage === 'diff'
    ? { ...stage, status: 'failed', error_message: 'Alignment error', completed_at: undefined }
    : stage.stage === 'summary'
      ? { ...stage, status: 'skipped', completed_at: undefined }
      : stage
  )
}

const diffTemplates = [
  {
    diff_result_id: 'diff-A-101',
    drawing_name: 'A-101',
    page_number: 1,
    alignment_score: 0.98,
    changes_detected: true,
    change_count: 6,
    change_types: { added: 2, modified: 3, removed: 1 },
    summary_text: `A-101: Removed future studio; updated keynotes and building area summary.

### Changes Found:
- Deleted 'Artist's Studio (future)' footprint and callout
- Added keynotes: 'Genset & Firepump Room', 'Electrical Switchboards', 'Overhead Crane'
- Updated Building Area Summary to new areas (MRF 67,390 SF; Backyard 183,945 SF)
- Modified room labels and callouts in core area
- Adjusted dimension strings for new wall locations`,
    overlay_ref: '/mock-overlays/A-101.png',
    categories: { Architectural: 3, MEP: 2, Electrical: 1 }
  },
  {
    diff_result_id: 'diff-A-111',
    drawing_name: 'A-111',
    page_number: 2,
    alignment_score: 0.95,
    changes_detected: true,
    change_count: 6,
    change_types: { added: 3, modified: 2, removed: 1 },
    summary_text: `A-111: Merged genset and pump rooms; added switchgear, cranes, transformer.

### Changes Found:
- Combined separate genset and fire pump rooms into single room
- Added electrical switchgear room with new callouts
- Added overhead crane details and structural supports
- Added transformer pad location and connections
- Modified MEP routing to accommodate new room layout
- Removed redundant mechanical equipment callouts`,
    overlay_ref: '/mock-overlays/A-111.png',
    categories: { MEP: 3, Electrical: 2, Structural: 1 }
  },
  {
    diff_result_id: 'diff-A-113',
    drawing_name: 'A-113',
    page_number: 3,
    alignment_score: 0.97,
    changes_detected: true,
    change_count: 5,
    change_types: { added: 1, modified: 2, removed: 2 },
    summary_text: `A-113: Cleared context; retained only staff restrooms and break room.

### Changes Found:
- Removed MRF, bale storage & backyard building outlines (context shading cleared)
- Deleted (E) conc. bunker and conveyor graphics outside core area
- Retained only the Staff Restrooms & Break Room footprint and callouts
- Removed gridlines and keynotes outside the break-room area
- Revision clouds around all cleared context elements`,
    overlay_ref: '/mock-overlays/A-113.png',
    categories: { Architectural: 2, Drywall: 1, 'Site Work': 2 }
  },
  {
    diff_result_id: 'diff-A-201',
    drawing_name: 'A-201',
    page_number: 4,
    alignment_score: 0.96,
    changes_detected: true,
    change_count: 5,
    change_types: { added: 2, modified: 2, removed: 1 },
    summary_text: `A-201: Shortened staff elevation; updated bale facade; added stair tower.

### Changes Found:
- Shortened staff elevation wall length by 15 feet
- Updated bale facade material callouts and details
- Added new stair tower at north end with egress path
- Modified window openings to match new elevation
- Removed old stair reference and callout`,
    overlay_ref: '/mock-overlays/A-201.png',
    categories: { Architectural: 3, Structural: 1, Concrete: 1 }
  },
  {
    diff_result_id: 'diff-G-101',
    drawing_name: 'G-101',
    page_number: 5,
    alignment_score: 0.99,
    changes_detected: true,
    change_count: 2,
    change_types: { added: 0, modified: 2, removed: 0 },
    summary_text: `G-101: Updated revision table entries and printed revision.

### Changes Found:
- Updated revision table with new entries for Issued for 100%
- Modified printed revision cloud locations and callouts`,
    overlay_ref: '/mock-overlays/G-101.png',
    categories: { Architectural: 2 }
  }
]

const buildDiff = (template: typeof diffTemplates[number]): NonNullable<JobResults['diffs']>[number] => ({
  diff_result_id: template.diff_result_id,
  drawing_name: template.drawing_name,
  page_number: template.page_number,
  alignment_score: template.alignment_score,
  changes_detected: template.changes_detected,
  change_count: template.change_count,
  change_types: template.change_types,
  overlay_ref: template.overlay_ref,
  categories: (template.categories || {}) as unknown as Record<string, number> | undefined,
  summary: {
    summary_id: `${template.diff_result_id}-summary`,
    summary_text: template.summary_text,
    source: 'machine',
    created_at: now
  }
})

export const mockJobResults: Record<string, JobResults> = {
  'job-mock-001': {
    job_id: 'job-mock-001',
    status: 'completed',
    completed_at: now,
    baseline_file_name: '241011_Innisfil Beach Park_Issued for 50.pdf',
    revised_file_name: '241220_Innisfil Beach Park_Issued for 100.pdf',
    kpis: { added: 21, modified: 6, removed: 0 },
    categories: {
      MEP: 8,
      Drywall: 4,
      Electrical: 5,
      Architectural: 3,
      Structural: 6,
      Concrete: 3,
      'Site Work': 2
    },
    diffs: diffTemplates.map(buildDiff)
  },
  'job-mock-002': {
    job_id: 'job-mock-002',
    status: 'in_progress',
    baseline_file_name: 'Core_Level_01.pdf',
    revised_file_name: 'Core_Level_01_Update.pdf',
    message: 'Diff worker is processing page 2',
    diffs: diffTemplates.slice(0, 2).map(buildDiff)
  },
  'job-mock-003': {
    job_id: 'job-mock-003',
    status: 'failed',
    message: 'OCR worker timed out on dense sheet',
    diffs: []
  }
}

export const mockSummaries: Record<string, { active: SummaryRecord; list: SummaryRecord[] }> = diffTemplates.reduce((acc, template) => {
  const summary: SummaryRecord = {
    summary_id: `${template.diff_result_id}-summary`,
    diff_result_id: template.diff_result_id,
    summary_text: template.summary_text,
    source: 'machine',
    is_active: true
  }
  acc[template.diff_result_id] = { active: summary, list: [summary] }
  return acc
}, {} as Record<string, { active: SummaryRecord; list: SummaryRecord[] }>)

// Map diff IDs to real test images for A-101 and A-111
const realImageMapping: Record<string, { overlay?: string; baseline: string; revised: string }> = {
  'diff-A-101': {
    baseline: '/test-images/A-101_baseline.png',
    revised: '/test-images/A-101_revised.png',
  },
  'diff-A-111': {
    baseline: '/test-images/A-111_baseline.png',
    revised: '/test-images/A-111_revised.png',
  }
}

export const mockImageMap: Record<string, { overlay_image_url?: string; baseline_image_url?: string; revised_image_url?: string }> = diffTemplates.reduce((acc, template) => {
  const realImages = realImageMapping[template.diff_result_id]
  if (realImages) {
    // Use real test images
    acc[template.diff_result_id] = {
      overlay_image_url: realImages.overlay || realImages.revised, // Use revised as overlay if no overlay
      baseline_image_url: realImages.baseline,
      revised_image_url: realImages.revised
    }
  } else {
    // Fallback to placeholder
    acc[template.diff_result_id] = {
      overlay_image_url: `https://placehold.co/1200x800?text=${template.diff_result_id}+Overlay`,
      baseline_image_url: `https://placehold.co/600x800?text=${template.diff_result_id}+Baseline`,
      revised_image_url: `https://placehold.co/600x800?text=${template.diff_result_id}+Revised`
    }
  }
  return acc
}, {} as Record<string, { overlay_image_url?: string; baseline_image_url?: string; revised_image_url?: string }>)

export const mockOcrLogs: Record<string, any> = {
  'job-mock-001': {
    job_id: 'job-mock-001',
    ocr_logs: [
      {
        drawing_version_id: 'dv-old-001',
        drawing_name: '241011_Innisfil Beach Park_Issued for 50.pdf',
        log: {
          summary: {
            total_pages: 3,
            drawings_found: ['A-101', 'A-111', 'A-113', 'A-201', 'A-202'],
            project_info: {
              projects: ['Innisfil Beach Park']
            },
            architect_info: {
              architects: ['ABC Architects Inc.']
            },
            revision_summary: {
              total_revisions: 2,
              revisions: ['Issued for 50%', 'Issued for 100%']
            }
          },
          started_at: now,
          completed_at: now,
          pages: [
            { page_number: 1, drawing_name: 'A-101', processed_at: now, extracted_info: { sections: ['Floor Plan', 'Keynotes'] } },
            { page_number: 2, drawing_name: 'A-111', processed_at: now, extracted_info: { sections: ['Mechanical Plan'] } },
            { page_number: 3, drawing_name: 'A-113', processed_at: now, extracted_info: { sections: ['Detail Views'] } }
          ]
        }
      },
      {
        drawing_version_id: 'dv-new-001',
        drawing_name: '241220_Innisfil Beach Park_Issued for 100.pdf',
        log: {
          summary: {
            total_pages: 3,
            drawings_found: ['A-101', 'A-111', 'A-113', 'A-201', 'A-202'],
            project_info: {
              projects: ['Innisfil Beach Park']
            },
            architect_info: {
              architects: ['ABC Architects Inc.']
            },
            revision_summary: {
              total_revisions: 2,
              revisions: ['Issued for 50%', 'Issued for 100%']
            }
          },
          started_at: now,
          completed_at: now,
          pages: [
            { page_number: 1, drawing_name: 'A-101', processed_at: now, extracted_info: { sections: ['Floor Plan', 'Keynotes'] } },
            { page_number: 2, drawing_name: 'A-111', processed_at: now, extracted_info: { sections: ['Mechanical Plan'] } },
            { page_number: 3, drawing_name: 'A-113', processed_at: now, extracted_info: { sections: ['Detail Views'] } }
          ]
        }
      }
    ]
  }
}

// Cost Impact Report Mock Data
export interface CostLineItem {
  item: string
  description: string
  costRange: string
}

export interface CostCategory {
  name: string
  icon: string
  items: CostLineItem[]
}

export interface CostImpactData {
  categories: CostCategory[]
  subtotal: string
  contingency: string
  contingencyPercent: number
  totalEstimate: string
  ballparkTotal: string
  importantNotes: string
  nextSteps: string
}

export const mockCostImpactData: CostImpactData = {
  categories: [
    {
      name: 'Building Modifications',
      icon: '🏗️',
      items: [
        { item: 'Platform Access Hatch', description: 'Hatch & framing support', costRange: '$8,000 – $12,000' },
        { item: 'MRF Ramp Infill', description: 'Demo & concrete infill', costRange: '$25,000 – $35,000' },
        { item: 'Free-standing CMU Walls', description: 'Masonry walls, footings', costRange: '$20,000 – $30,000' },
        { item: 'Gen Set & Fire-Pump Room Mods', description: 'Combine rooms, MEP tie-ins', costRange: '$40,000 – $60,000' },
        { item: 'Bale Canopy Framing Update', description: 'Extra steel & erection', costRange: '$15,000 – $25,000' },
        { item: 'Break-Room Structural Revisions', description: 'New footings & details', costRange: '$10,000 – $15,000' }
      ]
    },
    {
      name: 'Site & Environmental',
      icon: '🌿',
      items: [
        { item: 'LID/BMP Site Controls', description: 'Bio-swales, infiltration & piping', costRange: '$100,000 – $150,000' },
        { item: 'Landscape Detail Sheet', description: 'New planting/irrigation details', costRange: '$5,000 – $8,000' }
      ]
    },
    {
      name: 'Professional Services',
      icon: '📋',
      items: [
        { item: 'A/E Revision Hours', description: 'Arch/Struct/MEP coordination', costRange: '$15,000 – $25,000' },
        { item: 'Permitting: Watermaster & Soils', description: 'Review & filing fees', costRange: '$8,000 – $12,000' },
        { item: 'Pile-Schedule Redesign', description: 'Geotech review & drawings', costRange: '$5,000 – $7,000' },
        { item: 'Egress/Fire-Life Safety Updates', description: 'Exits, signage & capacity', costRange: '$5,000 – $10,000' }
      ]
    }
  ],
  subtotal: '$581,000 – $799,000',
  contingency: '$58,000 – $80,000',
  contingencyPercent: 10,
  totalEstimate: '$640,000 – $880,000',
  ballparkTotal: '$650,000 – $900,000',
  importantNotes: 'This estimate does not include general contractor markup, soft-costs (owner\'s rep, testing, insurance), or escalation beyond today\'s rates.',
  nextSteps: 'Solicit GMP bids from your trade partners to refine each line item.'
}

// Schedule Impact Report Mock Data
export interface ScheduleScenario {
  name: string
  description: string
  impact: string
  probability: number
  color: 'green' | 'yellow' | 'red'
}

export interface CriticalPathItem {
  item: string
  duration: string
  note: string
}

export interface ScheduleImpactData {
  criticalPathItems: CriticalPathItem[]
  overlapSummary: string
  scenarios: ScheduleScenario[]
  bottomLine: string
}

export const mockScheduleImpactData: ScheduleImpactData = {
  criticalPathItems: [
    { item: 'Long-lead equipment', duration: '12–16 weeks', note: 'sits squarely on the critical path.' },
    { item: 'Permitting', duration: '6–8 weeks', note: 'can run in parallel with A/E revisions.' },
    { item: 'Steel works', duration: 'stair tower, canopy', note: 'can overlap procurement once shop drawings are approved.' }
  ],
  overlapSummary: 'If you sequence everything back-to-back, you\'re looking at 6–8 months of additional work. With smart overlap (submit permits while revising drawings, order equipment the moment specs are locked), you can often compress to 3–4 months of net new schedule.',
  scenarios: [
    { 
      name: 'Best-case (parallelized)', 
      description: 'Equipment delivery and permitting are paced, other trades follow.',
      impact: '+3 months',
      probability: 25,
      color: 'green'
    },
    { 
      name: 'Typical-case', 
      description: 'Some permit or shop-drawing re-submittals.',
      impact: '+4 months',
      probability: 50,
      color: 'yellow'
    },
    { 
      name: 'Worst-case (serial)', 
      description: 'If permits or equipment slip and work waits.',
      impact: '+6–8 months',
      probability: 25,
      color: 'red'
    }
  ],
  bottomLine: 'The long-lead gear (transformer, switchgear, cranes) and permit cycles will govern your finish date. Early submittal of drawings and purchase orders is the single best way to avoid a 4+ month delay.'
}

// ============================================
// PROJECT MANAGEMENT MOCK DATA
// ============================================

// Document, Drawing, Comparison interfaces are imported from @/types

// Additional Mock Projects (extends the existing mockProjects from above)
export const mockProjectsExtended: Project[] = [
  {
    project_id: 'proj-001',
    name: 'Default Project',
    description: 'Created automatically from comparison upload',
    owner_id: 'mock-user-001',
    user_id: 'mock-user-001',
    status: 'active',
    created_at: '2025-11-16T10:30:00Z',
    updated_at: '2025-11-16T14:20:00Z',
    document_count: 2,
    drawing_count: 14,
    comparison_count: 3
  },
  {
    project_id: 'proj-002',
    name: 'Innisfil Beach Park',
    description: 'Beach park development - Phase 2 revisions',
    owner_id: 'mock-user-001',
    user_id: 'mock-user-001',
    status: 'active',
    created_at: '2025-10-20T09:00:00Z',
    updated_at: '2025-11-15T16:45:00Z',
    document_count: 4,
    drawing_count: 28,
    comparison_count: 8
  },
  {
    project_id: 'proj-003',
    name: 'Downtown Office Tower',
    description: 'Commercial building - HVAC system updates',
    owner_id: 'mock-user-001',
    user_id: 'mock-user-001',
    status: 'active',
    created_at: '2025-09-05T11:00:00Z',
    updated_at: '2025-11-10T09:30:00Z',
    document_count: 6,
    drawing_count: 45,
    comparison_count: 12
  }
]

// Mock Documents
export const mockDocuments: Document[] = [
  {
    document_id: 'doc-001',
    project_id: 'proj-001',
    name: '241220_Innisfil Beach Park_Issued for 100.pdf',
    file_type: 'application/pdf',
    file_size: 15234567,
    uploaded_at: '2025-11-16T10:30:00Z',
    page_count: 7,
    status: 'ready',
    version: 'revised'
  },
  {
    document_id: 'doc-002',
    project_id: 'proj-001',
    name: '241115_Innisfil Beach Park_Original.pdf',
    file_type: 'application/pdf',
    file_size: 14567890,
    uploaded_at: '2025-11-15T09:00:00Z',
    page_count: 7,
    status: 'ready',
    version: 'baseline'
  },
  {
    document_id: 'doc-003',
    project_id: 'proj-002',
    name: 'A-Series Floor Plans Rev3.pdf',
    file_type: 'application/pdf',
    file_size: 8234567,
    uploaded_at: '2025-11-14T14:00:00Z',
    page_count: 12,
    status: 'ready',
    version: 'revised'
  }
]

// Mock Drawings
export const mockDrawings: Drawing[] = [
  {
    drawing_id: 'draw-001',
    document_id: 'doc-001',
    project_id: 'proj-001',
    name: 'Page-1',
    page_number: 1,
    source_document: '241220_Innisfil Beach Park_Issued for 100.pdf',
    version: 'revised',
    auto_detected: true,
    created_at: '2025-11-16T10:35:00Z'
  },
  {
    drawing_id: 'draw-002',
    document_id: 'doc-001',
    project_id: 'proj-001',
    name: 'Page-2',
    page_number: 2,
    source_document: '241220_Innisfil Beach Park_Issued for 100.pdf',
    version: 'revised',
    auto_detected: true,
    created_at: '2025-11-16T10:35:00Z'
  },
  {
    drawing_id: 'draw-003',
    document_id: 'doc-001',
    project_id: 'proj-001',
    name: 'Page-3',
    page_number: 3,
    source_document: '241220_Innisfil Beach Park_Issued for 100.pdf',
    version: 'revised',
    auto_detected: true,
    created_at: '2025-11-16T10:35:00Z'
  },
  {
    drawing_id: 'draw-004',
    document_id: 'doc-001',
    project_id: 'proj-001',
    name: 'Page-4',
    page_number: 4,
    source_document: '241220_Innisfil Beach Park_Issued for 100.pdf',
    version: 'revised',
    auto_detected: true,
    created_at: '2025-11-16T10:35:00Z'
  },
  {
    drawing_id: 'draw-005',
    document_id: 'doc-001',
    project_id: 'proj-001',
    name: 'Page-5',
    page_number: 5,
    source_document: '241220_Innisfil Beach Park_Issued for 100.pdf',
    version: 'revised',
    auto_detected: true,
    created_at: '2025-11-16T10:35:00Z'
  },
  {
    drawing_id: 'draw-006',
    document_id: 'doc-001',
    project_id: 'proj-001',
    name: 'Page-6',
    page_number: 6,
    source_document: '241220_Innisfil Beach Park_Issued for 100.pdf',
    version: 'revised',
    auto_detected: true,
    created_at: '2025-11-16T10:35:00Z'
  },
  {
    drawing_id: 'draw-007',
    document_id: 'doc-001',
    project_id: 'proj-001',
    name: 'Page-7',
    page_number: 7,
    source_document: '241220_Innisfil Beach Park_Issued for 100.pdf',
    version: 'revised',
    auto_detected: true,
    created_at: '2025-11-16T10:35:00Z'
  }
]

// Mock Comparisons
export const mockComparisons: Comparison[] = [
  {
    comparison_id: 'comp-001',
    project_id: 'proj-001',
    baseline_drawing_id: 'draw-baseline-001',
    revised_drawing_id: 'draw-001',
    job_id: 'job-mock-001',
    status: 'completed',
    created_at: '2025-11-16T11:00:00Z',
    completed_at: '2025-11-16T11:05:00Z',
    change_count: 21
  },
  {
    comparison_id: 'comp-002',
    project_id: 'proj-001',
    baseline_drawing_id: 'draw-baseline-002',
    revised_drawing_id: 'draw-002',
    job_id: 'job-mock-002',
    status: 'completed',
    created_at: '2025-11-16T11:10:00Z',
    completed_at: '2025-11-16T11:15:00Z',
    change_count: 15
  }
]

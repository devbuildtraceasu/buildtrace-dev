// Shared types for results components to avoid circular dependencies

export type ViewMode = 'overlay' | 'side-by-side' | 'baseline' | 'revised'

export interface ChangeItem {
  id: string
  drawing_code?: string
  page_number?: number
  summary: string
  change_type: 'added' | 'modified' | 'removed'
  details?: string[]
  detail_count?: number
}

export interface ChangeDetails {
  id: string
  drawing_code?: string
  page_number?: number
  summary: string
  description?: string | string[]
  change_type: 'added' | 'modified' | 'removed'
  overlay_image_url?: string
  baseline_image_url?: string
  revised_image_url?: string
}

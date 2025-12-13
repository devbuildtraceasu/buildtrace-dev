import { ChangeItem, ChangeDetails } from '@/components/results/types'

// Structured change from backend JSON
interface StructuredChange {
  id: string
  title: string
  description: string
  change_type: 'added' | 'modified' | 'removed'
  location?: string
  impact?: string
  trade_affected?: string
}

interface StructuredSummaryJson {
  drawing_code?: string
  page_number?: number
  overall_summary?: string
  changes?: StructuredChange[]
  critical_change?: {
    title: string
    reason: string
  }
  recommendations?: string[]
  total_changes?: number
  // Legacy fields
  changes_found?: string[]
  change_count?: number
}

/**
 * Parse summary JSON or text to extract structured change items.
 * Prefers structured JSON from backend, falls back to text parsing.
 */
export function parseSummaryToChanges(
  summaryText: string | undefined,
  drawingName?: string,
  pageNumber?: number,
  summaryJson?: StructuredSummaryJson
): ChangeItem[] {
  // If we have structured JSON with changes array, use it directly
  if (summaryJson?.changes && Array.isArray(summaryJson.changes) && summaryJson.changes.length > 0) {
    return summaryJson.changes.map((change, index) => ({
      id: change.id || `change-${index + 1}`,
      drawing_code: summaryJson.drawing_code || drawingName?.match(/^([A-Z]+-\d+)/)?.[1],
      page_number: summaryJson.page_number || pageNumber,
      summary: change.title,
      change_type: change.change_type || 'modified',
      details: [
        change.description,
        change.location ? `Location: ${change.location}` : '',
        change.impact ? `Impact: ${change.impact}` : '',
        change.trade_affected ? `Trade: ${change.trade_affected}` : '',
      ].filter(Boolean),
      detail_count: 4,
    }))
  }

  // Fallback to text parsing
  if (!summaryText) {
    return []
  }

  const trimmedSummary = summaryText.trim()
  if (!trimmedSummary) {
    return []
  }

  const changes: ChangeItem[] = []

  const detectType = (text: string): ChangeItem['change_type'] => {
    const lower = text.toLowerCase()
    if (lower.includes('add') || lower.includes('new ') || lower.includes('[added]')) {
      return 'added'
    }
    if (lower.includes('remove') || lower.includes('delete') || lower.includes('[removed]')) {
      return 'removed'
    }
    return 'modified'
  }

  const pushChange = (
    drawingCode: string | undefined,
    summary: string,
    details: string[],
    typeHint?: ChangeItem['change_type']
  ) => {
    if (!summary && details.length) {
      summary = details[0]
    }
    const changeType = typeHint || detectType(summary)
    changes.push({
      id: `change-${changes.length + 1}`,
      drawing_code: drawingCode || drawingName?.match(/^([A-Z]+-\d+)/)?.[1],
      page_number: pageNumber,
      summary: summary.trim(),
      change_type: changeType,
      details: details.length ? details : undefined,
      detail_count: details.length || undefined,
    })
  }

  // Try to parse numbered changes from text
  // Pattern: "1. [Type] Title: Description" or "1. Title: Description"
  const numberedPattern = /(\d+)\.\s*(?:\[(Added|Modified|Removed)\]\s*)?([^:]+)(?::\s*(.+))?/gi
  const matches = Array.from(trimmedSummary.matchAll(numberedPattern))

  if (matches.length > 0) {
    for (const match of matches) {
      const typeHint = match[2]?.toLowerCase() as ChangeItem['change_type'] | undefined
      const title = match[3]?.trim() || ''
      const description = match[4]?.trim() || ''
      
      pushChange(
        drawingName?.match(/^([A-Z]+-\d+)/)?.[1],
        title,
        description ? [description] : [],
        typeHint
      )
    }
  } else {
    // Try block format: "A-101: content..."
    const blockRegex = /([A-Z]+-\d+):([\s\S]*?)(?=\n[A-Z]+-\d+:|$)/g
    const blockMatches = Array.from(trimmedSummary.matchAll(blockRegex))

    if (blockMatches.length) {
      for (const match of blockMatches) {
        const code = match[1]
        const block = (match[2] || '').trim()
        const lines = block.split(/\n+/).map((line) => line.trim()).filter(Boolean)
        const details: string[] = []
        const summaryPieces: string[] = []

        for (const line of lines) {
          if (/^[-•\d]/.test(line)) {
            details.push(line.replace(/^[-•\d. )]+/, '').trim())
          } else {
            summaryPieces.push(line)
          }
        }

        const summary = summaryPieces.join(' ')
        pushChange(code, summary, details)
      }
    } else {
      // Last fallback: entire summary is one change
      pushChange(undefined, trimmedSummary.substring(0, 200), [])
    }
  }

  return changes
}

/**
 * Convert ChangeItem to ChangeDetails
 */
export function changeItemToDetails(
  item: ChangeItem,
  overlayImageUrl?: string,
  baselineImageUrl?: string,
  revisedImageUrl?: string
): ChangeDetails {
  return {
    id: item.id,
    drawing_code: item.drawing_code,
    page_number: item.page_number,
    summary: item.summary,
    description: item.details && item.details.length ? item.details : item.summary,
    change_type: item.change_type,
    overlay_image_url: overlayImageUrl,
    baseline_image_url: baselineImageUrl,
    revised_image_url: revisedImageUrl,
  }
}

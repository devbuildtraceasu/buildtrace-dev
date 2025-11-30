import { ChangeItem, ChangeDetails } from '@/components/results/types'

/**
 * Parse summary text to extract structured change items.
 * This is a simple parser - can be enhanced based on actual summary format.
 */
export function parseSummaryToChanges(
  summaryText: string | undefined,
  drawingName?: string,
  pageNumber?: number
): ChangeItem[] {
  if (!summaryText) {
    return []
  }

  const trimmedSummary = summaryText.trim()
  if (!trimmedSummary) {
    return []
  }

  const changes: ChangeItem[] = []

  const blockRegex = /([A-Z]+-\d+):([\s\S]*?)(?=\n[A-Z]+-\d+:|$)/g
  const matches = Array.from(trimmedSummary.matchAll(blockRegex))

  const detectType = (text: string): ChangeItem['change_type'] => {
    const lower = text.toLowerCase()
    if (lower.includes('add') || lower.includes('new ')) {
      return 'added'
    }
    if (lower.includes('remove') || lower.includes('delete')) {
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

  if (matches.length) {
    for (const match of matches) {
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
    // Fallback: entire summary is one change
    pushChange(undefined, trimmedSummary, [])
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

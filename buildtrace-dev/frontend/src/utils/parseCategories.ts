/**
 * Parse categories from summary text or changes
 * Categories: MEP, Drywall, Electrical, Architectural, Structural, Concrete, Site Work
 */

export type Category = 'MEP' | 'Drywall' | 'Electrical' | 'Architectural' | 'Structural' | 'Concrete' | 'Site Work'

export function parseCategoriesFromSummary(summaryText?: string): Record<Category, number> {
  const categories: Record<Category, number> = {
    MEP: 0,
    Drywall: 0,
    Electrical: 0,
    Architectural: 0,
    Structural: 0,
    Concrete: 0,
    'Site Work': 0,
  }

  if (!summaryText) return categories

  const lowerText = summaryText.toLowerCase()

  // Simple keyword matching - can be enhanced with NLP
  const categoryKeywords: Record<Category, string[]> = {
    MEP: ['mep', 'mechanical', 'plumbing', 'hvac', 'duct', 'pipe', 'ventilation'],
    Drywall: ['drywall', 'gypsum', 'sheetrock', 'partition', 'wall board'],
    Electrical: ['electrical', 'wiring', 'conduit', 'outlet', 'switch', 'panel', 'circuit'],
    Architectural: ['architectural', 'floor plan', 'elevation', 'section', 'detail', 'room'],
    Structural: ['structural', 'beam', 'column', 'foundation', 'steel', 'concrete structure'],
    Concrete: ['concrete', 'slab', 'pour', 'cement', 'rebar'],
    'Site Work': ['site', 'excavation', 'grading', 'landscaping', 'paving', 'utilities'],
  }

  for (const [category, keywords] of Object.entries(categoryKeywords)) {
    const matches = keywords.filter(keyword => lowerText.includes(keyword)).length
    if (matches > 0) {
      categories[category as Category] = matches
    }
  }

  return categories
}

export function calculateChangeKPIs(changes: Array<{ change_type: 'added' | 'modified' | 'removed' }>): {
  added: number
  modified: number
  removed: number
} {
  return {
    added: changes.filter(c => c.change_type === 'added').length,
    modified: changes.filter(c => c.change_type === 'modified').length,
    removed: changes.filter(c => c.change_type === 'removed').length,
  }
}


import { ComparisonInput, ComparisonResult, ChangeDetail, Category } from "../models";

export interface IComparisonService {
  compare(input: ComparisonInput): Promise<ComparisonResult>;
}

export class ComparisonService implements IComparisonService {
  async compare(input: ComparisonInput): Promise<ComparisonResult> {
    // Simulate processing time
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Simulate random success/failure for realistic demo
    if (Math.random() < 0.1) {
      throw new Error("Failed to process comparison. Please try again.");
    }
    
    // Generate dynamic results based on file names and types
    const dynamicResult = this.generateDynamicResult(input);
    
    return {
      ...dynamicResult,
      id: `comparison-${Date.now()}`,
    };
  }

  private generateDynamicResult(input: ComparisonInput): Omit<ComparisonResult, 'id'> {
    // Generate realistic random numbers for KPIs
    const added = Math.floor(Math.random() * 30) + 5;
    const modified = Math.floor(Math.random() * 15) + 2;
    const removed = Math.floor(Math.random() * 10);
    
    // Extract drawing number from filename if possible
    const drawingNumber = this.extractDrawingNumber(input.baseline.name, input.revised.name);
    
    // Generate category distribution
    const categories: Category[] = ["MEP", "Drywall", "Electrical", "Architectural", "Structural", "Concrete", "Site Work"];
    const byCategory: Record<Category, number> = {} as Record<Category, number>;
    
    let remainingChanges = added + modified + removed;
    
    categories.forEach((category, index) => {
      if (index === categories.length - 1) {
        byCategory[category] = remainingChanges;
      } else {
        const count = Math.floor(Math.random() * Math.min(remainingChanges, 8));
        byCategory[category] = count;
        remainingChanges -= count;
      }
    });

    // Generate realistic changes based on file types and names
    const changes = this.generateChanges(input, added, modified, removed);

    return {
      drawingNumber,
      autoDetectedDrawingNumber: !!drawingNumber,
      kpis: { added, modified, removed },
      byCategory,
      changes,
    };
  }

  private extractDrawingNumber(baselineName: string, revisedName: string): string | undefined {
    // Try to extract drawing numbers from common patterns
    const patterns = [
      /([A-Z]-?\d{2,4})/,  // A-101, E200, etc.
      /(Page-?\d+)/i,      // Page-9, page9, etc.
      /(\d{2,4}[A-Z]?)/,   // 101A, 200, etc.
    ];

    for (const pattern of patterns) {
      const match = baselineName.match(pattern) || revisedName.match(pattern);
      if (match) {
        return match[1];
      }
    }

    return undefined;
  }

  private generateChanges(input: ComparisonInput, added: number, modified: number, removed: number): ChangeDetail[] {
    const changes: ChangeDetail[] = [];
    const changeTypes = [
      { action: "added" as const, count: added },
      { action: "modified" as const, count: modified },
      { action: "removed" as const, count: removed },
    ];

    let changeId = 1;

    changeTypes.forEach(({ action, count }) => {
      for (let i = 0; i < Math.min(count, 5); i++) {
        const change = this.generateSingleChange(changeId++, action, input);
        if (change) {
          changes.push(change);
        }
      }
    });

    return changes;
  }

  private generateSingleChange(id: number, action: "added" | "modified" | "removed", input: ComparisonInput): ChangeDetail {
    const categories: Category[] = ["MEP", "Drywall", "Electrical", "Architectural", "Structural", "Concrete", "Site Work"];
    const randomCategory = categories[Math.floor(Math.random() * categories.length)];
    
    const drawingCodes = ["A-101", "E-200", "M-150", "S-100", "P-300", "C-250"];
    const randomCode = drawingCodes[Math.floor(Math.random() * drawingCodes.length)];

    const summaries = {
      added: [
        "New electrical panel and circuit routing added",
        "Additional HVAC equipment installed in utility room",
        "New structural support beam added to main floor",
        "Fire safety system components added to east wing",
        "Additional plumbing fixtures added to restrooms",
      ],
      modified: [
        "Updated HVAC ductwork layout for improved airflow",
        "Modified electrical panel specifications and load calculations",
        "Revised structural beam sizing and connection details",
        "Updated fire damper locations and controls",
        "Modified plumbing layout for accessibility compliance",
      ],
      removed: [
        "Removed future expansion space from current phase",
        "Eliminated redundant electrical circuits",
        "Removed temporary construction access points",
        "Deleted unused equipment spaces",
        "Removed conflicting structural elements",
      ],
    };

    const descriptions = {
      added: [
        "New component installed per latest design requirements",
        "Equipment specifications updated to meet current codes",
        "Installation coordinates verified with field conditions",
        "Integration with existing systems confirmed",
      ],
      modified: [
        "Design updated to reflect engineering analysis",
        "Specifications revised per consultant recommendations",
        "Layout optimized for construction efficiency",
        "Coordination with other building systems verified",
      ],
      removed: [
        "Item eliminated to reduce project scope",
        "Component no longer required per design changes",
        "Removal coordinated with affected building systems",
        "Cost savings opportunity identified and implemented",
      ],
    };

    const summary = summaries[action][Math.floor(Math.random() * summaries[action].length)];
    const description = descriptions[action].slice(0, Math.floor(Math.random() * 3) + 2);

    return {
      id: `change-${id}`,
      drawingCode: randomCode,
      summary,
      description,
      action,
      categories: [randomCategory],
      detailCount: description.length,
    };
  }
}

export const comparisonService = new ComparisonService();

import { ComparisonResult, ComparisonInput } from "../models";

export interface IReportService {
  exportPdf(result: ComparisonResult, input: ComparisonInput): Promise<Blob>;
}

export class ReportService implements IReportService {
  async exportPdf(result: ComparisonResult, input: ComparisonInput): Promise<Blob> {
    // For now, create a simple text-based PDF content
    const reportContent = this.generateReportContent(result, input);
    
    // In a real implementation, you would use jsPDF or html2pdf here
    // For now, return a mock blob
    const blob = new Blob([reportContent], { type: 'application/pdf' });
    
    return blob;
  }

  private generateReportContent(result: ComparisonResult, input: ComparisonInput): string {
    return `
BuildTrace AI - Comparison Report
================================

Drawing Comparison: ${input.baseline.name} vs ${input.revised.name}
Drawing Number: ${result.drawingNumber || 'N/A'}
Generated: ${new Date().toLocaleString()}

SUMMARY
-------
Added: ${result.kpis.added}
Modified: ${result.kpis.modified} 
Removed: ${result.kpis.removed}
CHANGES
-------
${result.changes.map(change => 
  `${change.drawingCode}: ${change.summary}\n  Details: ${change.detailCount} items`
).join('\n\n')}
    `.trim();
  }
}

export const reportService = new ReportService();

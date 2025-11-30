import { ComparisonResult, ChangeDetail } from "../models";

export const mockComparisonResult: ComparisonResult = {
  id: "comparison-1",
  drawingNumber: "Page-9",
  autoDetectedDrawingNumber: true,
  kpis: {
    added: 21,
    modified: 6,
    removed: 0,
  },
  changes: [
    {
      id: "change-1",
      drawingCode: "A-101",
      summary: "Removed future studio; updated keynotes and building area summary",
      description: [
        "Studio space marked for future development has been removed from current phase",
        "Keynote references updated to reflect space allocation changes",
        "Building area summary table recalculated with new square footage",
        "Drawing scale and reference points maintained",
        "No impact to structural or MEP systems in affected area",
      ],
      action: "removed",
      categories: ["Architectural"],
      detailCount: 5,
      thumbnails: {
        baseline: "/api/thumbnails/baseline-1.png",
        revised: "/api/thumbnails/revised-1.png",
        overlay: "/api/thumbnails/overlay-1.png",
      },
    },
    {
      id: "change-2",
      drawingCode: "E-200",
      summary: "Added new electrical panel and updated circuit routing",
      description: [
        "New electrical panel installed in utility room",
        "Circuit routing updated to accommodate additional loads",
        "Conduit paths modified for optimal installation",
      ],
      action: "added",
      categories: ["Electrical"],
      detailCount: 3,
    },
    {
      id: "change-3", 
      drawingCode: "M-150",
      summary: "Modified HVAC ductwork layout and added new return air paths",
      description: [
        "Ductwork layout optimized for better airflow",
        "New return air paths added to improve circulation",
        "Equipment schedules updated with new specifications",
        "Zone controls modified for enhanced comfort",
        "Energy calculations updated to reflect changes",
        "Coordination with structural members verified",
        "Fire damper locations adjusted as needed",
      ],
      action: "modified",
      categories: ["MEP"],
      detailCount: 7,
    },
    {
      id: "change-4",
      drawingCode: "S-100", 
      summary: "Updated structural beam specifications and load calculations",
      description: [
        "Beam sizes increased to handle additional loads",
        "Load calculations updated per latest building codes",
      ],
      action: "modified",
      categories: ["Structural"],
      detailCount: 2,
    },
  ],
};

export const mockRecentItems = [
  {
    id: "comparison-1",
    date: "2024-01-15",
    drawingNumber: "Page-9",
    baselineName: "floor-plan-v1.pdf",
    revisedName: "floor-plan-v2.pdf", 
    changesCount: 27,
  },
  {
    id: "comparison-2",
    date: "2024-01-14",
    drawingNumber: "A-101",
    baselineName: "architectural-plan-old.dwg",
    revisedName: "architectural-plan-new.dwg",
    changesCount: 14,
  },
  {
    id: "comparison-3",
    date: "2024-01-13", 
    drawingNumber: "E-200",
    baselineName: "electrical-layout-v1.pdf",
    revisedName: "electrical-layout-v2.pdf",
    changesCount: 8,
  },
];

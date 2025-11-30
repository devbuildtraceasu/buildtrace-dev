export type FileRef = {
  id: string;
  name: string;
  size: number;
  type: "pdf" | "dwg" | "dxf" | "png" | "jpg";
  url?: string;
};

export type ComparisonInput = {
  baseline: FileRef;
  revised: FileRef;
};

export type ChangeAction = "added" | "modified" | "removed";

export type Category = string;

export type ChangeItem = {
  id?: string;
  drawing_code?: string;
  action?: ChangeAction;
  description?: string;
  categories?: Category[];
};

export type ChangesPayload = {
  change_list?: ChangeItem[];
  page_summaries?: Record<string, string>;
};

export type ComparisonResult = {
  id: string;
  drawingNumber?: string;
  autoDetectedDrawingNumber: boolean;
  kpis: { added: number; modified: number; removed: number };
  changes: ChangesPayload | any; // server-provided payload; prefer ChangesPayload shape
  pageInfo?: { added: number; modified: number; removed: number };
  pageMapping?: Array<[string, number, number]>;
  /**
   * When true, the comparison is still processing and KPIs may be provisional.
   * Use this to show placeholders (e.g., dashes) in the UI until finalized.
   */
  isPartial?: boolean;
};



export type ViewMode = "side-by-side" | "overlay" | "baseline" | "revised";

export type StepperStep = "upload-old" | "upload-new" | "process" | "results";

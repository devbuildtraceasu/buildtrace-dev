import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useComparisonStore } from "@/features/comparison/state/useComparisonStore";

export default function ChangesList() {
  const { result, selectedChangeId, selectChange } = useComparisonStore();

  // Expect new simplified shape: { changeList?: ChangeItem[], page_summaries?: Record<string,string> }
  const changesObj: any = (!Array.isArray(result?.changes) && result?.changes) ? result?.changes : undefined;
  const list: any[] = Array.isArray(changesObj?.change_list) ? changesObj.change_list : [];
  const pageSummaries: Record<string, string> = (changesObj?.page_summaries || {}) as Record<string, string>;

  const groups = new Map<string, { count: number; summary?: string }>();
  for (const it of list) {
    const code = (it?.drawing_code || result?.drawingNumber || 'Unknown').toString();
    const inc = typeof it?.description === 'string' && it.description ? 1 : 0;
    const preferred = pageSummaries[code];
    const prev = groups.get(code) || { count: 0, summary: preferred };
    groups.set(code, { count: prev.count + inc, summary: prev.summary || preferred });
  }

  const flatChanges: Array<{ id: string; drawingCode: string; summary: string; detailCount: number; placeholder?: boolean }>
    = Array.from(groups.entries()).map(([code, data]) => ({
      id: `page-${code}`,
      drawingCode: code,
      summary: data.summary || 'Changes detected',
      detailCount: data.count,
    }));

  // Fallback: if we don't yet have parsed change_list but we DO have pageMapping,
  // pre-populate bubbles so the UI doesn't misleadingly say "No changes found".
  let mappingCodes: string[] = [];
  try {
    let pm: any = (result as any)?.pageMapping;
    if (!Array.isArray(pm) && typeof pm === 'string') {
      pm = JSON.parse(pm);
    }
    if (Array.isArray(pm)) {
      mappingCodes = pm.map((m: any) => (Array.isArray(m) ? String(m[0]) : undefined)).filter(Boolean);
    }
  } catch (_) {}

  const isAnalyzing = !!(result as any)?.isPartial;

  let displayChanges: Array<{ id: string; drawingCode: string; summary: string; detailCount: number; placeholder?: boolean }>; 
  if (isAnalyzing && mappingCodes.length > 0) {
    // While analyzing, always show ALL mapped pages; fill in details for those that arrived
    const allCodes = Array.from(new Set<string>([...mappingCodes, ...flatChanges.map((c) => c.drawingCode)]));
    displayChanges = allCodes.map((code) => {
      const hit = flatChanges.find((c) => c.drawingCode === code);
      return hit
        ? hit
        : {
            id: `page-${code}`,
            drawingCode: code,
            summary: pageSummaries[code] || 'Analyzing changes…',
            detailCount: 0,
            placeholder: true,
          };
    });
  } else {
    // Not analyzing: prefer concrete changes; fall back to mapping if nothing parsed
    displayChanges = flatChanges.length > 0
      ? flatChanges
      : mappingCodes.map((code) => ({
          id: `page-${code}`,
          drawingCode: code,
          summary: pageSummaries[code] || 'Changes detected',
          detailCount: 0,
          placeholder: true,
        }));
  }

  if (displayChanges.length === 0) {
    return (
      <div className="bg-white rounded-2xl shadow-card p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-6">Changes List</h2>
        <div className="text-center text-gray-500 py-12">
          {isAnalyzing ? 'Analyzing changes…' : 'No changes found'}
        </div>
      </div>
    );
  }

  const getBadgeVariant = (drawingCode: string) => {
    // Simple hash to consistent color assignment
    const variants = ["default", "secondary", "outline"] as const;
    const index = drawingCode.charCodeAt(0) % variants.length;
    return variants[index];
  };

  return (
    <div className="bg-white rounded-2xl shadow-card p-6" data-testid="changes-list">
      <h2 className="text-xl font-semibold text-gray-900 mb-6">Changes List</h2>
      {isAnalyzing && (
        <div className="mb-4 text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded-md px-3 py-2">
          Analysis in progress. Page bubbles are preloaded from the drawing map; details will appear as they’re ready.
        </div>
      )}
      
      <div className="space-y-3">
        {displayChanges.map((change: any) => {
          const isSelected = change.id === selectedChangeId;
          
          return (
            <div
              key={change.id}
              onClick={() => selectChange(change.id)}
              className={cn(
                "border rounded-lg p-4 cursor-pointer transition-colors",
                {
                  "change-item-selected": isSelected,
                  "border-gray-200 hover:bg-gray-50": !isSelected,
                }
              )}
              data-testid={`change-item-${change.id}`}
            >
              <div className="flex items-start justify-between mb-2">
                <Badge 
                  variant={getBadgeVariant(change.drawingCode)}
                  className="text-xs"
                  data-testid={`badge-drawing-code-${change.id}`}
                >
                  {change.drawingCode}
                </Badge>
                <span className="text-xs text-gray-500" data-testid={`text-detail-count-${change.id}`}>
                  {change.placeholder ? 'pending…' : `${change.detailCount} details`}
                </span>
              </div>
              <p className="text-sm text-gray-700" data-testid={`text-summary-${change.id}`}>
                {change.summary}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

import { Image } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { useComparisonStore } from "@/features/comparison/state/useComparisonStore";
import PdfViewer from "@/libs/pdf/PdfViewer";
import { useEffect, useState } from "react";
import { apiRequest } from "@/lib/queryClient";

export default function ChangeDetailsPanel() {
  const { result, selectedChangeId, input } = useComparisonStore();
  const [overlayUrl, setOverlayUrl] = useState<string | null>(null);

  // Determine current drawing code from selection
  const currentCode = (() => {
    if (selectedChangeId && selectedChangeId.startsWith('page-')) {
      return selectedChangeId.replace(/^page-/, '');
    }
    return result?.drawingNumber || undefined;
  })();

  // Use matches to map old/new pages (zero-based -> convert to 1-based for pdf.js)
  const { oldPage, newPage } = (() => {
    let o: number | undefined = undefined, n: number | undefined = undefined;
    let matches: any = (result as any)?.pageMapping;
    if (!Array.isArray(matches) && typeof matches === 'string') {
      try { matches = JSON.parse(matches); } catch { matches = undefined; }
    }
    const toIndex = (val: unknown): number | undefined => {
      if (typeof val === 'number' && Number.isInteger(val)) return val;
      if (typeof val === 'string') {
        const parsed = parseInt(val, 10);
        return Number.isFinite(parsed) ? parsed : undefined;
      }
      return undefined;
    };
    if (Array.isArray(matches) && matches.length > 0) {
      const target = typeof currentCode === 'string' ? currentCode.trim() : undefined;
      const hit = target
        ? matches.find((m) => Array.isArray(m) && typeof m[0] !== 'undefined' && String(m[0]).trim() === target)
        : undefined;
      const chosen = Array.isArray(hit) ? hit : matches[0];
      if (Array.isArray(chosen)) {
        const ro = toIndex(chosen[1]);
        const rn = toIndex(chosen[2]);
        o = ro !== undefined ? ro + 1 : undefined;
        n = rn !== undefined ? rn + 1 : undefined;
      }
    }
    return { oldPage: o, newPage: n };
  })();

  const hasMapping = Number.isInteger(oldPage) && Number.isInteger(newPage) && (oldPage as number) > 0 && (newPage as number) > 0;

  useEffect(() => {
    let cancelled = false;
    let timer: number | undefined;
    const tick = async () => {
      if (cancelled) return;
      if (!result?.id || !currentCode) {
        timer = window.setTimeout(tick, 5000);
        return;
      }
      try {
        const res = await apiRequest('GET', `/api/comparisons/${result.id}/overlay?code=${encodeURIComponent(currentCode)}`);
        if (res.ok) {
          const data = await res.json();
          if (data?.url) {
            if (!cancelled) setOverlayUrl(data.url);
            return; // stop polling on success
          }
        }
      } catch (_) {
        // ignore and continue polling
      }
      timer = window.setTimeout(tick, 5000);
    };
    setOverlayUrl(null);
    tick();
    return () => {
      cancelled = true;
      if (timer) window.clearTimeout(timer);
    };
  }, [result?.id, currentCode]);
  
  // Simplified shape: result.changes = { change_list?: ChangeItem[], page_summaries?: Record<string,string> }
  const changesObj: any = (!Array.isArray(result?.changes) && result?.changes) ? result?.changes : undefined;
  const items = Array.isArray(changesObj?.change_list) ? (changesObj.change_list as any[]) : [];

  const normalized = items.map((item: any, idx: number) => {
    const type = (item?.action || 'change').toString().toLowerCase();
    const id = item?.id || `${type}-${idx}`;
    const drawingCode = item?.drawing_code || (result?.drawingNumber || 'Unknown');
    const summary = undefined as any; // summary comes from page_summaries by code in aggregated view
    const description = typeof item?.description === 'string' && item.description ? [item.description] : [];
    const detailCount = description.length || 0;
    return { id, drawingCode, summary, description, detailCount };
  });

  let selectedChange = normalized.find(c => c.id === selectedChangeId);

  // If user clicked the aggregated page bubble (e.g., id: page-A-101), synthesize a combined view
  if (!selectedChange && selectedChangeId && selectedChangeId.startsWith('page-')) {
    const drawingCode = selectedChangeId.replace(/^page-/, '');
    const makeLine = (it: any) => {
      if (typeof it === 'string') return it;
      return (
        it?.summary ||
        [it?.action, it?.aspect, it?.detail, it?.location]
          .filter(Boolean)
          .join(' - ')
      );
    };
    const combinedDescriptions: string[] = [];
    const pageSummaries = (changesObj as any)?.page_summaries || {};
    const addedSrcAll: any[] = items.filter((it: any) => (it?.action || '').toLowerCase() === 'added');
    const modifiedSrcAll: any[] = items.filter((it: any) => (it?.action || '').toLowerCase() === 'modified');
    const removedSrcAll: any[] = items.filter((it: any) => (it?.action || '').toLowerCase() === 'removed');

    // Filter by the selected drawing code if items carry it
    const codeOf = (it: any) => (it?.drawing_code || it?.drawingCode);
    const filterByCode = (arr: any[]) => arr.filter((it) => {
      const c = codeOf(it);
      return !c || String(c) === drawingCode; // if no code present, keep it for backward compatibility
    });

    const addedSrc = filterByCode(addedSrcAll);
    const modifiedSrc = filterByCode(modifiedSrcAll);
    const removedSrc = filterByCode(removedSrcAll);

    const summarizeItem = (it: any): string | undefined => (typeof it?.description === 'string' && it.description) ? it.description : undefined;

    const pushLines = (src: any[]) => {
      src.forEach((it) => {
        const line = summarizeItem(it);
        if (line) combinedDescriptions.push(line);
      });
    };
    pushLines(addedSrc);
    pushLines(modifiedSrc);
    pushLines(removedSrc);

    selectedChange = {
      id: selectedChangeId,
      drawingCode,
      summary: (typeof pageSummaries?.[drawingCode] === 'string' && pageSummaries[drawingCode])
        || `Changes for ${drawingCode}`,
      description: combinedDescriptions,
      detailCount: combinedDescriptions.length,
    } as any;
  }

  if (!selectedChange) {
    return (
      <div className="bg-white rounded-2xl shadow-card p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-6">Selected Change Details</h2>
        {((result as any)?.isPartial) ? (
          <div className="text-center text-gray-600 py-12">
            <div className="inline-flex items-center gap-2 text-sm bg-amber-50 border border-amber-200 text-amber-900 rounded-md px-3 py-2">
              <span>Analyzing changes… select a page to preview while details load.</span>
            </div>
          </div>
        ) : (
          <div className="text-center text-gray-500 py-12">
            Select a change from the list to view details
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl shadow-card p-6" data-testid="change-details-panel">
      <h2 className="text-xl font-semibold text-gray-900 mb-6">Selected Change Details</h2>
      
      <div className="space-y-6">
        {/* Page bubble */}
        <div className="flex items-center gap-3">
          <Badge variant="secondary" className="text-xs" data-testid="detail-drawing-code">
            {selectedChange.drawingCode}
          </Badge>
          <span className="text-xs text-gray-500">{((result as any)?.isPartial && !Array.isArray(selectedChange.description)) ? 'pending…' : `${selectedChange.detailCount} details`}</span>
        </div>

        {/* Summary */}
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Summary</h3>
          <p className="text-gray-700" data-testid="text-change-summary">
            {((result as any)?.isPartial && !selectedChange.summary) ? 'Analyzing changes…' : selectedChange.summary}
          </p>
        </div>
        
        {/* Description */}
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-3">Description</h3>
          {Array.isArray(selectedChange.description) && selectedChange.description.length > 0 ? (
            <ul className="list-disc pl-5 space-y-2 text-sm text-gray-700" data-testid="list-change-description">
              {selectedChange.description.map((item: any, index: number) => (
                <li key={index} className="marker:text-gray-400" data-testid={`description-item-${index}`}>
                  <span className="block leading-relaxed align-top">{item}</span>
                </li>
              ))}
            </ul>
          ) : (
            <div className="text-sm text-gray-500">{(result as any)?.isPartial ? 'Details are still being analyzed…' : 'No description available.'}</div>
          )}
        </div>
        
        {/* Thumbnails */}
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-3">Visual Comparison</h3>
          <div className="grid grid-cols-3 gap-3" data-testid="thumbnails-container">
            <div className="text-center">
              <div className="bg-gray-100 border border-gray-300 rounded-lg p-2 mb-2 overflow-hidden max-h-40">
                {input?.baseline?.url && hasMapping ? (
                  <PdfViewer key={`${input.baseline.url}:${currentCode || 'none'}`} fileUrl={input.baseline.url} page={oldPage} scale={100} className="w-full" />
                ) : (
                  <div className="h-20 flex items-center justify-center"><Image className="h-6 w-6 text-gray-400" /></div>
                )}
              </div>
              <span className="text-xs text-gray-600">baseline</span>
            </div>
            <div className="text-center">
              <div className="bg-gray-100 border border-gray-300 rounded-lg p-2 mb-2 overflow-hidden max-h-40">
                {input?.revised?.url && hasMapping ? (
                  <PdfViewer key={`${input.revised.url}:${currentCode || 'none'}`} fileUrl={input.revised.url} page={newPage} scale={100} className="w-full" />
                ) : (
                  <div className="h-20 flex items-center justify-center"><Image className="h-6 w-6 text-gray-400" /></div>
                )}
              </div>
              <span className="text-xs text-gray-600">revised</span>
            </div>
            <div className="text-center">
              <div className="bg-gray-100 border border-gray-300 rounded-lg p-2 mb-2 overflow-hidden max-h-40">
                {overlayUrl ? (
                  <PdfViewer key={`${overlayUrl}:${currentCode || 'none'}`} fileUrl={overlayUrl} scale={100} className="w-full" />
                ) : (
                  <div className="h-20 flex items-center justify-center"><Image className="h-6 w-6 text-gray-400" /></div>
                )}
              </div>
              <span className="text-xs text-gray-600">overlay</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

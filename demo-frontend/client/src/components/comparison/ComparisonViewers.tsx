import PdfViewer from "@/libs/pdf/PdfViewer";
import { pdfService } from "@/libs/pdf/PdfService";
import { useEffect, useState, useCallback, useRef } from "react";
import { apiRequest } from "@/lib/queryClient";
import { useComparisonStore } from "@/features/comparison/state/useComparisonStore";

export default function ComparisonViewers() {
  const { input, viewMode, zoom, result, selectedChangeId, setZoom } = useComparisonStore();
  const [overlayUrl, setOverlayUrl] = useState<string | null>(null);
  const [syncPanLeft, setSyncPanLeft] = useState<number>(0);
  const [syncPanTop, setSyncPanTop] = useState<number>(0);
  const lastPanSourceRef = useRef<'baseline' | 'revised' | null>(null);
  const [syncZoom, setSyncZoom] = useState<number>(zoom);
  const lastZoomSourceRef = useRef<'baseline' | 'revised' | null>(null);

  // Synchronized panning handlers
  const handleBaselinePan = useCallback((scrollLeft: number, scrollTop: number) => {
    if (lastPanSourceRef.current === 'revised') return; // Avoid feedback loop
    lastPanSourceRef.current = 'baseline';
    setSyncPanLeft(scrollLeft);
    setSyncPanTop(scrollTop);
    setTimeout(() => {
      lastPanSourceRef.current = null;
    }, 50);
  }, []);

  const handleRevisedPan = useCallback((scrollLeft: number, scrollTop: number) => {
    if (lastPanSourceRef.current === 'baseline') return; // Avoid feedback loop
    lastPanSourceRef.current = 'revised';
    setSyncPanLeft(scrollLeft);
    setSyncPanTop(scrollTop);
    setTimeout(() => {
      lastPanSourceRef.current = null;
    }, 50);
  }, []);

  // Synchronized zoom handlers
  const handleBaselineZoom = useCallback((newZoom: number) => {
    if (lastZoomSourceRef.current === 'revised') return; // Avoid feedback loop
    lastZoomSourceRef.current = 'baseline';
    setSyncZoom(newZoom);
    setZoom(newZoom); // Update global zoom state
    setTimeout(() => {
      lastZoomSourceRef.current = null;
    }, 50);
  }, [setZoom]);

  const handleRevisedZoom = useCallback((newZoom: number) => {
    if (lastZoomSourceRef.current === 'baseline') return; // Avoid feedback loop
    lastZoomSourceRef.current = 'revised';
    setSyncZoom(newZoom);
    setZoom(newZoom); // Update global zoom state
    setTimeout(() => {
      lastZoomSourceRef.current = null;
    }, 50);
  }, [setZoom]);

  // Sync internal zoom with external zoom prop
  useEffect(() => {
    setSyncZoom(zoom);
  }, [zoom]);

  const startOverlayPolling = useCallback((code?: string) => {
    if (!result?.id) return;
    let cancelled = false;
    let timer: number | undefined;
    const tick = async () => {
      if (cancelled) return;
      try {
        const qs = code ? `?code=${encodeURIComponent(code)}` : '';
        const res = await apiRequest('GET', `/api/comparisons/${result.id}/overlay${qs}`);
        if (res.ok) {
          const data = await res.json();
          if (data?.url) {
            setOverlayUrl(data.url);
            return; // stop polling once available
          }
        }
      } catch (_) {}
      timer = window.setTimeout(tick, 5000);
    };
    tick();
    return () => {
      cancelled = true;
      if (timer) window.clearTimeout(timer);
    };
  }, [result?.id]);

  // current drawing code based on selection or derive from first structured change
  const currentCode = (() => {
    if (selectedChangeId && selectedChangeId.startsWith('page-')) {
      return selectedChangeId.replace(/^page-/, '');
    }
    if (result?.drawingNumber) return result.drawingNumber;
    const ch: any = result?.changes;
    if (ch && !Array.isArray(ch)) {
      const pick = (arr: any[]) => Array.isArray(arr) && arr.length > 0 ? arr[0]?.drawing_code : undefined;
      return pick(ch.added) || pick(ch.modified) || pick(ch.removed) || undefined;
    }
    // Fallback: derive from first mapping entry if available
    let matches: any = (result as any)?.pageMapping;
    if (!Array.isArray(matches) && typeof matches === 'string') {
      try { matches = JSON.parse(matches); } catch { matches = undefined; }
    }
    if (Array.isArray(matches) && matches.length > 0 && Array.isArray(matches[0]) && matches[0][0]) {
      return String(matches[0][0]);
    }
    return undefined;
  })();

  // reset mapping state and poll overlay when code changes
  useEffect(() => {
    if (!result?.id) return;
    setOverlayUrl(null);
    const cleanup = startOverlayPolling(currentCode);
    return () => {
      if (typeof cleanup === 'function') cleanup();
    };
  }, [result?.id, currentCode, startOverlayPolling]);

  // Preload baseline/revised PDFs once input is available
  useEffect(() => {
    if (!input?.baseline?.url || !input?.revised?.url) return;
    pdfService.preload([input.baseline.url, input.revised.url]);
  }, [input?.baseline?.url, input?.revised?.url]);

  if (!input) {
    return (
      <div className="bg-white rounded-2xl shadow-card p-6">
        <div className="text-center text-gray-500 py-12">
          No comparison data available
        </div>
      </div>
    );
  }

  const { oldPage, newPage } = (() => {
    let o: number | undefined = undefined, n: number | undefined = undefined;
    let matches: any = (result as any)?.pageMapping;
    if (!Array.isArray(matches) && typeof matches === 'string') {
      try { matches = JSON.parse(matches); } catch { matches = undefined; }
    }

    const toIndex = (val: unknown): number | undefined => {
      if (typeof val === 'number' && Number.isInteger(val)) return val;
      if (typeof val === 'string') {
        const parsed = parseInt(val.trim(), 10);
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
      console.log('[viewers] mapping', { currentCode: target, chosen, matchesLen: matches.length });
      if (Array.isArray(chosen)) {
        const ro = toIndex(chosen[1]);
        const rn = toIndex(chosen[2]);
        o = ro !== undefined ? ro + 1 : undefined;
        n = rn !== undefined ? rn + 1 : undefined;
      }
    }
    console.log('[viewers] pages', { oldPage: o, newPage: n });
    return { oldPage: o, newPage: n };
  })();

  const hasMapping = Number.isInteger(oldPage) && Number.isInteger(newPage) && (oldPage as number) >= 1 && (newPage as number) >= 1;

  const renderSideBySide = () => (
    <div className="grid md:grid-cols-2 gap-6">
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-gray-900">Baseline Drawing</h3>
        {hasMapping ? (
          <PdfViewer
            key={`${input.baseline.url}:${currentCode || 'none'}`}
            fileUrl={input.baseline.url}
            page={oldPage}
            scale={lastZoomSourceRef.current === 'revised' ? syncZoom : zoom}
            className="border border-gray-300 rounded-xl bg-gray-50"
            onPanChange={handleBaselinePan}
            externalPanLeft={lastPanSourceRef.current === 'revised' ? syncPanLeft : undefined}
            externalPanTop={lastPanSourceRef.current === 'revised' ? syncPanTop : undefined}
            onZoomChange={handleBaselineZoom}
          />
        ) : (
          <div className="border border-gray-300 rounded-xl bg-gray-50 h-40 flex items-center justify-center text-gray-500">
            Waiting for page mapping…
          </div>
        )}
      </div>
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-gray-900">Revised Drawing</h3>
        {hasMapping ? (
          <PdfViewer
            key={`${input.revised.url}:${currentCode || 'none'}`}
            fileUrl={input.revised.url}
            page={newPage}
            scale={lastZoomSourceRef.current === 'baseline' ? syncZoom : zoom}
            className="border border-gray-300 rounded-xl bg-gray-50"
            onPanChange={handleRevisedPan}
            externalPanLeft={lastPanSourceRef.current === 'baseline' ? syncPanLeft : undefined}
            externalPanTop={lastPanSourceRef.current === 'baseline' ? syncPanTop : undefined}
            onZoomChange={handleRevisedZoom}
          />
        ) : (
          <div className="border border-gray-300 rounded-xl bg-gray-50 h-40 flex items-center justify-center text-gray-500">
            Waiting for page mapping…
          </div>
        )}
      </div>
    </div>
  );

  const renderOverlay = () => (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">Overlay View</h3>
        {/** Slider temporarily disabled */}
      </div>
      <div className="relative border border-gray-300 rounded-xl bg-gray-50 p-3">
        {overlayUrl ? (
          <PdfViewer key={`${overlayUrl}:${currentCode || 'none'}`} fileUrl={overlayUrl} scale={zoom} className="w-full" />
        ) : (
          <div className="flex items-center justify-center min-h-48 py-16">
            <div className="text-center text-gray-600">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-3"></div>
              <p>Generating overlay…</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );

  const renderSingle = (title: string, fileRef: typeof input.baseline) => (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
      {hasMapping ? (
        <PdfViewer
          fileUrl={fileRef.url}
          page={title.startsWith('Baseline') ? oldPage : newPage}
          scale={zoom}
          className="border border-gray-300 rounded-xl bg-gray-50"
        />
      ) : (
        <div className="border border-gray-300 rounded-xl bg-gray-50 h-40 flex items-center justify-center text-gray-500">
          Waiting for page mapping…
        </div>
      )}
    </div>
  );

  return (
    <div className="bg-white rounded-2xl shadow-card p-6" data-testid="comparison-viewers">
      {viewMode === "side-by-side" && renderSideBySide()}
      {viewMode === "overlay" && renderOverlay()}
      {viewMode === "baseline" && renderSingle("Baseline Drawing", input.baseline)}
      {viewMode === "revised" && renderSingle("Revised Drawing", input.revised)}
    </div>
  );
}

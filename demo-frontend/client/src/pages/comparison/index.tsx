import { useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ArrowLeft, CheckCircle } from "lucide-react";
import ComparisonToolbar from "@/components/comparison/ComparisonToolbar";
import ViewModeToggle from "@/components/comparison/ViewModeToggle";
import ComparisonViewers from "@/components/comparison/ComparisonViewers";
import SummarySection from "@/components/comparison/SummarySection";
import ChangesList from "@/components/comparison/ChangesList";
import ChangeDetailsPanel from "@/components/comparison/ChangeDetailsPanel";
import { useComparisonStore } from "@/features/comparison/state/useComparisonStore";
import { mockComparisonResult } from "@/features/comparison/mocks/fixtures";
import { apiRequest } from "@/lib/queryClient";
import { recentService } from "@/features/recent/services/recentService";
import AskPanel from "@/components/comparison/AskPanel";

export default function ComparisonPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { result, setResult, selectChange, setInput, setError, input, selectedChangeId } = useComparisonStore();
  

  useEffect(() => {
    
    if (!id) return;
    let isCancelled = false;
    let pollTimer: number | undefined;
    const loadOnce = async () => {
      try {
        const url = `/api/comparisons/${id}`;
        
        const res = await apiRequest('GET', url);
        const cmp = await res.json();
        
        if (cmp?.baselineFileId && cmp?.revisedFileId) {
          setInput({
            baseline: {
              id: cmp.baselineFileId,
              name: cmp?.baselineOriginalName || 'Baseline',
              size: 0,
              type: 'pdf',
              url: `/api/files/${cmp.baselineFileId}/download`,
            },
            revised: {
              id: cmp.revisedFileId,
              name: cmp?.revisedOriginalName || 'Revised',
              size: 0,
              type: 'pdf',
              url: `/api/files/${cmp.revisedFileId}/download`,
            },
          });
        }
        // Parse JSON fields if they came back as strings
        let changesField: any = cmp.changes;
        if (typeof changesField === 'string') {
          try { changesField = JSON.parse(changesField); } catch { /* ignore */ }
        }
        // Parse pageInfo if it came back as a JSON string; support snake_case source
        let pageInfoField: any = (cmp as any).pageInfo ?? (cmp as any).page_info;
        if (typeof pageInfoField === 'string') {
          try { pageInfoField = JSON.parse(pageInfoField); } catch { /* ignore */ }
        }
        // Parse pageMapping if it came back as a JSON string; support snake_case source
        let pageMapping: any = (cmp as any)?.pageMapping ?? (cmp as any)?.page_mapping;
        if (typeof pageMapping === 'string') {
          try { pageMapping = JSON.parse(pageMapping); } catch { /* ignore */ }
        }
        pageMapping = Array.isArray(pageMapping) ? pageMapping : undefined;

        

        // Normalize shapes
        const isStructured = changesField && !Array.isArray(changesField);
        const hasStructuredLists = isStructured && (
          Array.isArray(changesField?.added) || Array.isArray(changesField?.modified) || Array.isArray(changesField?.removed)
        );

        let normalizedChanges: any;
        const looksLikeNewShape = changesField && typeof changesField === 'object' && (
          Array.isArray((changesField as any)?.change_list) || (changesField as any)?.page_summaries
        );
        if (looksLikeNewShape) {
          // Use the new simplified shape as-is
          normalizedChanges = changesField;
        } else if (Array.isArray(changesField)) {
          normalizedChanges = changesField;
        } else if (hasStructuredLists) {
          normalizedChanges = {
            summary: changesField?.summary || cmp?.analysisSummary,
            added: changesField?.added || [],
            modified: changesField?.modified || [],
            removed: changesField?.removed || [],
            artifacts: changesField?.artifacts || [],
            matches: changesField?.matches || [],
            only_in_old: changesField?.only_in_old || [],
            only_in_new: changesField?.only_in_new || [],
          };
        } else {
          const onlyInOld = (changesField?.only_in_old || []) as any[];
          const onlyInNew = (changesField?.only_in_new || []) as any[];
          // use pageMapping delivered alongside comparison
          const matches = ((cmp as any)?.pageMapping || []) as any[];
          const toItem = (val: any, prefix: string, idx: number) => ({
            id: `${prefix}-${idx + 1}`,
            drawingCode: typeof val === 'string' ? val : String(val?.[0] ?? val),
            summary: typeof val === 'string' ? val : JSON.stringify(val),
            detailCount: 0,
          });
          normalizedChanges = {
            summary: cmp?.analysisSummary,
            added: onlyInNew.map((v, i) => toItem(v, 'added', i)),
            removed: onlyInOld.map((v, i) => toItem(v, 'removed', i)),
            modified: matches.map((v, i) => toItem(v, 'modified', i)),
            artifacts: changesField?.artifacts || [],
            matches,
            only_in_old: onlyInOld,
            only_in_new: onlyInNew,
          };
        }

        const derivedFromStructured = {
          added: Array.isArray(normalizedChanges?.added) ? normalizedChanges.added.length : 0,
          modified: Array.isArray(normalizedChanges?.modified) ? normalizedChanges.modified.length : 0,
          removed: Array.isArray(normalizedChanges?.removed) ? normalizedChanges.removed.length : 0,
        };
        let kpis = cmp.kpis || undefined;
        if (pageInfoField && typeof pageInfoField === 'object') {
          kpis = {
            added: typeof pageInfoField.added === 'number' ? pageInfoField.added : undefined,
            modified: typeof pageInfoField.modified === 'number' ? pageInfoField.modified : undefined,
            removed: typeof pageInfoField.removed === 'number' ? pageInfoField.removed : undefined,
          } as any;
        } else if (!kpis || (kpis as any).added === undefined) {
          const mf = (cmp.kpis?.matches_found ?? 0) as number;
          const fo = (cmp.kpis?.failed_overlays ?? 0) as number;
          const so = (cmp.kpis?.successful_overlays ?? 0) as number;
          const legacyPresent = mf + fo + so > 0;
          if (legacyPresent) {
            const changeList: any[] = Array.isArray((normalizedChanges as any)?.change_list) ? (normalizedChanges as any).change_list : [];
            const countBy = (a: string) => changeList.filter((it) => (it?.action || '').toLowerCase() === a).length;
            const addedLen = changeList.length > 0
              ? countBy('added')
              : (Array.isArray((normalizedChanges as any)?.added) ? (normalizedChanges as any).added.length : 0);
            const modifiedLen = changeList.length > 0
              ? countBy('modified')
              : (Array.isArray((normalizedChanges as any)?.modified) ? (normalizedChanges as any).modified.length : mf);
            const removedLen = changeList.length > 0
              ? countBy('removed')
              : (Array.isArray((normalizedChanges as any)?.removed) ? (normalizedChanges as any).removed.length : 0);
            kpis = { added: addedLen, modified: modifiedLen, removed: removedLen } as any;
          } else {
            kpis = derivedFromStructured as any;
          }
        }

        const hasNewChangeList = Array.isArray((normalizedChanges as any)?.change_list) && (normalizedChanges as any).change_list.length > 0;
        const hasChanges = hasNewChangeList
          || (((normalizedChanges?.added?.length || 0) + (normalizedChanges?.modified?.length || 0) + (normalizedChanges?.removed?.length || 0)) > 0)
          || (Array.isArray(normalizedChanges) && normalizedChanges.length > 0);
        const hasMapping = Array.isArray(pageMapping) && pageMapping.length > 0;
        

        // Always update result so mapping becomes available to viewers immediately
        const drawingNum = cmp.drawingNumber || (hasMapping ? String((pageMapping as any[])[0][0] || 'Unknown') : undefined);
        
        const nextResult = {
          id: cmp.id,
          drawingNumber: drawingNum,
          autoDetectedDrawingNumber: !!cmp.autoDetectedDrawingNumber,
          kpis,
          changes: normalizedChanges,
          pageInfo: pageInfoField,
          pageMapping: pageMapping as any,
          // temporary: also store snake_case for any components still reading it
          ...(hasMapping ? { page_mapping: pageMapping as any } : {}),
          isPartial: cmp?.status !== 'completed',
        } as any;
        setResult(nextResult);

        if (Array.isArray(normalizedChanges) && normalizedChanges.length > 0) {
          selectChange(normalizedChanges[0].id);
        }

        if (cmp?.status === 'completed' && hasChanges) {
          try {
            const changesCount = Array.isArray(normalizedChanges)
              ? normalizedChanges.length
              : ((normalizedChanges?.added?.length || 0) + (normalizedChanges?.modified?.length || 0) + (normalizedChanges?.removed?.length || 0));
            const drawingNum = (Array.isArray(pageMapping) && pageMapping.length > 0)
              ? String((pageMapping as any[])[0][0])
              : (cmp?.drawingNumber || undefined);
            const baselineName = (input?.baseline?.name) || cmp?.baselineDisplayName || cmp?.baselineOriginalName || 'Baseline';
            const revisedName = (input?.revised?.name) || cmp?.revisedDisplayName || cmp?.revisedOriginalName || 'Revised';
            await recentService.add({
              id: cmp.id,
              date: (cmp?.createdAt ? new Date(cmp.createdAt).toISOString() : new Date().toISOString()),
              drawingNumber: drawingNum,
              baselineName,
              revisedName,
              changesCount,
            });
          } catch (_) {}
          return; // stop only when completed AND we have changes
        }
        if (cmp?.status === 'failed') {
          setError('Comparison failed. Please try again.');
        }
      } catch (error) {
        
      }
      // schedule next poll if not completed
      pollTimer = window.setTimeout(loadOnce, 5000);
    };
    loadOnce();
    return () => {
      isCancelled = true;
      if (pollTimer) window.clearTimeout(pollTimer);
    };
  }, [id]);

  if (!result) {
    return (
      <div className="space-y-6">
        <div className="bg-white rounded-2xl shadow-card p-6" data-testid="comparison-header">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">Processing Comparison</h1>
              <p className="text-gray-600">This can take a few minutes. We’ll load results automatically.</p>
            </div>
            <Button variant="outline" asChild data-testid="button-back-home">
              <Link to="/">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to Home
              </Link>
            </Button>
          </div>
        </div>
        {/* Show preparing state only until either input or result is present */}
        {!input && !result && (
          <div className="flex items-center justify-center min-h-[50vh]">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
              <p className="text-gray-600">Preparing viewers…</p>
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-2xl shadow-card p-6" data-testid="comparison-header">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Comparison Results</h1>
            <p className="text-gray-600" data-testid="text-file-names">
              {(() => {
                const b = input?.baseline?.name || 'Baseline';
                const r = input?.revised?.name || 'Revised';
                return `${b} vs ${r}`;
              })()}
            </p>
          </div>
          <Button variant="outline" asChild data-testid="button-back-home">
            <Link to="/">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Home
            </Link>
          </Button>
        </div>
        
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <span className="text-sm font-medium text-gray-700">Drawing Number:</span>
            {/* Build codes strictly from page_mapping */}
            {(() => {
              const r: any = result;
              const mapping: any[] = Array.isArray((r as any)?.pageMapping) ? ((r as any).pageMapping as any[]) : [];
              const options = mapping.map((m) => (Array.isArray(m) ? String(m[0]) : '')).filter(Boolean);
              const current = selectedChangeId?.startsWith('page-')
                ? selectedChangeId.replace(/^page-/, '')
                : (options[0] || '');

              return (
                <Select value={current} onValueChange={(val) => selectChange(`page-${val}`)}>
                  <SelectTrigger className="h-8 w-40 text-sm">
                    <SelectValue placeholder="Select drawing" />
                  </SelectTrigger>
                  <SelectContent>
                    {options.map((c) => (
                      <SelectItem key={c} value={c}>{c}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              );
            })()}
            {result.autoDetectedDrawingNumber && (
              <Badge variant="outline" className="text-green-700 border-green-300">
                <CheckCircle className="h-3 w-3 mr-1" />
                Auto-detected from drawing
              </Badge>
            )}
          </div>
        </div>
      </div>

      {/* Unified toolbar */}
      <div className="bg-white rounded-2xl shadow-card p-4 flex items-center justify-between flex-wrap gap-4">
        <ViewModeToggle />
        <ComparisonToolbar />
      </div>

      {/* Viewers */}
      <ComparisonViewers />

      {/* Summary Section - full width */}
      <SummarySection />

      {/* Changes Section */}
      <div className="grid lg:grid-cols-2 gap-6">
        <ChangesList />
        <ChangeDetailsPanel />
      </div>

      {/* Ask About Changes - full width at bottom */}
      <AskPanel />
    </div>
  );
}

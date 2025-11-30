import KpiTile from "@/components/common/KpiTile";
import { useComparisonStore } from "@/features/comparison/state/useComparisonStore";

export default function SummarySection() {
  const { result } = useComparisonStore();

  if (!result) {
    return (
      <div className="bg-white rounded-2xl shadow-card p-6">
        <div className="text-center text-gray-500 py-12">
          No comparison results available
        </div>
      </div>
    );
  }

  // Only use server-provided pageInfo; show '-' if missing
  const counts = (() => {
    const pageInfo = (result as any)?.pageInfo;
    return {
      added: typeof pageInfo?.added === 'number' ? pageInfo.added : undefined,
      modified: typeof pageInfo?.modified === 'number' ? pageInfo.modified : undefined,
      removed: typeof pageInfo?.removed === 'number' ? pageInfo.removed : undefined,
    } as { added?: number; modified?: number; removed?: number };
  })();

  return (
    <div className="bg-white rounded-2xl shadow-card p-6" data-testid="summary-section">
      <h2 className="text-xl font-semibold text-gray-900 mb-6">Summary</h2>
      <div className="mb-6 text-gray-800" data-testid="assistant-summary">
        Changes by type and category
      </div>
      <div className="grid md:grid-cols-3 gap-4 mb-6">
        <KpiTile value={counts.added} label="Added" variant="added" />
        <KpiTile value={counts.modified} label="Modified" variant="modified" />
        <KpiTile value={counts.removed} label="Removed" variant="removed" />
      </div>
      {/* By Category counts derived from change_list */}
      {(() => {
        const ch: any = (result as any)?.changes;
        const list: any[] = Array.isArray(ch?.change_list) ? ch.change_list : [];
        if (list.length === 0) return null;
        const countsByCategory: Record<string, number> = {};
        for (const it of list) {
          const cats: any[] = Array.isArray(it?.categories) ? it.categories : [];
          for (const c of cats) {
            const key = String(c);
            countsByCategory[key] = (countsByCategory[key] || 0) + 1;
          }
        }
        const entries = Object.entries(countsByCategory);
        if (entries.length === 0) return null;
        return (
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-4">By Category</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3" data-testid="category-list">
              {entries.map(([category, count]) => {
                const testId = `category-${category.toLowerCase().replace(/\s+/g, '-')}`;
                return (
                  <div
                    key={category}
                    className="flex items-center justify-between rounded-xl border bg-gray-50 px-4 py-3"
                    data-testid={testId}
                  >
                    <span className="text-sm font-medium text-gray-800">{category}:</span>
                    <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-white border text-[11px] font-semibold text-gray-800">
                      {count}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        );
      })()}
    </div>
  );
}

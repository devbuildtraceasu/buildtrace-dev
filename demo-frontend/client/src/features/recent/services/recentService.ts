import { RecentItem } from "../models";
import { apiRequest } from "@/lib/queryClient";

export interface IRecentService {
  load(): Promise<RecentItem[]>;
  save(items: RecentItem[]): Promise<void>;
  add(item: RecentItem): Promise<void>;
  remove(id: string): Promise<void>;
}

export class RecentService implements IRecentService {
  private storageKey = "buildtrace-recent-comparisons";

  async load(): Promise<RecentItem[]> {
    // Fetch from server comparisons for current user
    try {
      const res = await apiRequest('GET', '/api/comparisons');
      const list = await res.json();
      if (!Array.isArray(list)) return [];
      const items: RecentItem[] = list
        .sort((a: any, b: any) => new Date(b.createdAt || 0).getTime() - new Date(a.createdAt || 0).getTime())
        .map((c: any) => {
          const changes = c?.changes;
          const changesCount = Array.isArray(changes)
            ? changes.length
            : ((changes?.added?.length || 0) + (changes?.modified?.length || 0) + (changes?.removed?.length || 0));
          const pageMapping = (c as any)?.pageMapping || changes?.matches;
          const drawingNum = (Array.isArray(pageMapping) && pageMapping.length > 0)
            ? String(pageMapping[0][0])
            : (c?.drawingNumber || undefined);
          return {
            id: c.id,
            date: c.createdAt || new Date().toISOString(),
            drawingNumber: drawingNum,
            baselineName: c.baselineDisplayName || c.baselineOriginalName || 'Baseline',
            revisedName: c.revisedDisplayName || c.revisedOriginalName || 'Revised',
            changesCount,
          } as RecentItem;
        });
      // Cache locally for quick loads
      await this.save(items);
      return items;
    } catch (_err) {
      // Fallback to local cache if offline
      const stored = localStorage.getItem(this.storageKey);
      return stored ? JSON.parse(stored) : [];
    }
  }

  async save(items: RecentItem[]): Promise<void> {
    localStorage.setItem(this.storageKey, JSON.stringify(items));
  }

  async add(item: RecentItem): Promise<void> {
    // Keep local cache updated; server list is derived from comparisons table
    const items = await this.load();
    const updated = [item, ...items.filter(i => i.id !== item.id)];
    await this.save(updated);
  }

  async remove(id: string): Promise<void> {
    // Deleting a recent item should delete the comparison on the server
    try {
      await apiRequest('DELETE', `/api/comparisons/${id}`);
    } catch {}
    const items = await this.load();
    const updated = items.filter(item => item.id !== id);
    await this.save(updated);
  }
}

export const recentService = new RecentService();

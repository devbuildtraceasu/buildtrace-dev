import { create } from "zustand";
import { RecentItem } from "../models";

interface RecentState {
  items: RecentItem[];
  query: string;
  loading: boolean;
  
  // Actions
  setItems: (items: RecentItem[]) => void;
  setQuery: (query: string) => void;
  addItem: (item: RecentItem) => void;
  removeItem: (id: string) => void;
  setLoading: (loading: boolean) => void;
  getFilteredItems: () => RecentItem[];
}

export const useRecentStore = create<RecentState>((set, get) => ({
  items: [],
  query: "",
  loading: false,

  setItems: (items) => set({ items }),
  setQuery: (query) => set({ query }),
  addItem: (item) => set(state => ({ 
    items: [item, ...state.items] 
  })),
  removeItem: (id) => set(state => ({ 
    items: state.items.filter(item => item.id !== id) 
  })),
  setLoading: (loading) => set({ loading }),
  
  getFilteredItems: () => {
    const { items, query } = get();
    if (!query) return items;
    
    return items.filter(item => 
      item.drawingNumber?.toLowerCase().includes(query.toLowerCase()) ||
      item.baselineName.toLowerCase().includes(query.toLowerCase()) ||
      item.revisedName.toLowerCase().includes(query.toLowerCase())
    );
  },
}));

import { create } from "zustand";
import { ComparisonInput, ComparisonResult, ViewMode } from "../models";

interface ComparisonState {
  input: ComparisonInput | null;
  result: ComparisonResult | null;
  viewMode: ViewMode;
  zoom: number;
  selectedChangeId: string | null;
  loading: boolean;
  error?: string;
  
  // Actions
  setInput: (input: ComparisonInput | null) => void;
  setResult: (result: ComparisonResult | null) => void;
  setViewMode: (mode: ViewMode) => void;
  setZoom: (zoom: number) => void;
  selectChange: (id: string | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | undefined) => void;
  reset: () => void;
}

export const useComparisonStore = create<ComparisonState>((set) => ({
  input: null,
  result: null,
  viewMode: "side-by-side",
  zoom: 100,
  selectedChangeId: null,
  loading: false,
  error: undefined,

  setInput: (input) => set({ input }),
  setResult: (result) => set({ result }),
  setViewMode: (viewMode) => set({ viewMode, zoom: 100 }),
  setZoom: (zoom) => set({ zoom }),
  selectChange: (selectedChangeId) => set({ selectedChangeId }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
  reset: () => set({
    input: null,
    result: null,
    viewMode: "side-by-side",
    zoom: 100,
    selectedChangeId: null,
    loading: false,
    error: undefined,
  }),
}));

import { create } from "zustand";

interface SqlResult {
  data: Record<string, unknown>[];
  total: number;
  error?: string;
  query: string;
}

interface SqlStore {
  isOpen: boolean;
  results: SqlResult | null;
  setResults: (results: SqlResult | null) => void;
  setIsOpen: (isOpen: boolean) => void;
}

export const useSqlStore = create<SqlStore>((set) => ({
  isOpen: false,
  results: null,
  setResults: (results) => set({ results, isOpen: !!results }),
  setIsOpen: (isOpen) => set({ isOpen }),
}));

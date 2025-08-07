import { create } from "zustand";

interface SqlResult {
  data: Record<string, unknown>[];
  total: number;
  columns?: string[];
  error?: string;
  query: string;
  chatId?: string;
}

interface SqlStore {
  isOpen: boolean;
  results: SqlResult | null;
  executedQueries: string[];
  setResults: (results: SqlResult | null) => void;
  setIsOpen: (isOpen: boolean) => void;
  markQueryAsExecuted: (messageId: string, query: string) => boolean;
  resetExecutedQueries: () => void;
}

export const useSqlStore = create<SqlStore>((set, get) => ({
  isOpen: false,
  results: null,
  executedQueries: [],
  setResults: (results) => set({ results, isOpen: !!results }),
  setIsOpen: (isOpen) => set({ isOpen }),
  markQueryAsExecuted: (messageId: string, query: string) => {
    const queryKey = `${messageId}:${query}`;
    const { executedQueries } = get();

    if (executedQueries.includes(queryKey)) {
      return false;
    }

    set((state) => ({
      executedQueries: [...state.executedQueries, queryKey],
    }));
    return true;
  },
  resetExecutedQueries: () => set({ executedQueries: [] }),
}));

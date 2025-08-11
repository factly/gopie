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
  currentPage: number;
  rowsPerPage: number;
  isLoading: boolean;
  onPageChange: ((page: number, limit: number) => void) | null;
  setResults: (results: SqlResult | null) => void;
  setIsOpen: (isOpen: boolean) => void;
  setCurrentPage: (page: number) => void;
  setRowsPerPage: (rows: number) => void;
  setIsLoading: (loading: boolean) => void;
  setOnPageChange: (callback: ((page: number, limit: number) => void) | null) => void;
  markQueryAsExecuted: (messageId: string, query: string) => boolean;
  resetExecutedQueries: () => void;
  resetPagination: () => void;
}

export const useSqlStore = create<SqlStore>((set, get) => ({
  isOpen: false,
  results: null,
  executedQueries: [],
  currentPage: 1,
  rowsPerPage: 20,
  isLoading: false,
  onPageChange: null,
  setResults: (results) => set({ results, isOpen: !!results }),
  setIsOpen: (isOpen) => set({ isOpen }),
  setCurrentPage: (page) => set({ currentPage: page }),
  setRowsPerPage: (rows) => set({ rowsPerPage: rows }),
  setIsLoading: (loading) => set({ isLoading: loading }),
  setOnPageChange: (callback) => set({ onPageChange: callback }),
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
  resetPagination: () => set({ currentPage: 1, rowsPerPage: 20 }),
}));

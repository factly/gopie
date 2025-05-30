import { create } from "zustand";

interface ColumnDescriptionState {
  columnDescriptions: Record<string, string>;
  setColumnDescription: (columnName: string, description: string) => void;
  getColumnDescriptions: () => Record<string, string>;
  clearColumnDescriptions: () => void;
}

export const useColumnDescriptionStore = create<ColumnDescriptionState>()(
  (set, get) => ({
    columnDescriptions: {},
    setColumnDescription: (columnName: string, description: string) =>
      set((state) => ({
        columnDescriptions: {
          ...state.columnDescriptions,
          [columnName]: description,
        },
      })),
    getColumnDescriptions: () => get().columnDescriptions,
    clearColumnDescriptions: () => set({ columnDescriptions: {} }),
  })
);

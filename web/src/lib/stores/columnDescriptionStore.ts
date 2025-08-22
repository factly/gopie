import { create } from "zustand";

interface ColumnDescriptionState {
  columnDescriptions: Record<string, string>;
  setColumnDescription: (columnName: string, description: string) => void;
  getColumnDescriptions: () => Record<string, string>;
  clearColumnDescriptions: () => void;
  updateColumnDescriptionKey: (oldKey: string, newKey: string) => void;
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
    updateColumnDescriptionKey: (oldKey: string, newKey: string) =>
      set((state) => {
        const newDescriptions = { ...state.columnDescriptions };
        if (newDescriptions[oldKey] && oldKey !== newKey) {
          newDescriptions[newKey] = newDescriptions[oldKey];
          delete newDescriptions[oldKey];
        }
        return { columnDescriptions: newDescriptions };
      }),
  })
);

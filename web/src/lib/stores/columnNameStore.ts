import { create } from "zustand";

export interface ColumnNameMapping {
  originalName: string;
  updatedName: string;
  isValid: boolean;
  dataType?: string;
}

interface ColumnNameState {
  projectId: string | null;
  columnMappings: Map<string, ColumnNameMapping>;
  setProjectId: (projectId: string) => void;
  setColumnMappings: (originalNames: string[], columnTypes?: string[]) => void;
  updateColumnName: (originalName: string, updatedName: string) => void;
  resetColumnMappings: () => void;
  getColumnMappings: () => Record<string, string>;
  autoFixAllColumns: () => void;
}

export const validateColumnName = (name: string): boolean => {
  // Rules:
  // 1. Must be in snake_case (lowercase with underscores)
  // 2. Cannot start with a digit
  // 3. No special chars (only a-z, 0-9, and _)
  // 4. Cannot be a single digit
  const snakeCaseRegex = /^[a-z][a-z0-9_]*$/;
  return snakeCaseRegex.test(name) && !/^\d$/.test(name);
};

/**
 * Convert a string to snake_case format for column names
 */
export const toSnakeCase = (name: string): string => {
  // Handle strings starting with numbers by adding prefix
  let result = name;
  if (/^\d/.test(result)) {
    result = "col_" + result;
  }

  // Replace spaces and special characters with underscores
  result = result
    // Convert to lowercase
    .toLowerCase()
    // Replace spaces, hyphens with underscores
    .replace(/[\s-]+/g, "_")
    // Remove any non-alphanumeric characters except underscores
    .replace(/[^a-z0-9_]/g, "")
    // Replace multiple consecutive underscores with a single one
    .replace(/_+/g, "_")
    // Remove trailing underscores
    .replace(/^_+|_+$/g, "");

  // If we end up with an empty string or just a digit, add a prefix
  if (result === "" || /^\d$/.test(result)) {
    result = "column_" + (result || "unknown");
  }

  return result;
};

export const useColumnNameStore = create<ColumnNameState>((set, get) => ({
  projectId: null,
  columnMappings: new Map<string, ColumnNameMapping>(),

  setProjectId: (projectId: string) => set({ projectId }),

  setColumnMappings: (originalNames: string[], columnTypes?: string[]) => {
    const mappings = new Map<string, ColumnNameMapping>();

    originalNames.forEach((name, index) => {
      const isValid = validateColumnName(name);
      const mapping: ColumnNameMapping = {
        originalName: name,
        updatedName: name,
        isValid,
      };
      if (columnTypes && columnTypes[index]) {
        mapping.dataType = columnTypes[index];
      }
      mappings.set(name, mapping);
    });

    set({ columnMappings: mappings });
  },

  updateColumnName: (originalName: string, updatedName: string) => {
    set((state) => {
      const newMappings = new Map(state.columnMappings);
      const currentMapping = newMappings.get(originalName);

      if (currentMapping) {
        const isValid = validateColumnName(updatedName);
        newMappings.set(originalName, {
          ...currentMapping,
          updatedName,
          isValid,
        });
      }

      return { columnMappings: newMappings };
    });
  },

  resetColumnMappings: () => set({ columnMappings: new Map() }),

  getColumnMappings: () => {
    const result: Record<string, string> = {};
    get().columnMappings.forEach((mapping) => {
      result[mapping.originalName] = mapping.updatedName;
    });
    return result;
  },

  autoFixAllColumns: () => {
    set((state) => {
      const newMappings = new Map(state.columnMappings);

      // Process all column mappings
      newMappings.forEach((mapping, key) => {
        // Only fix invalid column names
        if (!mapping.isValid) {
          const fixedName = toSnakeCase(mapping.originalName);
          newMappings.set(key, {
            ...mapping,
            updatedName: fixedName,
            isValid: true, // Should always be valid after fixing
          });
        }
      });

      return { columnMappings: newMappings };
    });
  },
}));

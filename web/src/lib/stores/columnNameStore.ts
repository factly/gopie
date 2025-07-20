import { create } from "zustand";

export interface ColumnNameMapping {
  originalName: string;
  updatedName: string;
  isValid: boolean;
  dataType?: string;
  updatedDataType?: string;
}

interface ColumnNameState {
  projectId: string | null;
  columnMappings: Record<string, ColumnNameMapping>;
  setProjectId: (projectId: string) => void;
  setColumnMappings: (originalNames: string[], columnTypes?: string[]) => void;
  updateColumnName: (originalName: string, updatedName: string) => void;
  updateColumnDataType: (originalName: string, updatedDataType: string) => void;
  resetColumnMappings: () => void;
  getColumnMappings: () => Record<string, string>;
  getColumnDataTypes: () => Record<string, string>;
  autoFixAllColumns: () => void;
  hasDataTypeChanges: () => boolean;
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

// Valid DuckDB data types for columns
export const VALID_DUCK_DB_TYPES = [
  "INTEGER",
  "BIGINT",
  "DOUBLE",
  "FLOAT",
  "VARCHAR",
  "TEXT",
  "BOOLEAN",
  "DATE",
  "TIMESTAMP",
  "DECIMAL",
];

// Validate datatype is a valid DuckDB type
export const validateDataType = (type: string): boolean => {
  return VALID_DUCK_DB_TYPES.includes(type.toUpperCase());
};

export const useColumnNameStore = create<ColumnNameState>((set, get) => ({
  projectId: null,
  columnMappings: {},

  setProjectId: (projectId: string) => set({ projectId }),

  setColumnMappings: (originalNames: string[], columnTypes?: string[]) => {
    const mappings: Record<string, ColumnNameMapping> = {};

    originalNames.forEach((name, index) => {
      const isValid = validateColumnName(name);
      const dataType =
        columnTypes && columnTypes[index] ? columnTypes[index] : undefined;
      const mapping: ColumnNameMapping = {
        originalName: name,
        updatedName: name,
        isValid,
        dataType,
        updatedDataType: dataType,
      };
      mappings[name] = mapping;
    });

    set({ columnMappings: mappings });
  },

  updateColumnName: (originalName: string, updatedName: string) => {
    set((state) => {
      const newMappings = { ...state.columnMappings };
      const currentMapping = newMappings[originalName];

      if (currentMapping) {
        const isValid = validateColumnName(updatedName);
        newMappings[originalName] = {
          ...currentMapping,
          updatedName,
          isValid,
        };
      }

      return { columnMappings: newMappings };
    });
  },

  updateColumnDataType: (originalName: string, updatedDataType: string) => {
    set((state) => {
      const newMappings = { ...state.columnMappings };
      const currentMapping = newMappings[originalName];

      if (currentMapping) {
        newMappings[originalName] = {
          ...currentMapping,
          updatedDataType,
        };
      }

      return { columnMappings: newMappings };
    });
  },

  resetColumnMappings: () => set({ columnMappings: {} }),

  getColumnMappings: () => {
    const result: Record<string, string> = {};
    Object.values(get().columnMappings).forEach((mapping) => {
      result[mapping.originalName] = mapping.updatedName;
    });
    return result;
  },

  getColumnDataTypes: () => {
    const result: Record<string, string> = {};
    Object.values(get().columnMappings).forEach((mapping) => {
      if (mapping.updatedDataType) {
        result[mapping.updatedName] = mapping.updatedDataType;
      }
    });
    return result;
  },

  hasDataTypeChanges: () => {
    const mappings = get().columnMappings;
    return Object.values(mappings).some(
      (mapping) => mapping.dataType !== mapping.updatedDataType
    );
  },

  autoFixAllColumns: () => {
    set((state) => {
      const newMappings = { ...state.columnMappings };

      // Process all column mappings
      Object.entries(newMappings).forEach(([key, mapping]) => {
        // Only fix invalid column names
        if (!mapping.isValid) {
          const fixedName = toSnakeCase(mapping.originalName);
          newMappings[key] = {
            ...mapping,
            updatedName: fixedName,
            isValid: true, // Should always be valid after fixing
          };
        }
      });

      return { columnMappings: newMappings };
    });
  },
}));

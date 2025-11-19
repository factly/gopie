import { ColumnInfo } from './../queries/dataset/get-schema'; // Assuming path is correct
import { ValidationResult } from "@/lib/validation/validate-file";

interface SchemaComparisonResult {
  areMatching: boolean;
  error?: string;
}

/**
 * Compares an existing dataset schema with a newly uploaded file's schema,
 * checking column count, names, order, and exact types.
 * Assumes consistent type representation (e.g., DuckDB on both ends).
 *
 * @param existingSchema - The schema from the API (Array of ColumnInfo).
 * @param newSchema - The schema from DuckDB validation (ValidationResult).
 * @returns An object indicating if schemas match and an error message if they don't.
 */
export function compareSchemas(
  existingSchema: ColumnInfo[],
  newSchema: ValidationResult
): SchemaComparisonResult {
  const newColumnNames = newSchema.columnNames || [];
  const newColumnTypes = newSchema.columnTypes || []; // Get the types inferred by DuckDB client

  // 1. Check for the same number of columns
  if (existingSchema.length !== newColumnNames.length) {
    return {
      areMatching: false,
      error: `Schema mismatch: Expected ${existingSchema.length} columns, but the new file has ${newColumnNames.length}.`,
    };
  }

  // 2. Check for the same column names, order, AND exact types
  for (let i = 0; i < existingSchema.length; i++) {
    const existingColName = existingSchema[i].column_name;
    const newColName = newColumnNames[i];

    // Check Name
    if (existingColName !== newColName) {
      return {
        areMatching: false,
        error: `Schema mismatch at column ${i + 1}: Expected column name "${existingColName}", but found "${newColName}". column names, order and type must be identical.`,
      };
    }

    // Check Type (Exact Match, case-insensitive for robustness)
    const existingType = existingSchema[i].column_type?.toUpperCase(); // Normalize case just in case
    const newType = newColumnTypes[i]?.toUpperCase(); // Normalize case just in case

    if (!existingType || !newType) {
        // Handle cases where type might be missing unexpectedly
        return {
            areMatching: false,
            error: `Schema mismatch at column "${existingColName}" (column ${i + 1}): Could not determine type information for comparison. Existing: ${existingType || 'N/A'}, New: ${newType || 'N/A'}.`,
          };
    }

    if (existingType !== newType) {
      return {
        areMatching: false,
        // Provide the original (non-uppercased) types in the error for clarity
        error: `Schema mismatch at column "${existingColName}" (column ${i + 1}): Expected type "${existingSchema[i].column_type}", but found type "${newColumnTypes[i]}".`,
      };
    }
  }

  // If all checks pass
  return { areMatching: true };
}
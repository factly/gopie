import * as duckdb from "@duckdb/duckdb-wasm";

export interface ValidationResult {
  isValid: boolean;
  columnNames?: string[];
  columnTypes?: string[];
  columnCount?: number;
  previewRowCount?: number;
  previewData?: unknown[][];
  error?: string;
  columnMappings?: Record<string, string>;
}

/**
 * Validates a CSV file using DuckDB WebAssembly
 * @param db The DuckDB instance
 * @param fileArrayBuffer The file content as ArrayBuffer
 * @param fileSize The file size in bytes
 * @returns Validation result with error or success information
 */
export async function validateCsvWithDuckDb(
  db: duckdb.AsyncDuckDB,
  fileArrayBuffer: ArrayBuffer,
  fileSize: number
): Promise<ValidationResult> {
  // Skip validation for files larger than 1GB
  const ONE_GB = 1000 * 1000 * 1000;
  if (fileSize > ONE_GB) {
    return {
      isValid: true,
      error:
        "File too large for browser validation, will be uploaded and validated on the server",
    };
  }

  // Create a connection to DuckDB
  const conn = await db.connect();

  try {
    // Create virtual filename for the CSV
    const virtualFileName = `temp_file_${Date.now()}.csv`;

    // Register the file buffer with DuckDB
    await db.registerFileBuffer(
      virtualFileName,
      new Uint8Array(fileArrayBuffer)
    );

    try {
      // First try to read the CSV with auto-detection to check for parsing errors
      const validationResults = await conn.query(`
        SELECT * FROM read_csv_auto('${virtualFileName}', header=true)
        LIMIT 5
      `);

      // Check if we got valid results
      if (!validationResults) {
        throw new Error("Failed to read CSV file");
      }

      // Get column info and row count for validation message
      const columnCount = validationResults.schema.fields.length;
      const previewRowCount = validationResults.numRows;
      const dataPreview = validationResults.toArray() as unknown[][];
      const columnNames = validationResults.schema.fields.map((f) => f.name);
      const columnTypes = validationResults.schema.fields.map((f) =>
        f.type.toString()
      );

      // Now try creating a table from the validated CSV to catch any deeper issues
      const tempTableName = `temp_validate_${Date.now()}`;
      await conn.query(`
        CREATE TABLE ${tempTableName} AS 
        SELECT * FROM read_csv_auto('${virtualFileName}', header=true)
      `);

      // Check table creation succeeded
      await conn.query(`SELECT * FROM ${tempTableName} LIMIT 1`);

      // Clean up the temporary table
      await conn.query(`DROP TABLE IF EXISTS ${tempTableName}`);

      // Close the connection
      await conn.close();

      return {
        isValid: true,
        columnNames,
        columnTypes,
        columnCount,
        previewRowCount,
        previewData: dataPreview,
      };
    } catch (csvError) {
      throw new Error(`CSV parsing error: ${(csvError as Error).message}`);
    }
  } catch (error) {
    // Close the connection on error
    await conn.close();

    return {
      isValid: false,
      error: `CSV validation failed: ${(error as Error).message}`,
    };
  }
}

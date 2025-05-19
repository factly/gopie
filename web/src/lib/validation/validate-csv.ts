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
 * Validates a CSV file using DuckDB WASM in the browser
 */
export async function validateCsvWithDuckDb(
  db: duckdb.AsyncDuckDB,
  fileArrayBuffer: ArrayBuffer,
  fileSize: number
): Promise<ValidationResult> {
  // We'll create a virtual file name for the CSV
  const virtualFileName = `temp_${Date.now()}.csv`;
  const conn = await db.connect();

  try {
    try {
      // If file is too large (>1GB), we'll do basic validation only
      if (fileSize > 1024 * 1024 * 1024) {
        await conn.close();
        return {
          isValid: true,
          error:
            "File is larger than 1GB. Only basic validation performed, full validation will be done on the server.",
        };
      }

      // Register the file buffer with DuckDB
      await db.registerFileBuffer(
        virtualFileName,
        new Uint8Array(fileArrayBuffer)
      );

      // First create a temp table from the CSV
      const tempTableName = `temp_validate_${Date.now()}`;
      await conn.query(`
        CREATE TABLE ${tempTableName} AS 
        SELECT * FROM read_csv_auto('${virtualFileName}', header=true)
      `);

      // Now get column info from the created table
      const result = await conn.query(`
        SELECT 
          column_name, 
          data_type as column_type
        FROM 
          information_schema.columns
        WHERE 
          table_name = '${tempTableName}'
      `);

      const columnNames: string[] = [];
      const columnTypes: string[] = [];
      const schema = result.toArray().map((row) => ({
        name: row.column_name.toString(),
        type: row.column_type.toString(),
      }));

      schema.forEach((col) => {
        columnNames.push(col.name);
        columnTypes.push(col.type);
      });

      // Get preview data (first 10 rows)
      const previewRowCount = 10;
      const previewQuery = await conn.query(`
        SELECT * FROM ${tempTableName} 
        LIMIT ${previewRowCount}
      `);

      const dataPreview = previewQuery.toArray();
      const columnCount = columnNames.length;

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

/**
 * Converts a CSV file with the specified column types using DuckDB
 * @param db DuckDB instance
 * @param fileArrayBuffer Original CSV file buffer
 * @param columnMappings Column name mappings (original to updated)
 * @param columnTypes Column type mappings (updated name to type)
 * @returns ArrayBuffer of the converted CSV file
 */
export async function convertCsvWithTypes(
  db: duckdb.AsyncDuckDB,
  fileArrayBuffer: ArrayBuffer,
  columnMappings: Record<string, string>,
  columnTypes: Record<string, string>
): Promise<ArrayBuffer> {
  // Create virtual file names
  const sourceFileName = `source_${Date.now()}.csv`;
  const destFileName = `converted_${Date.now()}.csv`;
  const conn = await db.connect();

  try {
    // Register the file buffer with DuckDB
    await db.registerFileBuffer(
      sourceFileName,
      new Uint8Array(fileArrayBuffer)
    );

    // Create a temporary table from the CSV
    const tempTableName = `temp_convert_${Date.now()}`;
    await conn.query(`
      CREATE TABLE ${tempTableName} AS 
      SELECT * FROM read_csv_auto('${sourceFileName}', header=true)
    `);

    // Build a SQL statement to create a new table with the desired column types
    let createCastTableSQL = `CREATE TABLE ${tempTableName}_cast AS SELECT `;
    const castParts: string[] = [];

    // For each column in our mapping, create a cast expression
    for (const originalCol in columnMappings) {
      const updatedCol = columnMappings[originalCol];
      // Check if this column has a specific type defined
      if (columnTypes[updatedCol]) {
        // Cast the column to the desired type but preserve the original column name
        castParts.push(
          `CAST("${originalCol}" AS ${columnTypes[updatedCol]}) AS "${originalCol}"`
        );
      } else {
        // Keep the original column type and name
        castParts.push(`"${originalCol}" AS "${originalCol}"`);
      }
    }

    // Complete the SQL statement
    createCastTableSQL += castParts.join(", ");
    createCastTableSQL += ` FROM ${tempTableName}`;

    // Execute the SQL to create a new table with the casted columns
    await conn.query(createCastTableSQL);

    // Write the results to a temporary buffer
    await conn.query(`
      COPY (SELECT * FROM ${tempTableName}_cast) TO '${destFileName}' (FORMAT CSV, HEADER)
    `);

    // Get the converted CSV data
    const convertedCsvBuffer = await db.copyFileToBuffer(destFileName);

    // Clean up temporary tables
    await conn.query(`DROP TABLE IF EXISTS ${tempTableName}`);
    await conn.query(`DROP TABLE IF EXISTS ${tempTableName}_cast`);

    // Close the connection
    await conn.close();

    // Create a new ArrayBuffer from the buffer data
    const buffer = convertedCsvBuffer.buffer;
    const newBuffer = new Uint8Array(buffer).buffer as ArrayBuffer;
    return newBuffer;
  } catch (error) {
    // Close the connection on error
    await conn.close();
    throw new Error(`CSV conversion failed: ${(error as Error).message}`);
  }
}

import * as duckdb from "@duckdb/duckdb-wasm";
import * as XLSX from "xlsx";

export type SupportedFileFormat =
  | "csv"
  | "parquet"
  | "json"
  | "excel"
  | "duckdb";

export interface ValidationResult {
  isValid: boolean;
  format: SupportedFileFormat;
  columnNames?: string[];
  columnTypes?: string[];
  columnCount?: number;
  previewRowCount?: number;
  previewData?: unknown[][];
  error?: string;
  columnMappings?: Record<string, string>;
  tables?: string[]; // For DuckDB files that may contain multiple tables
}

export interface FileFormatInfo {
  format: SupportedFileFormat;
  extensions: string[];
  mimeTypes: string[];
  duckdbFunction: string;
  requiresExtension?: string;
}

// File format configurations
export const SUPPORTED_FORMATS: Record<SupportedFileFormat, FileFormatInfo> = {
  csv: {
    format: "csv",
    extensions: [".csv", ".tsv", ".txt"],
    mimeTypes: ["text/csv", "text/tab-separated-values", "text/plain"],
    duckdbFunction: "read_csv_auto",
  },
  parquet: {
    format: "parquet",
    extensions: [".parquet", ".parq"],
    mimeTypes: ["application/octet-stream"],
    duckdbFunction: "read_parquet",
  },
  json: {
    format: "json",
    extensions: [".json", ".jsonl", ".ndjson"],
    mimeTypes: ["application/json", "text/json"],
    duckdbFunction: "read_json_auto",
  },
  excel: {
    format: "excel",
    extensions: [".xlsx", ".xls"], // Support both .xlsx and .xls via SheetJS
    mimeTypes: [
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      "application/vnd.ms-excel",
    ],
    duckdbFunction: "read_csv_auto", // Will convert to CSV first
    requiresExtension: undefined, // No DuckDB extension needed
  },
  duckdb: {
    format: "duckdb",
    extensions: [".duckdb", ".db", ".ddb"],
    mimeTypes: ["application/octet-stream"],
    duckdbFunction: "ATTACH",
  },
};

/**
 * Detects file format based on file name and MIME type
 */
export function detectFileFormat(
  fileName: string,
  mimeType?: string
): SupportedFileFormat | null {
  const lowercaseFileName = fileName.toLowerCase();

  // Check by extension first
  for (const formatInfo of Object.values(SUPPORTED_FORMATS)) {
    if (formatInfo.extensions.some((ext) => lowercaseFileName.endsWith(ext))) {
      return formatInfo.format;
    }
  }

  // Fallback to MIME type
  if (mimeType) {
    for (const formatInfo of Object.values(SUPPORTED_FORMATS)) {
      if (formatInfo.mimeTypes.includes(mimeType)) {
        return formatInfo.format;
      }
    }
  }

  return null;
}

/**
 * Gets all supported file extensions for Uppy restrictions
 */
export function getSupportedFileExtensions(): string[] {
  return Object.values(SUPPORTED_FORMATS).flatMap(
    (format) => format.extensions
  );
}

/**
 * Gets all supported MIME types for Uppy restrictions
 */
export function getSupportedMimeTypes(): string[] {
  return [
    ...new Set(
      Object.values(SUPPORTED_FORMATS).flatMap((format) => format.mimeTypes)
    ),
  ];
}

/**
 * Validates a file using DuckDB WASM in the browser
 */
export async function validateFileWithDuckDb(
  db: duckdb.AsyncDuckDB,
  fileArrayBuffer: ArrayBuffer,
  fileName: string,
  fileSize: number,
  mimeType?: string
): Promise<ValidationResult> {
  const format = detectFileFormat(fileName, mimeType);

  if (!format) {
    return {
      isValid: false,
      format: "csv", // fallback
      error: `Unsupported file format. Supported formats: ${Object.keys(
        SUPPORTED_FORMATS
      ).join(", ")}`,
    };
  }

  const formatInfo = SUPPORTED_FORMATS[format];

  // Check if extension is required and install it
  if (formatInfo.requiresExtension) {
    // Extension loading will be handled in the specific validation function
    // This prevents premature failures and allows for better error handling
    console.log(`File format ${format} requires ${formatInfo.requiresExtension} extension - will attempt to load during validation`);
  }

  // Handle large files
  if (fileSize > 1024 * 1024 * 1024) {
    return {
      isValid: true,
      format,
      error: `File is larger than 1GB. Only basic validation performed, full validation will be done on the server.`,
    };
  }

  // Route to specific validation function
  switch (format) {
    case "csv":
      return validateCsvFile(db, fileArrayBuffer);
    case "parquet":
      return validateParquetFile(db, fileArrayBuffer);
    case "json":
      return validateJsonFile(db, fileArrayBuffer);
    case "excel":
      return validateExcelFile(db, fileArrayBuffer);
    case "duckdb":
      return validateDuckDbFile(db, fileArrayBuffer);
    default:
      return {
        isValid: false,
        format,
        error: `Validation not implemented for ${format} format`,
      };
  }
}

/**
 * Validates a CSV file
 */
async function validateCsvFile(
  db: duckdb.AsyncDuckDB,
  fileArrayBuffer: ArrayBuffer
): Promise<ValidationResult> {
  const virtualFileName = `temp_${Date.now()}.csv`;
  const conn = await db.connect();

  try {
    await db.registerFileBuffer(
      virtualFileName,
      new Uint8Array(fileArrayBuffer)
    );

    const tempTableName = `temp_validate_${Date.now()}`;
    await conn.query(`
      CREATE TABLE ${tempTableName} AS 
      SELECT * FROM read_csv_auto('${virtualFileName}', header=true)
    `);

    const result = await validateTableStructure(conn, tempTableName);
    await conn.query(`DROP TABLE IF EXISTS ${tempTableName}`);
    await conn.close();

    return {
      ...result,
      format: "csv",
    };
  } catch (error) {
    await conn.close();
    return {
      isValid: false,
      format: "csv",
      error: `CSV validation failed: ${(error as Error).message}`,
    };
  }
}

/**
 * Validates a Parquet file
 */
async function validateParquetFile(
  db: duckdb.AsyncDuckDB,
  fileArrayBuffer: ArrayBuffer
): Promise<ValidationResult> {
  const virtualFileName = `temp_${Date.now()}.parquet`;
  const conn = await db.connect();

  try {
    await db.registerFileBuffer(
      virtualFileName,
      new Uint8Array(fileArrayBuffer)
    );

    const tempTableName = `temp_validate_${Date.now()}`;
    await conn.query(`
      CREATE TABLE ${tempTableName} AS 
      SELECT * FROM read_parquet('${virtualFileName}')
    `);

    const result = await validateTableStructure(conn, tempTableName);
    await conn.query(`DROP TABLE IF EXISTS ${tempTableName}`);
    await conn.close();

    return {
      ...result,
      format: "parquet",
    };
  } catch (error) {
    await conn.close();
    return {
      isValid: false,
      format: "parquet",
      error: `Parquet validation failed: ${(error as Error).message}`,
    };
  }
}

/**
 * Validates a JSON file
 */
async function validateJsonFile(
  db: duckdb.AsyncDuckDB,
  fileArrayBuffer: ArrayBuffer
): Promise<ValidationResult> {
  const virtualFileName = `temp_${Date.now()}.json`;
  const conn = await db.connect();

  try {
    await db.registerFileBuffer(
      virtualFileName,
      new Uint8Array(fileArrayBuffer)
    );

    const tempTableName = `temp_validate_${Date.now()}`;

    // Try different JSON formats
    let createQuery = "";
    try {
      // Try auto-detection first
      createQuery = `CREATE TABLE ${tempTableName} AS SELECT * FROM read_json_auto('${virtualFileName}')`;
      await conn.query(createQuery);
    } catch {
      try {
        // Try newline-delimited JSON
        createQuery = `CREATE TABLE ${tempTableName} AS SELECT * FROM read_json_auto('${virtualFileName}', format='newline_delimited')`;
        await conn.query(createQuery);
      } catch {
        // Try array format
        createQuery = `CREATE TABLE ${tempTableName} AS SELECT * FROM read_json_auto('${virtualFileName}', format='array')`;
        await conn.query(createQuery);
      }
    }

    const result = await validateTableStructure(conn, tempTableName);
    await conn.query(`DROP TABLE IF EXISTS ${tempTableName}`);
    await conn.close();

    return {
      ...result,
      format: "json",
    };
  } catch (error) {
    await conn.close();
    return {
      isValid: false,
      format: "json",
      error: `JSON validation failed: ${
        (error as Error).message
      }. Supported formats: auto-detect, newline-delimited, array`,
    };
  }
}

/**
 * Validates an Excel file by converting it to CSV first using SheetJS
 */
async function validateExcelFile(
  db: duckdb.AsyncDuckDB,
  fileArrayBuffer: ArrayBuffer
): Promise<ValidationResult> {
  try {
    console.log(`Converting Excel file to CSV (${fileArrayBuffer.byteLength} bytes)`);
    
    // Convert Excel to CSV using SheetJS
    const workbook = XLSX.read(fileArrayBuffer, { type: 'array' });
    
    // Get the first sheet
    const firstSheetName = workbook.SheetNames[0];
    if (!firstSheetName) {
      return {
        isValid: false,
        format: "excel",
        error: "Excel file contains no sheets or is corrupted.",
      };
    }
    
    const worksheet = workbook.Sheets[firstSheetName];
    const csvData = XLSX.utils.sheet_to_csv(worksheet);
    
    if (!csvData.trim()) {
      return {
        isValid: false,
        format: "excel",
        error: "Excel file appears to be empty or contains no data.",
      };
    }
    
    console.log(`Excel to CSV conversion successful (${csvData.length} characters)`);
    
    // Convert CSV string to ArrayBuffer
    const csvBuffer = new TextEncoder().encode(csvData);
    
    // Use the existing CSV validation function
    const result = await validateCsvFile(db, csvBuffer.buffer);
    
    // Return result with Excel format but CSV validation
    return {
      ...result,
      format: "excel",
      error: result.error ? `Excel file processed: ${result.error}` : undefined,
    };
    
  } catch (error) {
    const errorMessage = (error as Error).message;
    
    // Handle specific SheetJS errors
    if (errorMessage.includes("Unsupported file")) {
      return {
        isValid: false,
        format: "excel",
        error: "Unsupported Excel file format. Please ensure the file is a valid .xlsx or .xls file.",
      };
    }
    
    if (errorMessage.includes("End of data")) {
      return {
        isValid: false,
        format: "excel",
        error: "Excel file appears to be corrupted or incomplete.",
      };
    }
    
    return {
      isValid: false,
      format: "excel",
      error: `Excel file processing failed: ${errorMessage}. Please ensure the file is a valid Excel file.`,
    };
  }
}

/**
 * Validates a DuckDB file
 */
async function validateDuckDbFile(
  db: duckdb.AsyncDuckDB,
  fileArrayBuffer: ArrayBuffer
): Promise<ValidationResult> {
  const virtualFileName = `temp_${Date.now()}.duckdb`;
  const conn = await db.connect();

  try {
    await db.registerFileBuffer(
      virtualFileName,
      new Uint8Array(fileArrayBuffer)
    );

    // Attach the database
    await conn.query(`ATTACH '${virtualFileName}' AS temp_db`);

    // Get list of tables
    const tablesResult = await conn.query(`
      SELECT table_name 
      FROM temp_db.information_schema.tables 
      WHERE table_schema = 'main'
    `);

    const tables = tablesResult
      .toArray()
      .map((row) => row.table_name.toString());

    if (tables.length === 0) {
      await conn.query(`DETACH temp_db`);
      await conn.close();
      return {
        isValid: false,
        format: "duckdb",
        error: "No tables found in DuckDB file",
      };
    }

    // For now, validate the first table
    const firstTable = tables[0];
    const result = await validateTableStructure(conn, `temp_db.${firstTable}`);

    await conn.query(`DETACH temp_db`);
    await conn.close();

    return {
      ...result,
      format: "duckdb",
      tables,
      error:
        tables.length > 1
          ? `DuckDB file contains ${tables.length} tables. Currently showing structure of: ${firstTable}`
          : undefined,
    };
  } catch (error) {
    await conn.close();
    return {
      isValid: false,
      format: "duckdb",
      error: `DuckDB validation failed: ${(error as Error).message}`,
    };
  }
}

/**
 * Common function to validate table structure and get preview data
 */
async function validateTableStructure(
  conn: duckdb.AsyncDuckDBConnection,
  tableName: string
) {
  // Get column info
  const result = await conn.query(`
    SELECT 
      column_name, 
      data_type as column_type
    FROM 
      information_schema.columns
    WHERE 
      table_name = '${tableName.split(".").pop()}' 
    ORDER BY ordinal_position
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
    SELECT * FROM ${tableName} 
    LIMIT ${previewRowCount}
  `);

  const dataPreview = previewQuery.toArray();
  const columnCount = columnNames.length;

  return {
    isValid: true,
    columnNames,
    columnTypes,
    columnCount,
    previewRowCount,
    previewData: dataPreview,
  };
}

/**
 * Converts a file with the specified column types using DuckDB
 * Currently only supports CSV conversion, others will pass through unchanged
 */
export async function convertFileWithTypes(
  db: duckdb.AsyncDuckDB,
  fileArrayBuffer: ArrayBuffer,
  fileName: string,
  columnMappings: Record<string, string>,
  columnTypes: Record<string, string>
): Promise<ArrayBuffer> {
  const format = detectFileFormat(fileName);

  // Only CSV supports conversion currently
  if (format !== "csv") {
    return fileArrayBuffer; // Return original buffer for other formats
  }

  return convertCsvWithTypes(db, fileArrayBuffer, columnMappings, columnTypes);
}

/**
 * Converts a CSV file with the specified column types using DuckDB
 */
async function convertCsvWithTypes(
  db: duckdb.AsyncDuckDB,
  fileArrayBuffer: ArrayBuffer,
  columnMappings: Record<string, string>,
  columnTypes: Record<string, string>
): Promise<ArrayBuffer> {
  const sourceFileName = `source_${Date.now()}.csv`;
  const destFileName = `converted_${Date.now()}.csv`;
  const conn = await db.connect();

  try {
    await db.registerFileBuffer(
      sourceFileName,
      new Uint8Array(fileArrayBuffer)
    );

    const tempTableName = `temp_convert_${Date.now()}`;
    await conn.query(`
      CREATE TABLE ${tempTableName} AS 
      SELECT * FROM read_csv_auto('${sourceFileName}', header=true)
    `);

    let createCastTableSQL = `CREATE TABLE ${tempTableName}_cast AS SELECT `;
    const castParts: string[] = [];

    for (const originalCol in columnMappings) {
      const updatedCol = columnMappings[originalCol];
      if (columnTypes[updatedCol]) {
        castParts.push(
          `CAST("${originalCol}" AS ${columnTypes[updatedCol]}) AS "${originalCol}"`
        );
      } else {
        castParts.push(`"${originalCol}" AS "${originalCol}"`);
      }
    }

    createCastTableSQL += castParts.join(", ");
    createCastTableSQL += ` FROM ${tempTableName}`;

    await conn.query(createCastTableSQL);

    await conn.query(`
      COPY (SELECT * FROM ${tempTableName}_cast) TO '${destFileName}' (FORMAT CSV, HEADER)
    `);

    const convertedCsvBuffer = await db.copyFileToBuffer(destFileName);

    await conn.query(`DROP TABLE IF EXISTS ${tempTableName}`);
    await conn.query(`DROP TABLE IF EXISTS ${tempTableName}_cast`);
    await conn.close();

    const buffer = convertedCsvBuffer.buffer;
    const newBuffer = new Uint8Array(buffer).buffer as ArrayBuffer;
    return newBuffer;
  } catch (error) {
    await conn.close();
    throw new Error(`CSV conversion failed: ${(error as Error).message}`);
  }
}

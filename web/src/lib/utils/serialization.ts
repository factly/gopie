/**
 * Utility functions for data serialization
 */

/**
 * Sanitizes a value for JSON serialization by converting special types
 * that cannot be directly serialized into safe representations.
 * 
 * @param value - The value to sanitize
 * @returns A JSON-serializable value
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function sanitizeForSerialization(value: any): any {
  // Handle BigInt - convert to string to preserve precision
  if (typeof value === 'bigint') {
    return value.toString();
  }
  
  // Handle Date objects - convert to ISO string
  if (value instanceof Date) {
    return value.toISOString();
  }
  
  // Handle undefined - convert to null for JSON compatibility
  if (typeof value === 'undefined') {
    return null;
  }
  
  // Handle functions - skip them in serialization
  if (typeof value === 'function') {
    return null;
  }
  
  // Handle symbols - convert to string representation
  if (typeof value === 'symbol') {
    return value.toString();
  }
  
  // Handle infinity values - convert to null
  if (value === Infinity || value === -Infinity) {
    return null;
  }
  
  // Handle NaN - convert to null
  if (Number.isNaN(value)) {
    return null;
  }
  
  // Handle arrays recursively
  if (Array.isArray(value)) {
    return value.map(sanitizeForSerialization);
  }
  
  // Handle objects recursively (but not null, Date, or other special objects)
  if (value !== null && typeof value === 'object' && !(value instanceof Date)) {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const sanitized: Record<string, any> = {};
    for (const [key, val] of Object.entries(value)) {
      sanitized[key] = sanitizeForSerialization(val);
    }
    return sanitized;
  }
  
  // Return the value as-is for all other types (string, number, boolean, null)
  return value;
}

/**
 * Sanitizes dataset rows for serialization, handling both array and object row formats.
 * 
 * @param rows - The dataset rows to sanitize
 * @returns Sanitized rows safe for JSON serialization
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function sanitizeDatasetRows(rows: any[]): any[][] {
  if (!Array.isArray(rows)) {
    return [];
  }
  
  return rows.map((row) => {
    // Handle array format: ["value1", "value2"]
    if (Array.isArray(row)) {
      return row.map(sanitizeForSerialization);
    }
    
    // Handle object format: {col1: "value1", col2: "value2"}
    if (typeof row === 'object' && row !== null) {
      // Convert object to array of values and sanitize each
      return Object.values(row).map(sanitizeForSerialization);
    }
    
    // Fallback for unexpected formats - wrap in array
    return [sanitizeForSerialization(row)];
  });
}

/**
 * Custom JSON.stringify replacer function for handling special types
 * Can be used directly with JSON.stringify as the second parameter
 * 
 * @param key - The object key being stringified
 * @param value - The value to stringify
 * @returns A JSON-safe value
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function jsonReplacer(key: string, value: any): any {
  return sanitizeForSerialization(value);
}
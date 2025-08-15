export interface SqlErrorDetails {
  message: string;
  details?: string;
  suggestion?: string;
  code?: number;
}

/**
 * Categorizes SQL errors and provides helpful suggestions for users
 * @param errorData - The error data from the server
 * @returns SqlErrorDetails with categorized error information and suggestions
 */
export function categorizeSqlError(errorData: unknown): SqlErrorDetails {
  const errorDetails: SqlErrorDetails = {
    message: 'An error occurred',
    details: undefined,
    suggestion: undefined,
    code: undefined,
  };

  // Type guard to check if errorData is an object
  if (errorData && typeof errorData === 'object') {
    const data = errorData as Record<string, unknown>;
    
    // Extract meaningful error information from server response
    if (data.message && typeof data.message === 'string') {
      errorDetails.message = data.message;
    }
    
    if (data.error) {
      // If error is a string, use it as details
      if (typeof data.error === 'string') {
        errorDetails.details = data.error;
      }
    }
    
    if (data.code && typeof data.code === 'number') {
      errorDetails.code = data.code;
    }
  }

  // Add suggestions based on error type
  if (errorDetails.code === 404 || errorDetails.message.includes("dataset does not exist")) {
    errorDetails.suggestion = "Check that the table name is correct and that the dataset has been properly loaded.";
  } else if (errorDetails.code === 403 || errorDetails.message.includes("Only SELECT statements") || errorDetails.message.includes("only read-only queries")) {
    errorDetails.suggestion = "Only read-only queries are allowed (SELECT, WITH, DESCRIBE, SUMMARIZE). Please modify your query to retrieve data without making changes.";
  } else if (errorDetails.details?.includes("Syntax Error") || errorDetails.details?.includes("Parser Error")) {
    errorDetails.suggestion = "Check your SQL syntax. Common issues include missing commas, unclosed quotes, or incorrect keywords.";
  } else if (errorDetails.details?.includes("column") && errorDetails.details?.includes("not found")) {
    errorDetails.suggestion = "The column name might be incorrect. Check the available columns in the schema.";
  } else if (errorDetails.details?.includes("Binder Error")) {
    errorDetails.suggestion = "There's an issue with table or column references. Verify that all referenced tables and columns exist.";
  }

  return errorDetails;
}

/**
 * Formats an SQL error object into SqlErrorDetails
 * @param error - The error object (can be Error instance or server error response)
 * @returns SqlErrorDetails with formatted error information
 */
export function parseSqlError(error: unknown): SqlErrorDetails {
  if (error && typeof error === 'object' && 'errorData' in error) {
    return categorizeSqlError(error.errorData);
  } else if (error instanceof Error) {
    return {
      message: error.message,
      details: undefined,
      suggestion: undefined,
      code: undefined,
    };
  } else {
    return {
      message: 'An unknown error occurred',
      details: undefined,
      suggestion: undefined,
      code: undefined,
    };
  }
}
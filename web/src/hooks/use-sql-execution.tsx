import { useCallback, useEffect, useState } from "react";
import { useSqlStore } from "@/lib/stores/sql-store";
import { useResultsPanelStore } from "@/lib/stores/results-panel-store";

interface SqlExecutionError extends Error {
  details?: {
    message: string;
    code?: string;
    sqlState?: string;
  };
}

interface SqlMutationResult {
  data?: unknown[];
  count?: number;
  total?: number;
}

interface SqlMutation {
  mutateAsync: (params: {
    query: string;
    limit: number;
    offset: number;
  }) => Promise<SqlMutationResult>;
}

interface UseSqlExecutionOptions {
  messageId: string;
  role: string;
  isLatest: boolean;
  isLoading?: boolean;
  sqlQueries: string[];
  executeSqlMutation: SqlMutation;
}

export function useSqlExecution({
  messageId,
  role,
  isLatest,
  isLoading = false,
  sqlQueries,
  executeSqlMutation,
}: UseSqlExecutionOptions) {
  const { markQueryAsExecuted, resetPagination, setOnPageChange } = useSqlStore();
  const { setActiveTab } = useResultsPanelStore();
  const [results, setResults] = useState<SqlMutationResult | null>(null);
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionError, setExecutionError] = useState<string | null>(null);

  // Handle query execution
  const handleRunQuery = useCallback(
    async (query: string, page: number = 1, limit: number = 20) => {
      setResults(null);
      setIsExecuting(true);
      setExecutionError(null);
      const offset = (page - 1) * limit;

      try {
        const result = await executeSqlMutation.mutateAsync({
          query,
          limit,
          offset,
        });
        
        setResults({
          data: result.data ?? [],
          total: result.count ?? result.data?.length ?? 0,
        });

        // Auto-switch to SQL tab when results are available
        if (result.data && result.data.length > 0) {
          setActiveTab("sql");
        }
      } catch (error) {
        console.error("Error executing SQL:", error);
        const sqlError = error as SqlExecutionError;
        setExecutionError(
          sqlError.details?.message || 
          sqlError.message || 
          "Failed to execute query"
        );
      } finally {
        setIsExecuting(false);
      }
    },
    [executeSqlMutation, setActiveTab]
  );

  // Execute SQL queries automatically when conditions are met
  useEffect(() => {
    // Skip if not an assistant message or not the latest
    if ((role !== "assistant" && role !== "ai") || !isLatest) {
      return;
    }

    // Skip if still loading
    if (isLoading) {
      return;
    }

    // Get the last SQL query to execute
    const sqlToExecute = sqlQueries.length > 0 
      ? sqlQueries[sqlQueries.length - 1] 
      : null;

    if (sqlToExecute) {
      const shouldExecute = markQueryAsExecuted(messageId, sqlToExecute);
      
      if (shouldExecute) {
        // Reset pagination for new query
        resetPagination();

        // Set up the page change callback
        setOnPageChange((page: number, limit: number) => {
          handleRunQuery(sqlToExecute, page, limit);
        });

        // Execute query asynchronously without blocking UI
        queueMicrotask(() => {
          handleRunQuery(sqlToExecute, 1, 20);
        });
      }
    }
  }, [
    role,
    isLatest,
    isLoading,
    sqlQueries,
    messageId,
    handleRunQuery,
    markQueryAsExecuted,
    resetPagination,
    setOnPageChange,
  ]);

  return {
    results,
    isExecuting,
    executionError,
    handleRunQuery,
  };
}
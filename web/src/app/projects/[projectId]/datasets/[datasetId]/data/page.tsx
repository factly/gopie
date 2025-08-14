"use client";

import "regenerator-runtime/runtime";
import * as React from "react";
import { motion } from "framer-motion";
import { useDatasetSql } from "@/lib/mutations/dataset/sql";
import { Button } from "@/components/ui/button";
import { PlayIcon, Loader2, Database, Lightbulb, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";
import { ResultsTable } from "@/components/dataset/sql/results-table";
import { Textarea } from "@/components/ui/textarea";
import { useNl2Sql } from "@/lib/mutations/dataset/nl2sql";
import { SqlEditor } from "@/components/dataset/sql/sql-editor";
import { useDataset } from "@/lib/queries/dataset/get-dataset";
import { format } from "sql-formatter";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

import { useSidebar } from "@/components/ui/sidebar";

declare global {
  interface Window {
    require: ((
      deps: string[],
      callback: (...args: unknown[]) => void
    ) => void) & {
      config: (config: { paths: Record<string, string> }) => void;
    };
  }
}

const pageVariants = {
  initial: { opacity: 0 },
  animate: {
    opacity: 1,
    transition: { duration: 0.3 },
  },
};

const fadeInVariants = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  exit: { opacity: 0 },
  transition: { duration: 0.2 },
};

interface ErrorDetails {
  message: string;
  details?: string;
  suggestion?: string;
  code?: number;
}

export default function SqlPage({
  params,
}: {
  params: Promise<{ projectId: string; datasetId: string }>;
}) {
  const { datasetId, projectId } = React.use(params);
  const { setOpen } = useSidebar();
  const [results, setResults] = React.useState<
    Record<string, unknown>[] | null
  >(null);
  const [totalCount, setTotalCount] = React.useState<number>(0);
  const [columns, setColumns] = React.useState<string[] | undefined>(undefined);
  const [executionTime, setExecutionTime] = React.useState<number | undefined>(undefined);
  const [isExecuting, setIsExecuting] = React.useState(false);
  const [queryError, setQueryError] = React.useState<ErrorDetails | null>(null);
  const executeSql = useDatasetSql();
  const nl2Sql = useNl2Sql();
  const [naturalQuery, setNaturalQuery] = React.useState("");
  const [rightPanelOpen, setRightPanelOpen] = React.useState(true);
  const [panelWidth, setPanelWidth] = React.useState(70);
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [datasetRows, setDatasetRows] = React.useState<
    Record<string, unknown>[] | null
  >(null);
  const [isResizing, setIsResizing] = React.useState(false);
  const [previewRowLimit] = React.useState(100);
  const [currentQuery, setCurrentQuery] = React.useState<string>("");
  const [queryGenerationStatus, setQueryGenerationStatus] = React.useState<
    "idle" | "processing" | "converting" | "executing" | "completed"
  >("idle");
  const [queryGenerated, setQueryGenerated] = React.useState(false);

  const { data: dataset, isLoading: datasetLoading } = useDataset({
    variables: {
      datasetId,
      projectId,
    },
  });

  const [query, setQuery] = React.useState("");
  const initializedDatasetRef = React.useRef<string | null>(null);

  // Close sidebar only on initial mount
  React.useEffect(() => {
    setOpen(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const executeQueryWithPagination = React.useCallback(
    async (queryToExecute: string, page: number = 1, limit: number = 10) => {
      const offset = (page - 1) * limit;

      // Clear previous results and errors when starting new query execution
      setResults(null);
      setTotalCount(0);
      setColumns(undefined);
      setExecutionTime(undefined);
      setQueryError(null);
      
      setIsExecuting(true);
      try {
        const response = await executeSql.mutateAsync({
          query: queryToExecute,
          limit,
          offset,
        });

        setResults(response.data);
        setTotalCount(response.count);
        setColumns(response.columns);
        setExecutionTime(response.executionTime);
        setCurrentQuery(queryToExecute);
        setQueryError(null);

        return response;
      } catch (error: unknown) {
        // Parse error response
        const errorDetails: ErrorDetails = {
          message: "Failed to execute query",
          details: undefined,
          suggestion: undefined,
          code: undefined,
        };

        const errorWithData = error as { errorData?: { message?: string; error?: string | unknown; code?: number } };
        if (errorWithData?.errorData) {
          const errorData = errorWithData.errorData;
          
          // Extract meaningful error information from server response
          if (errorData.message) {
            errorDetails.message = errorData.message;
          }
          if (errorData.error) {
            // If error is a string, use it as details
            if (typeof errorData.error === 'string') {
              errorDetails.details = errorData.error;
            }
          }
          if (errorData.code) {
            errorDetails.code = errorData.code;
          }
          
          // Add suggestions based on error type
          if (errorData.code === 404 || errorDetails.message.includes("dataset does not exist")) {
            errorDetails.suggestion = "Check that the table name is correct and that the dataset has been properly loaded.";
          } else if (errorData.code === 403 || errorDetails.message.includes("Only SELECT statements")) {
            errorDetails.suggestion = "Only SELECT queries are allowed. Please modify your query to retrieve data without making changes.";
          } else if (errorDetails.details?.includes("Syntax Error") || errorDetails.details?.includes("Parser Error")) {
            errorDetails.suggestion = "Check your SQL syntax. Common issues include missing commas, unclosed quotes, or incorrect keywords.";
          } else if (errorDetails.details?.includes("column") && errorDetails.details?.includes("not found")) {
            errorDetails.suggestion = "The column name might be incorrect. Check the available columns in the schema.";
          } else if (errorDetails.details?.includes("Binder Error")) {
            errorDetails.suggestion = "There's an issue with table or column references. Verify that all referenced tables and columns exist.";
          }
        } else if (error instanceof Error) {
          errorDetails.message = error.message;
        }

        setQueryError(errorDetails);
        setResults(null);
        throw error;
      } finally {
        setIsExecuting(false);
      }
    },
    [executeSql]
  );

  const handleExecuteSql = React.useCallback(async () => {
    if (!query.trim()) {
      toast.error("Please enter a SQL query");
      return;
    }

    // Format the SQL query before executing
    let formattedQuery = query;
    try {
      formattedQuery = format(query, {
        language: "sql",
        tabWidth: 2,
        useTabs: false,
        keywordCase: "lower",
        linesBetweenQueries: 2,
      });
      // Update the query state with formatted version
      setQuery(formattedQuery);
    } catch (error) {
      console.warn("Failed to format SQL:", error);
      // Continue with original query if formatting fails
    }

    executeQueryWithPagination(formattedQuery, 1, 20).catch(() => {
      // Error is already handled in executeQueryWithPagination
      // No need to show toast here as we'll display in the UI
    });
  }, [query, executeQueryWithPagination, setQuery]);

  const handlePageChange = React.useCallback(
    (page: number, limit: number) => {
      if (!currentQuery) return;

      executeQueryWithPagination(currentQuery, page, limit).catch(() => {
        // Error is already handled in executeQueryWithPagination
      });
    },
    [currentQuery, executeQueryWithPagination]
  );

  React.useEffect(() => {
    if (dataset?.name && dataset.name !== initializedDatasetRef.current) {
      // Mark this dataset as initialized
      initializedDatasetRef.current = dataset.name;

      const initialQuery = `SELECT * FROM ${dataset.name}`;
      setQuery(initialQuery);

      // Execute the initial query with pagination
      if (initialQuery.trim()) {
        executeQueryWithPagination(initialQuery, 1, 20).catch(() => {
          // Error is already handled in executeQueryWithPagination
        });
      }

      // Fetch initial dataset rows for preview
      executeSql
        .mutateAsync(`SELECT * FROM ${dataset.name} LIMIT ${previewRowLimit}`)
        .then((response) => {
          setDatasetRows(response.data);
        })
        .catch((error) => {
          console.error("Failed to fetch dataset rows:", error);
          toast.error(
            `Failed to fetch dataset preview: ${
              (error as Error).message || "Unknown error occurred"
            }`
          );
          setDatasetRows(null);
        });
    }
  }, [dataset?.name, executeSql, previewRowLimit, executeQueryWithPagination]);

  const handleGenerateAndExecute = async () => {
    if (!naturalQuery.trim()) {
      toast.error("Please enter your question");
      return;
    }

    if (!dataset?.name || dataset.name.trim() === "") {
      toast.error(
        "Dataset name is missing. Please refresh the page and try again."
      );
      return;
    }

    setQueryGenerationStatus("processing");
    setQueryGenerated(false);

    try {
      setQueryGenerationStatus("converting");
      const sqlQuery = await nl2Sql.mutateAsync({
        query: naturalQuery,
        datasetId: dataset.name,
      });

      // Format and set the generated SQL in the main editor
      let formattedSQL = sqlQuery.sql;
      try {
        formattedSQL = format(sqlQuery.sql, {
          language: "sql",
          tabWidth: 2,
          useTabs: false,
          keywordCase: "lower",
          linesBetweenQueries: 2,
        });
      } catch (error) {
        console.warn("Failed to format AI-generated SQL:", error);
        // Use original SQL if formatting fails
      }
      setQuery(formattedSQL);
      setQueryGenerated(true);

      setQueryGenerationStatus("executing");
      await executeQueryWithPagination(formattedSQL, 1, 20);

      setQueryGenerationStatus("completed");
      // Reset status after a delay
      setTimeout(() => {
        setQueryGenerationStatus("idle");
      }, 3000);
    } catch (error) {
      setQueryGenerationStatus("idle");
      setQueryGenerated(false);
      // Only show toast for NL2SQL generation errors, not SQL execution errors
      if (!queryError) {
        toast.error("Failed to process question: " + (error as Error).message);
      }
    }
  };

  const handleMouseDown = React.useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
  }, []);

  const handleMouseMove = React.useCallback(
    (e: MouseEvent) => {
      if (!isResizing) return;

      const newWidth = Math.max(
        30,
        Math.min(
          80,
          ((window.innerWidth - e.clientX) / window.innerWidth) * 100
        )
      );
      setPanelWidth(newWidth);
    },
    [isResizing]
  );

  const handleMouseUp = React.useCallback(() => {
    setIsResizing(false);
  }, []);

  React.useEffect(() => {
    if (isResizing) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
    } else {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    }

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
  }, [isResizing, handleMouseMove, handleMouseUp]);

  const isPending = isExecuting || nl2Sql.isPending;

  if (datasetLoading) {
    return <div>Loading dataset...</div>;
  }
  if (!dataset) {
    return <div>No dataset found</div>;
  }

  return (
    <motion.div
      variants={pageVariants}
      initial="initial"
      animate="animate"
      className="h-screen flex overflow-hidden"
    >
      {/* Main Query Interface */}
      <div className="flex-1 px-4 overflow-hidden min-h-0 flex flex-col">
        <motion.div variants={fadeInVariants} className="flex-1 min-h-0">
          <Card className="h-full flex flex-col">
            <CardHeader className="pb-4 flex-shrink-0 border-b bg-muted/50">
              <CardTitle className="font-medium">Query Data</CardTitle>
            </CardHeader>
            <CardContent className="flex-1 min-h-0 overflow-auto space-y-6">
              {/* Natural Language Input */}
              <div className="space-y-4 pt-4">
                <h3 className="text-sm font-medium text-muted-foreground">
                  Ask in Natural Language
                </h3>
                <div className="relative flex flex-col gap-2 border">
                  <div className="relative">
                    <Textarea
                      placeholder="Ask AI to help you write your query..."
                      value={naturalQuery}
                      onChange={(e) => setNaturalQuery(e.target.value)}
                      className="min-h-[80px] text-base leading-relaxed bg-background focus:ring-2 focus:ring-primary/20 border-muted placeholder:text-muted-foreground/50 resize-none rounded-md shadow-sm transition-all duration-200 ease-in-out hover:border-primary/30 focus:border-primary/40 pr-16"
                    />
                    <Button
                      onClick={handleGenerateAndExecute}
                      disabled={isPending}
                      size="sm"
                      variant="ghost"
                      className="absolute right-2 bottom-2 bg-transparent hover:bg-primary hover:text-primary-foreground border border-border hover:border-primary"
                    >
                      {nl2Sql.isPending ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <PlayIcon className="h-4 w-4" />
                      )}
                      Run
                    </Button>
                  </div>
                </div>
              </div>

              {/* SQL Editor */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-medium text-muted-foreground">
                    SQL Query
                  </h3>
                  <div className="flex items-center gap-2">
                    {queryGenerationStatus === "processing" && (
                      <span className="text-xs text-muted-foreground flex items-center gap-1">
                        <Loader2 className="h-3 w-3 animate-spin" />
                        Processing your question...
                      </span>
                    )}
                    {queryGenerationStatus === "converting" && (
                      <span className="text-xs text-muted-foreground flex items-center gap-1">
                        <Loader2 className="h-3 w-3 animate-spin" />
                        Converting to SQL...
                      </span>
                    )}
                    {queryGenerationStatus === "executing" && (
                      <span className="text-xs text-muted-foreground flex items-center gap-1">
                        <Loader2 className="h-3 w-3 animate-spin" />
                        Executing generated SQL...
                      </span>
                    )}
                    {queryGenerationStatus === "completed" && queryGenerated && (
                      <span className="text-xs text-green-600 flex items-center gap-1">
                        <CheckCircle2 className="h-3 w-3" />
                        Auto-generated
                      </span>
                    )}
                  </div>
                </div>
                <div className="relative border rounded-md overflow-hidden">
                  <SqlEditor
                    value={query}
                    onChange={(value) => {
                      setQuery(value);
                      // Reset the auto-generated flag if user manually edits the query
                      if (queryGenerated && queryGenerationStatus === "completed") {
                        setQueryGenerated(false);
                        setQueryGenerationStatus("idle");
                      }
                    }}
                    schema={dataset.columns}
                    datasetId={dataset.name}
                  />
                  <Button
                    onClick={handleExecuteSql}
                    disabled={isPending}
                    size="sm"
                    variant="ghost"
                    className="absolute right-2 bottom-2 z-10 bg-transparent hover:bg-primary hover:text-primary-foreground border border-border hover:border-primary"
                  >
                    {isExecuting ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <PlayIcon className="h-4 w-4" />
                    )}
                    Run
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* Right Panel */}
      {rightPanelOpen && (
        <motion.div
          initial={{ width: 0, opacity: 0 }}
          animate={{
            width: `${panelWidth}%`,
            opacity: 1,
            transition: { duration: 0 },
          }}
          exit={{ width: 0, opacity: 0 }}
          className="border-l flex flex-col min-h-0 relative h-full"
          transition={{ duration: 0 }}
        >
          {/* Resize Handle */}
          <div
            className="absolute left-0 top-0 bottom-0 w-px cursor-col-resize hover:bg-primary/50 bg-border"
            onMouseDown={handleMouseDown}
          />

          {/* Results Header */}
          <div className="border-b bg-muted/50 p-3 border">
            <div className="flex items-center justify-between px-4">
              <h3 className="font-medium">Results</h3>
              {!isExecuting && executionTime !== undefined && (
                <span className="text-sm text-muted-foreground">
                  Query Execution Time: {executionTime}ms
                </span>
              )}
            </div>
          </div>

          {/* Results Content */}
          <div className="flex-1 min-h-0 overflow-auto">
            {isExecuting ? (
              <div className="flex h-full flex-col items-center justify-center gap-2 text-muted-foreground">
                <Loader2 className="h-8 w-8 animate-spin opacity-50" />
                <p className="text-sm">Executing query...</p>
              </div>
            ) : queryError ? (
              <div className="flex h-full items-center justify-center px-8 pb-32">
                <div className="w-full max-w-3xl">
                  <div className="rounded-lg border border-destructive/20 bg-destructive/5 p-6 shadow-sm">
                    <div className="flex items-start gap-3">
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-destructive/10">
                        <svg
                          className="h-5 w-5 text-destructive"
                          fill="none"
                          viewBox="0 0 24 24"
                          strokeWidth="2"
                          stroke="currentColor"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
                          />
                        </svg>
                      </div>
                      <div className="flex-1 space-y-3">
                        <div>
                          <h3 className="text-base font-semibold text-destructive">
                            Query Execution Failed
                          </h3>
                          <p className="mt-1 text-sm text-destructive/90">
                            {queryError.message}
                          </p>
                        </div>
                        
                        {queryError.details && (
                          <div className="rounded-md bg-background/50 p-3">
                            <p className="text-xs font-medium text-muted-foreground mb-1">
                              Error Details:
                            </p>
                            <p className="text-sm text-foreground/80">
                              {queryError.details}
                            </p>
                          </div>
                        )}
                        
                        {currentQuery && (
                          <div className="rounded-md bg-muted/30 p-3">
                            <p className="text-xs font-medium text-muted-foreground mb-2">
                              Query that failed:
                            </p>
                            <pre className="text-xs text-muted-foreground overflow-x-auto whitespace-pre-wrap">
                              {currentQuery}
                            </pre>
                          </div>
                        )}
                        
                        {queryError.suggestion && (
                          <div className="flex items-start gap-2 rounded-md bg-primary/5 p-3">
                            <Lightbulb className="h-4 w-4 text-primary mt-0.5 shrink-0" />
                            <div>
                              <p className="text-xs font-medium text-primary mb-1">
                                Suggestion:
                              </p>
                              <p className="text-sm text-foreground/80">
                                {queryError.suggestion}
                              </p>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ) : results ? (
              <div className="p-4">
                <ResultsTable
                  results={results}
                  total={totalCount}
                  columns={columns}
                  onPageChange={handlePageChange}
                  loading={isExecuting}
                  sqlQuery={currentQuery}
                  datasetId={dataset?.name}
                />
              </div>
            ) : (
              <div className="flex h-full items-center justify-center text-muted-foreground pb-32">
                No results to display.
              </div>
            )}
          </div>
        </motion.div>
      )}

      {/* Right Panel Toggle Button (when closed) */}
      {!rightPanelOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="fixed right-4 top-1/2 -translate-y-1/2"
        >
          <Button
            onClick={() => setRightPanelOpen(true)}
            className="rounded-l-lg rounded-r-none shadow-lg"
          >
            <Database className="h-4 w-4" />
          </Button>
        </motion.div>
      )}
    </motion.div>
  );
}

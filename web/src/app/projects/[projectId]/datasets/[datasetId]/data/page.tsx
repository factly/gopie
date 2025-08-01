"use client";

import "regenerator-runtime/runtime";
import * as React from "react";
import { motion } from "framer-motion";
import { useDatasetSql, SqlQueryParams } from "@/lib/mutations/dataset/sql";
import { Button } from "@/components/ui/button";
import {
  PlayIcon,
  Loader2,
  Database,
} from "lucide-react";
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
  const [isExecuting, setIsExecuting] = React.useState(false);
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

  const executeQueryWithPagination = React.useCallback(async (
    queryToExecute: string, 
    page: number = 1, 
    limit: number = 10
  ) => {
    const offset = (page - 1) * limit;
    
    setIsExecuting(true);
    try {
      const response = await executeSql.mutateAsync({
        query: queryToExecute,
        limit,
        offset
      });
      
      setResults(response.data);
      setTotalCount(response.count);
      setCurrentQuery(queryToExecute);
      
      return response;
    } finally {
      setIsExecuting(false);
    }
  }, [executeSql]);

  const handleExecuteSql = React.useCallback(async () => {
    if (!query.trim()) {
      toast.error("Please enter a SQL query");
      return;
    }

    // Format the SQL query before executing
    let formattedQuery = query;
    try {
      formattedQuery = format(query, {
        language: 'sql',
        tabWidth: 2,
        useTabs: false,
        keywordCase: 'lower',
        linesBetweenQueries: 2,
      });
      // Update the query state with formatted version
      setQuery(formattedQuery);
    } catch (error) {
      console.warn('Failed to format SQL:', error);
      // Continue with original query if formatting fails
    }

    toast.promise(executeQueryWithPagination(formattedQuery, 1, 10), {
      loading: "Executing SQL query...",
      success: () => "Query executed successfully",
      error: (err) => `Failed to execute query: ${err.message}`,
    });
  }, [query, executeQueryWithPagination, setQuery]);

  const handlePageChange = React.useCallback((page: number, limit: number) => {
    if (!currentQuery) return;
    
    toast.promise(executeQueryWithPagination(currentQuery, page, limit), {
      loading: "Loading page...",
      success: () => `Loaded page ${page}`,
      error: (err) => `Failed to load page: ${err.message}`,
    });
  }, [currentQuery, executeQueryWithPagination]);


  React.useEffect(() => {
    if (dataset?.name && dataset.name !== initializedDatasetRef.current) {
      // Mark this dataset as initialized
      initializedDatasetRef.current = dataset.name;
      
      const initialQuery = `SELECT * FROM ${dataset.name}`;
      setQuery(initialQuery);
      
      // Execute the initial query with pagination
      if (initialQuery.trim()) {
        toast.promise(executeQueryWithPagination(initialQuery, 1, 10), {
          loading: "Executing SQL query...",
          success: () => "Query executed successfully",
          error: (err) => `Failed to execute query: ${err.message}`,
        });
      }
      
      // Fetch initial dataset rows for preview
      executeSql.mutateAsync(`SELECT * FROM ${dataset.name} LIMIT ${previewRowLimit}`)
        .then((response) => {
          setDatasetRows(response.data);
        })
        .catch((error) => {
          console.error("Failed to fetch dataset rows:", error);
          toast.error(
            `Failed to fetch dataset preview: ${(error as Error).message || "Unknown error occurred"}`
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
      toast.error("Dataset name is missing. Please refresh the page and try again.");
      return;
    }

    const promiseId = toast.loading("Processing your question...");

    try {
      toast.loading("Converting to SQL...", { id: promiseId });
      const sqlQuery = await nl2Sql.mutateAsync({
        query: naturalQuery,
        datasetId: dataset.name,
      });

      // Format and set the generated SQL in the main editor
      let formattedSQL = sqlQuery.sql;
      try {
        formattedSQL = format(sqlQuery.sql, {
          language: 'sql',
          tabWidth: 2,
          useTabs: false,
          keywordCase: 'lower',
          linesBetweenQueries: 2,
        });
      } catch (error) {
        console.warn('Failed to format AI-generated SQL:', error);
        // Use original SQL if formatting fails
      }
      setQuery(formattedSQL);

      toast.loading("Executing generated SQL...", { id: promiseId });
      await executeQueryWithPagination(formattedSQL, 1, 10);

      toast.success("Query executed successfully", { id: promiseId });
    } catch (error) {
      toast.error("Failed to process question: " + (error as Error).message, {
        id: promiseId,
      });
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
                <h3 className="text-sm font-medium text-muted-foreground">
                  SQL Query
                </h3>
                <div className="relative border rounded-md overflow-hidden">
                  <SqlEditor
                    value={query}
                    onChange={setQuery}
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
          <div className="border-b bg-muted/50 p-3 ml-4 border">
            <div className="flex items-center">
              <h3 className="font-medium">Results</h3>
            </div>
          </div>

          {/* Results Content */}
          <div className="mt-4 ml-4 flex-1 min-h-0 overflow-auto">
            {results ? (
              <ResultsTable 
                results={results} 
                total={totalCount}
                onPageChange={handlePageChange}
                loading={isExecuting}
              />
            ) : (
              <div className="p-4 text-center text-muted-foreground">
                No results to display. Execute a query to see results.
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
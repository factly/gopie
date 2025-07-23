"use client";

import "regenerator-runtime/runtime";
import * as React from "react";
import { motion } from "framer-motion";
import { useDatasetSql } from "@/lib/mutations/dataset/sql";
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
import { Badge } from "@/components/ui/badge";

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
  const executeSql = useDatasetSql();
  const nl2Sql = useNl2Sql();
  const [naturalQuery, setNaturalQuery] = React.useState("");
  const [rightPanelOpen, setRightPanelOpen] = React.useState(true);
  const [panelWidth, setPanelWidth] = React.useState(70);
  const [datasetRows, setDatasetRows] = React.useState<
    Record<string, unknown>[] | null
  >(null);
  const [isResizing, setIsResizing] = React.useState(false);
  const [previewRowLimit] = React.useState(100);

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

    toast.promise(executeSql.mutateAsync(formattedQuery), {
      loading: "Executing SQL query...",
      success: (response) => {
        setResults(response.data);
        return "Query executed successfully";
      },
      error: (err) => `Failed to execute query: ${err.message}`,
    });
  }, [query, executeSql, setQuery]);


  React.useEffect(() => {
    if (dataset?.name && dataset.name !== initializedDatasetRef.current) {
      // Mark this dataset as initialized
      initializedDatasetRef.current = dataset.name;
      
      const initialQuery = `SELECT * FROM ${dataset.name} LIMIT 10`;
      setQuery(initialQuery);
      
      // Execute the initial query directly
      if (initialQuery.trim()) {
        toast.promise(executeSql.mutateAsync(initialQuery), {
          loading: "Executing SQL query...",
          success: (response) => {
            setResults(response.data);
            return "Query executed successfully";
          },
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
  }, [dataset?.name, executeSql, previewRowLimit]);

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
      const response = await executeSql.mutateAsync(formattedSQL);
      setResults(response.data);

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

  const isPending = executeSql.isPending || nl2Sql.isPending;

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
            <CardHeader className="pb-3 flex-shrink-0">
              <CardTitle className="text-lg">Query Data</CardTitle>
            </CardHeader>
            <CardContent className="flex-1 min-h-0 overflow-auto space-y-6">
              {/* Natural Language Input */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-medium text-muted-foreground">
                    Ask in Natural Language
                  </h3>
                  <Button
                    onClick={handleGenerateAndExecute}
                    disabled={isPending}
                    size="sm"
                  >
                    {nl2Sql.isPending ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <PlayIcon className="mr-2 h-4 w-4" />
                    )}
                    Generate & Execute
                  </Button>
                </div>
                <div className="relative flex flex-col gap-2">
                  <Textarea
                    placeholder="Ask AI to help you write your query..."
                    value={naturalQuery}
                    onChange={(e) => setNaturalQuery(e.target.value)}
                    className="min-h-[80px] text-base leading-relaxed bg-background focus:ring-2 focus:ring-primary/20 border-muted placeholder:text-muted-foreground/50 resize-none rounded-md shadow-sm transition-all duration-200 ease-in-out hover:border-primary/30 focus:border-primary/40"
                  />
                </div>
              </div>

              {/* SQL Editor */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-medium text-muted-foreground">
                    SQL Query
                  </h3>
                  <Button
                    onClick={handleExecuteSql}
                    disabled={isPending}
                    size="sm"
                  >
                    {executeSql.isPending ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <PlayIcon className="mr-2 h-4 w-4" />
                    )}
                    Execute Query
                  </Button>
                </div>
                <div className="border rounded-md overflow-hidden">
                  <SqlEditor
                    value={query}
                    onChange={setQuery}
                    schema={dataset.columns}
                    datasetId={dataset.name}
                  />
                </div>
              </div>

              {/* Schema Section */}
              {dataset.columns && dataset.columns.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-sm font-medium text-muted-foreground">
                    Schema
                  </h4>
                  <div className="flex flex-wrap gap-1">
                    {dataset.columns.map((column, index) => (
                      <Badge
                        key={index}
                        variant="outline"
                        className="text-xs"
                      >
                        {column.column_name}
                        {column.column_type && (
                          <span className="text-muted-foreground ml-1">
                            ({column.column_type})
                          </span>
                        )}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
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
          <div className="border-b bg-muted/50 p-3 ml-4">
            <div className="flex items-center gap-2">
              <h3 className="font-medium">Results</h3>
            </div>
          </div>

          {/* Results Content */}
          <div className="mt-4 ml-4 flex-1 min-h-0 overflow-auto">
            {results ? (
              <ResultsTable results={results} />
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
"use client";

import * as React from "react";
import { useSqlStore } from "@/lib/stores/sql-store";
import { Button } from "@/components/ui/button";
import { Database, Download, Loader2, CheckCircleIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Progress } from "@/components/ui/progress";
import { useCreateDownload } from "@/lib/mutations/download/create-download";
import { useDownloadStore } from "@/lib/stores/download-store";
import { format as formatSQL } from "sql-formatter";
import dynamic from "next/dynamic";
import { useTheme } from "next-themes";
import { useToast } from "@/hooks/use-toast";

// Dynamically import Monaco Editor to avoid SSR issues
const Editor = dynamic(() => import("@monaco-editor/react"), {
  ssr: false,
  loading: () => (
    <div className="min-h-[150px] flex items-center justify-center border rounded-md bg-muted/20">
      <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
    </div>
  ),
});

// Helper function to format SQL queries safely
function formatSqlQuery(sql: string): string {
  try {
    return formatSQL(sql, {
      language: "sql",
      tabWidth: 2,
      useTabs: false,
      keywordCase: "upper",
      linesBetweenQueries: 2,
    });
  } catch (error) {
    console.error("Failed to format SQL:", error);
    return sql; // Return original SQL if formatting fails
  }
}

export function SqlResults() {
  const { results, currentPage, rowsPerPage, setCurrentPage, setRowsPerPage, onPageChange, isLoading } = useSqlStore();
  const { resolvedTheme } = useTheme();
  const { toast } = useToast();
  
  // Download state
  const [isDownloadDialogOpen, setIsDownloadDialogOpen] = React.useState(false);
  const [downloadFormat, setDownloadFormat] = React.useState<"csv" | "json" | "parquet">("csv");
  const [downloadSql, setDownloadSql] = React.useState("");
  const [completedDownloadUrl, setCompletedDownloadUrl] = React.useState<string | null>(null);
  const { createDownload } = useCreateDownload();
  const { currentDownloadProgress, setCurrentDownloadProgress } = useDownloadStore();
  
  // Extract dataset ID from the query if it exists
  const extractDatasetId = (query: string): string | null => {
    // Look for patterns like FROM "dataset_id" or FROM 'dataset_id' or FROM dataset_id
    // Also handle cases with schema like FROM schema.table or FROM "schema"."table"
    const patterns = [
      /FROM\s+["']?([^"'\s,]+)["']?/i,  // Basic pattern
      /FROM\s+["']?[\w]+["']?\.["']?([^"'\s,]+)["']?/i,  // Schema.table pattern
    ];
    
    for (const pattern of patterns) {
      const match = query.match(pattern);
      if (match) {
        // Get the last match group (table name in case of schema.table)
        return match[match.length - 1];
      }
    }
    return null;
  };
  
  const handleDownload = async () => {
    // If we have a completed download URL, just open it
    if (completedDownloadUrl) {
      window.open(completedDownloadUrl, "_blank");
      return;
    }

    try {
      // Extract dataset ID from the query
      const datasetId = extractDatasetId(downloadSql);
      
      if (!datasetId) {
        toast({
          title: "Error",
          description: "Could not identify dataset from the SQL query",
          variant: "destructive",
        });
        return;
      }
      
      const result = await createDownload({
        dataset_id: datasetId,
        sql: downloadSql,
        format: downloadFormat,
      });

      // Store the completed URL for re-download
      if (result.url) {
        setCompletedDownloadUrl(result.url);
        // Automatically open the download URL in a new tab
        window.open(result.url, "_blank");
      }

      toast({
        title: "Download ready",
        description: "Your download has been prepared and opened in a new tab.",
      });

      // Don't close the dialog, just update the state to show completion
      // User can close manually or download again
    } catch (error) {
      toast({
        title: "Download failed",
        description: error instanceof Error ? error.message : "Failed to create download",
        variant: "destructive",
      });
      setCompletedDownloadUrl(null);
    }
  };
  
  // Reset download progress and URL when dialog closes, format SQL when dialog opens
  React.useEffect(() => {
    if (!isDownloadDialogOpen) {
      setCurrentDownloadProgress(null);
      setCompletedDownloadUrl(null);
    } else if (results?.query) {
      // Format the SQL query when dialog opens
      setDownloadSql(formatSqlQuery(results.query));
    }
  }, [isDownloadDialogOpen, setCurrentDownloadProgress, results?.query]);

  const handleRowsPerPageChange = (value: string) => {
    const newRowsPerPage = Number(value);
    setRowsPerPage(newRowsPerPage);
    setCurrentPage(1);
    
    // Trigger server-side pagination if callback is provided
    if (onPageChange && results?.query) {
      onPageChange(1, newRowsPerPage);
    }
  };

  const handlePageChange = (newPage: number) => {
    setCurrentPage(newPage);
    
    // Trigger server-side pagination if callback is provided
    if (onPageChange && results?.query) {
      onPageChange(newPage, rowsPerPage);
    }
  };

  // Calculate total pages
  const totalPages = results?.total ? Math.ceil(results.total / rowsPerPage) : 0;
  
  return (
    <div className="flex h-full min-h-0 flex-col bg-muted/50">
      <div className="flex items-center justify-between border-b px-4 py-2">
        <div className="flex items-center gap-4">
          {results?.error ? (
            <span className="text-xs text-destructive">Error</span>
          ) : (
            <>
              <span className="text-xs text-muted-foreground">
                {results?.total || 0} total rows
              </span>
              {results?.executionTime !== undefined && (
                <span className="text-xs text-muted-foreground">
                  Query Execution Time: {results.executionTime}ms
                </span>
              )}
              {results?.data && results.data.length > 0 && (
                <>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground">
                      Rows per page:
                    </span>
                    <Select
                      value={rowsPerPage.toString()}
                      onValueChange={handleRowsPerPageChange}
                      disabled={isLoading}
                    >
                      <SelectTrigger className="h-7 w-[70px] text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="10">10</SelectItem>
                        <SelectItem value="20">20</SelectItem>
                        <SelectItem value="50">50</SelectItem>
                        <SelectItem value="100">100</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    Showing {results.data.length} rows
                  </span>
                </>
              )}
            </>
          )}
        </div>
        <div className="flex gap-2">
          {results?.data && results.data.length > 0 && (
            <Dialog
              open={isDownloadDialogOpen}
              onOpenChange={setIsDownloadDialogOpen}
            >
              <DialogTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                  title="Download Results"
                >
                  <Download className="h-4 w-4" />
                </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-[600px]">
                <DialogHeader>
                  <DialogTitle>Download Results</DialogTitle>
                  <DialogDescription>
                    Export your query results in your preferred format
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">
                      Format
                    </label>
                    <Select
                      value={downloadFormat}
                      onValueChange={(value) =>
                        setDownloadFormat(
                          value as "csv" | "json" | "parquet"
                        )
                      }
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="csv">
                          CSV - Comma-separated values
                        </SelectItem>
                        <SelectItem value="json">
                          JSON - JavaScript Object Notation
                        </SelectItem>
                        <SelectItem value="parquet">
                          Parquet - Columnar storage format
                        </SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <label className="text-sm font-medium">
                        SQL Query
                      </label>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          const formatted = formatSqlQuery(downloadSql);
                          setDownloadSql(formatted);
                        }}
                        className="h-7 text-xs"
                      >
                        Format SQL
                      </Button>
                    </div>
                    <div className="border rounded-md overflow-hidden">
                      <Editor
                        height="150px"
                        defaultLanguage="sql"
                        value={downloadSql}
                        onChange={(value) => setDownloadSql(value || "")}
                        theme={resolvedTheme === "dark" ? "vs-dark" : "light"}
                        options={{
                          minimap: { enabled: false },
                          fontSize: 13,
                          lineNumbers: "on",
                          roundedSelection: false,
                          scrollBeyondLastLine: false,
                          automaticLayout: true,
                          wordWrap: "on",
                          wrappingIndent: "indent",
                          formatOnPaste: true,
                          formatOnType: true,
                          scrollbar: {
                            vertical: "auto",
                            horizontal: "auto",
                          },
                          padding: {
                            top: 8,
                            bottom: 8,
                          },
                        }}
                      />
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Customize the SQL query to filter or transform
                      your data before download
                    </p>
                  </div>
                  {currentDownloadProgress && (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-muted-foreground">
                          {currentDownloadProgress.message}
                        </span>
                        <span className="font-medium">
                          {currentDownloadProgress.progress}%
                        </span>
                      </div>
                      <Progress
                        value={currentDownloadProgress.progress}
                      />
                    </div>
                  )}
                  {completedDownloadUrl &&
                    !currentDownloadProgress && (
                      <div className="rounded-lg bg-green-50 dark:bg-green-950 p-3 text-sm text-green-800 dark:text-green-200">
                        <div className="flex items-center gap-2">
                          <CheckCircleIcon className="h-4 w-4" />
                          <span>
                            Download completed successfully! The file
                            has been opened in a new tab.
                          </span>
                        </div>
                      </div>
                    )}
                </div>
                <DialogFooter>
                  <Button
                    variant="outline"
                    onClick={() => {
                      setIsDownloadDialogOpen(false);
                      setCompletedDownloadUrl(null);
                    }}
                    disabled={
                      currentDownloadProgress?.status === "processing"
                    }
                  >
                    {completedDownloadUrl ? "Close" : "Cancel"}
                  </Button>
                  <Button
                    onClick={handleDownload}
                    disabled={
                      !downloadSql ||
                      currentDownloadProgress?.status === "processing"
                    }
                  >
                    {currentDownloadProgress?.status ===
                    "processing" ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Processing...
                      </>
                    ) : completedDownloadUrl ? (
                      <>
                        <Download className="mr-2 h-4 w-4" />
                        Download File
                      </>
                    ) : (
                      <>
                        <Download className="mr-2 h-4 w-4" />
                        Download
                      </>
                    )}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          )}
        </div>
      </div>
      <div className="flex-1 min-h-0 overflow-auto p-4">
        {results?.error ? (
          <div className="w-full border border-destructive/50 bg-destructive/10 p-4">
            <p className="text-sm text-destructive">{results.error}</p>
            <pre className="mt-2 text-xs text-muted-foreground">
              {results.query}
            </pre>
          </div>
        ) : isLoading ? (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-muted-foreground">
            <Loader2 className="h-8 w-8 animate-spin opacity-50" />
            <p className="text-sm">Loading results...</p>
          </div>
        ) : results?.data?.length ? (
          <>
            <div className="w-full overflow-x-auto border">
              <table className="w-full text-sm">
                <thead className="sticky top-0 z-10">
                  <tr className="border-b bg-muted/50">
                    {(results.columns || Object.keys(results.data[0] || {})).map((key) => (
                      <th
                        key={key}
                        className="whitespace-nowrap border-r px-4 py-2 text-left font-medium last:border-r-0"
                      >
                        {key}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {results.data.map((row, i) => (
                    <tr
                      key={i}
                      className={cn(
                        "border-b last:border-b-0",
                        i % 2 === 0 ? "bg-background" : "bg-muted/30"
                      )}
                    >
                      {(results.columns || Object.keys(results.data[0] || {})).map((key, j) => (
                        <td
                          key={j}
                          className="whitespace-nowrap border-r px-4 py-2 last:border-r-0"
                        >
                          {String(row[key])}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            
            {/* Pagination */}
            {totalPages > 1 && (
              <div className="mt-4">
                <Pagination className="justify-center">
                  <PaginationContent>
                    <PaginationItem>
                      <PaginationPrevious
                        onClick={() => handlePageChange(Math.max(1, currentPage - 1))}
                        className={cn(
                          "cursor-pointer",
                          (currentPage === 1 || isLoading) && "pointer-events-none opacity-50"
                        )}
                      />
                    </PaginationItem>

                    {[...Array(totalPages)].map((_, i) => {
                      const page = i + 1;
                      const isCurrentPage = page === currentPage;

                      if (
                        page === 1 ||
                        page === totalPages ||
                        (page >= currentPage - 1 && page <= currentPage + 1)
                      ) {
                        return (
                          <PaginationItem key={page}>
                            <PaginationLink
                              onClick={() => handlePageChange(page)}
                              isActive={isCurrentPage}
                              className={cn(
                                "cursor-pointer",
                                isLoading && "pointer-events-none opacity-50"
                              )}
                            >
                              {page}
                            </PaginationLink>
                          </PaginationItem>
                        );
                      }

                      if (page === currentPage - 2 || page === currentPage + 2) {
                        return (
                          <PaginationItem key={page}>
                            <PaginationEllipsis />
                          </PaginationItem>
                        );
                      }

                      return null;
                    })}

                    <PaginationItem>
                      <PaginationNext
                        onClick={() => handlePageChange(Math.min(totalPages, currentPage + 1))}
                        className={cn(
                          "cursor-pointer",
                          (currentPage === totalPages || isLoading) && "pointer-events-none opacity-50"
                        )}
                      />
                    </PaginationItem>
                  </PaginationContent>
                </Pagination>
              </div>
            )}
          </>
        ) : (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-muted-foreground">
            <Database className="h-12 w-12 opacity-20" />
            <p className="text-sm font-medium">No data to display yet</p>
            <p className="text-xs">Run a query to see results here</p>
          </div>
        )}
      </div>
    </div>
  );
}

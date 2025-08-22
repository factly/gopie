import * as React from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card } from "@/components/ui/card";
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
import { TableIcon, Code2Icon, Download, Loader2, CheckCircleIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { SqlPreview } from "./sql-preview";
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

interface ResultsTableProps {
  results: Record<string, unknown>[];
  total?: number; // Total number of records (for server-side pagination)
  columns?: string[]; // Optional column order information
  onPageChange?: (page: number, limit: number) => void; // Callback for server-side pagination
  loading?: boolean; // Loading state for server-side pagination
  sqlQuery?: string; // The SQL query that was executed to get these results
  datasetId?: string; // The dataset ID for the download
}

export function ResultsTable({ results, total, columns, onPageChange, loading = false, sqlQuery, datasetId }: ResultsTableProps) {
  const [currentPage, setCurrentPage] = React.useState(1);
  const [rowsPerPage, setRowsPerPage] = React.useState(20);
  const [viewMode, setViewMode] = React.useState<"table" | "json">("table");
  const { resolvedTheme } = useTheme();
  const { toast } = useToast();
  
  // Download state
  const [isDownloadDialogOpen, setIsDownloadDialogOpen] = React.useState(false);
  const [downloadFormat, setDownloadFormat] = React.useState<"csv" | "json" | "parquet">("csv");
  const [downloadSql, setDownloadSql] = React.useState("");
  const [completedDownloadUrl, setCompletedDownloadUrl] = React.useState<string | null>(null);
  const { createDownload } = useCreateDownload();
  const { currentDownloadProgress, setCurrentDownloadProgress } = useDownloadStore();

  const handleRowsPerPageChange = (value: string) => {
    const newRowsPerPage = Number(value);
    setRowsPerPage(newRowsPerPage);
    setCurrentPage(1);
    
    // Trigger server-side pagination if callback is provided
    if (onPageChange) {
      onPageChange(1, newRowsPerPage);
    }
  };

  const handleDownload = async () => {
    // If we have a completed download URL, just open it
    if (completedDownloadUrl) {
      window.open(completedDownloadUrl, "_blank");
      return;
    }

    try {
      if (!datasetId) {
        toast({
          title: "Error",
          description: "Dataset ID is missing. Please refresh the page and try again.",
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
    } else {
      // Format the SQL query when dialog opens
      // Use the provided SQL query or default to SELECT * FROM dataset
      const queryToUse = sqlQuery || (datasetId ? `SELECT * FROM "${datasetId}"` : "");
      setDownloadSql(formatSqlQuery(queryToUse));
    }
  }, [isDownloadDialogOpen, setCurrentDownloadProgress, sqlQuery, datasetId]);

  const handlePageChange = (newPage: number) => {
    setCurrentPage(newPage);
    
    // Trigger server-side pagination if callback is provided
    if (onPageChange) {
      onPageChange(newPage, rowsPerPage);
    }
  };

  // Use server-side pagination if total is provided, otherwise client-side
  const isServerSidePagination = total !== undefined && onPageChange !== undefined;
  const totalPages = isServerSidePagination 
    ? Math.ceil(total / rowsPerPage)
    : Math.ceil(results.length / rowsPerPage);
  
  const paginatedResults = isServerSidePagination 
    ? results // Server already returned paginated results
    : results.slice((currentPage - 1) * rowsPerPage, currentPage * rowsPerPage);
  const tableColumns = columns || (results.length > 0 ? Object.keys(results[0]) : []);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="flex items-center border shadow-sm">
              <Button
                variant={viewMode === "table" ? "secondary" : "ghost"}
                size="sm"
                onClick={() => setViewMode("table")}
                className="gap-2"
              >
                <TableIcon className="h-4 w-4" />
                Table
              </Button>
              <Button
                variant={viewMode === "json" ? "secondary" : "ghost"}
                size="sm"
                onClick={() => setViewMode("json")}
                className="gap-2"
              >
                <Code2Icon className="h-4 w-4" />
                JSON
              </Button>
            </div>
            {results.length > 0 && (
              <Dialog
                open={isDownloadDialogOpen}
                onOpenChange={setIsDownloadDialogOpen}
              >
                <DialogTrigger asChild>
                  <Button
                    variant="outline"
                    size="sm"
                    className="gap-2"
                  >
                    <Download className="h-4 w-4" />
                    Download
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
          {viewMode === "table" && (
            <>
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground">
                  Rows per page:
                </span>
                <Select
                  value={rowsPerPage.toString()}
                  onValueChange={handleRowsPerPageChange}
                >
                  <SelectTrigger className="w-[100px]">
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
              <p className="text-sm text-muted-foreground">
                Showing {paginatedResults.length} of {isServerSidePagination ? total : results.length} rows
              </p>
            </>
          )}
        </div>
      </div>

      {viewMode === "table" ? (
        <>
          <Card>
            <Table>
              <TableHeader>
                <TableRow>
                  {tableColumns.map((column) => (
                    <TableHead key={column}>{column}</TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={tableColumns.length} className="text-center py-8">
                      Loading...
                    </TableCell>
                  </TableRow>
                ) : (
                  paginatedResults.map((row, idx) => (
                    <TableRow key={idx}>
                      {tableColumns.map((column) => (
                        <TableCell key={column}>
                          {row[column]?.toString() ?? "NULL"}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </Card>

          {totalPages > 1 && (
            <Pagination className="justify-center">
              <PaginationContent>
                <PaginationItem>
                  <PaginationPrevious
                    onClick={() => handlePageChange(Math.max(1, currentPage - 1))}
                    className={`cursor-pointer ${
                      currentPage === 1 ? "pointer-events-none opacity-50" : ""
                    }`}
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
                          className="cursor-pointer"
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
                    className={`cursor-pointer ${
                      currentPage === totalPages
                        ? "pointer-events-none opacity-50"
                        : ""
                    }`}
                  />
                </PaginationItem>
              </PaginationContent>
            </Pagination>
          )}
        </>
      ) : (
        <div className="h-[600px] border overflow-hidden">
          <SqlPreview
            value={JSON.stringify(results, null, 2)}
            language="json"
            height="600px"
          />
        </div>
      )}
    </div>
  );
}

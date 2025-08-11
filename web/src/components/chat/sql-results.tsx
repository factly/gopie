"use client";

import * as React from "react";
import { useSqlStore } from "@/lib/stores/sql-store";
import { Button } from "@/components/ui/button";
import { Database, Download, Loader2 } from "lucide-react";
import { cn, downloadCsv } from "@/lib/utils";
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

export function SqlResults() {
  const { results, currentPage, rowsPerPage, setCurrentPage, setRowsPerPage, onPageChange, isLoading } = useSqlStore();
  
  const handleDownload = () => {
    if (!results?.data?.length) return;
    downloadCsv(
      results.data,
      `sql_results_${new Date().toISOString().split("T")[0]}.csv`
    );
  };

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
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={handleDownload}
              title="Download as CSV"
            >
              <Download className="h-4 w-4" />
            </Button>
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

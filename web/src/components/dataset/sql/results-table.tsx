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
import { TableIcon, Code2Icon, Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { SqlPreview } from "./sql-preview";
import { downloadCsv } from "@/lib/utils";

interface ResultsTableProps {
  results: Record<string, unknown>[];
  total?: number; // Total number of records (for server-side pagination)
  onPageChange?: (page: number, limit: number) => void; // Callback for server-side pagination
  loading?: boolean; // Loading state for server-side pagination
}

export function ResultsTable({ results, total, onPageChange, loading = false }: ResultsTableProps) {
  const [currentPage, setCurrentPage] = React.useState(1);
  const [rowsPerPage, setRowsPerPage] = React.useState(20);
  const [viewMode, setViewMode] = React.useState<"table" | "json">("table");

  const handleRowsPerPageChange = (value: string) => {
    const newRowsPerPage = Number(value);
    setRowsPerPage(newRowsPerPage);
    setCurrentPage(1);
    
    // Trigger server-side pagination if callback is provided
    if (onPageChange) {
      onPageChange(1, newRowsPerPage);
    }
  };

  const handleDownload = () => {
    if (!results.length) return;
    downloadCsv(
      results,
      `results_${new Date().toISOString().split("T")[0]}.csv`,
    );
  };

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
  const columns = results.length > 0 ? Object.keys(results[0]) : [];

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
              <Button
                variant="outline"
                size="sm"
                onClick={handleDownload}
                className="gap-2"
              >
                <Download className="h-4 w-4" />
                Download
              </Button>
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
                  {columns.map((column) => (
                    <TableHead key={column}>{column}</TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={columns.length} className="text-center py-8">
                      Loading...
                    </TableCell>
                  </TableRow>
                ) : (
                  paginatedResults.map((row, idx) => (
                    <TableRow key={idx}>
                      {columns.map((column) => (
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

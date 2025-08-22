"use client";

import * as React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { useGetTable } from "@/lib/queries/dataset/get-table";
import {
  Pagination,
  PaginationContent,
  PaginationItem,
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
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Check,
  ChevronsUpDown,
  EyeOff,
  ArrowDown,
  ArrowUp,
  ArrowUpDown,
  TableIcon,
  Code2Icon,
  X,
  Filter,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useSchema } from "@/lib/queries/dataset/get-schema";
import { SqlPreview } from "@/components/dataset/sql/sql-preview";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { AlertCircle } from "lucide-react";

const MotionCard = motion.create(Card);
const MotionTableRow = motion.create(TableRow);

export function DataPreview(props: { datasetId: string }) {
  const [currentPage, setCurrentPage] = React.useState(1);
  const [rowsPerPage, setRowsPerPage] = React.useState(10);
  const [selectedColumns, setSelectedColumns] = React.useState<string[]>([]);
  const [open, setOpen] = React.useState(false);
  const [sortState, setSortState] = React.useState<
    Record<string, "asc" | "desc" | null>
  >({});
  const [viewMode, setViewMode] = React.useState<"table" | "json">("table");
  type FilterOperator = "e" | "gt" | "lt";
  type Filter = {
    column: string;
    value: string;
    operator: FilterOperator;
  };

  const [filters, setFilters] = React.useState<Filter[]>([]);
  const [filterOpen, setFilterOpen] = React.useState(false);
  const [newFilter, setNewFilter] = React.useState<Filter>({
    column: "",
    operator: "e",
    value: "",
  });

  const {
    data,
    isLoading: isTableLoading,
    error: tableError,
  } = useGetTable({
    variables: {
      limit: rowsPerPage,
      page: currentPage,
      datasetId: props.datasetId,
      columns: selectedColumns.length > 0 ? selectedColumns : [],
      sort: Object.entries(sortState)
        .filter(([_, direction]) => direction !== null)
        .map(([column, direction]) => ({
          column,
          direction: direction as "asc" | "desc",
        })),
      filter: filters,
    },
  });

  const {
    data: schema,
    isLoading: isSchemaLoading,
    error: schemaError,
  } = useSchema({
    variables: {
      datasetId: props.datasetId,
    },
  });

  const isLoading = isTableLoading || isSchemaLoading;
  const hasError = tableError || schemaError;

  // Get all available columns from the schema and maintain their order
  const allColumns = React.useMemo(
    () => schema?.schema.map((col) => col.column_name) ?? [],
    [schema]
  );

  // Use selected columns in schema order
  const columnsToShow = React.useMemo(
    () =>
      selectedColumns.length > 0
        ? allColumns.filter((col) => selectedColumns.includes(col))
        : allColumns,
    [selectedColumns, allColumns]
  );

  React.useEffect(() => {
    // Set initial columns when schema is loaded
    if (allColumns.length > 0 && selectedColumns.length === 0) {
      setSelectedColumns(allColumns);
    }
  }, [allColumns, selectedColumns.length]);

  const handleRowsPerPageChange = (value: string) => {
    setRowsPerPage(Number(value));
    setCurrentPage(1);
  };

  const handleSort = (column: string) => {
    setSortState((prev) => {
      const currentDirection = prev[column];
      const newState = { ...prev };

      // Cycle through: null -> asc -> desc -> null
      if (!currentDirection) {
        newState[column] = "asc";
      } else if (currentDirection === "asc") {
        newState[column] = "desc";
      } else {
        newState[column] = null;
      }

      return newState;
    });
  };

  const getSortIcon = (column: string) => {
    const direction = sortState[column];
    if (!direction)
      return <ArrowUpDown className="w-4 h-4 text-muted-foreground/50" />;
    return direction === "asc" ? (
      <ArrowUp className="w-4 h-4 text-primary" />
    ) : (
      <ArrowDown className="w-4 h-4 text-primary" />
    );
  };

  // Get the column count for skeleton UI
  const skeletonColumnCount = React.useMemo(
    () => schema?.schema.length || 6,
    [schema]
  );

  if (hasError) {
    return (
      <Alert variant="destructive" className="mb-4">
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>Error</AlertTitle>
        <AlertDescription>
          {tableError
            ? `Failed to load table data: ${tableError.message}`
            : schemaError
            ? `Failed to load schema: ${schemaError.message}`
            : "An unknown error occurred while loading data."}
        </AlertDescription>
      </Alert>
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        {/* Header skeleton */}
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-32" />
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-muted-foreground">
                Columns:
              </span>
              <Skeleton className="h-10 w-[200px]" />
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-muted-foreground">
                Rows per page:
              </span>
              <Skeleton className="h-10 w-[100px]" />
            </div>
          </div>
        </div>

        {/* Table skeleton */}
        <MotionCard
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="shadow-sm border overflow-hidden"
        >
          <Table>
            <TableHeader className="bg-muted/5">
              <TableRow>
                {[...Array(skeletonColumnCount)].map((_, i) => (
                  <TableHead key={i} className="py-3">
                    <div className="flex items-center gap-2">
                      <Skeleton className="h-4 w-[100px]" />
                      <Skeleton className="h-4 w-4" />
                    </div>
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {[...Array(10)].map((_, i) => (
                <MotionTableRow
                  key={i}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.1, delay: i * 0.05 }}
                >
                  {[...Array(skeletonColumnCount)].map((_, j) => (
                    <TableCell key={j}>
                      <Skeleton
                        className={cn(
                          "h-4",
                          // Vary the widths to make it look more natural
                          j === 0
                            ? "w-[80px]"
                            : j === 1
                            ? "w-[150px]"
                            : j === 2
                            ? "w-[100px]"
                            : "w-[120px]"
                        )}
                      />
                    </TableCell>
                  ))}
                </MotionTableRow>
              ))}
            </TableBody>
          </Table>
        </MotionCard>

        {/* Pagination skeleton */}
        <div className="flex items-center justify-between">
          <Skeleton className="h-4 w-16" />
          <Pagination className="justify-center">
            <PaginationContent className="shadow-sm">
              <PaginationItem>
                <Skeleton className="h-10 w-10" />
              </PaginationItem>
              <PaginationItem>
                <Skeleton className="h-10 w-10" />
              </PaginationItem>
            </PaginationContent>
          </Pagination>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div className="flex items-center gap-4">
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
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-muted-foreground">
              Columns:
            </span>
            <Popover open={open} onOpenChange={setOpen}>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  role="combobox"
                  aria-expanded={open}
                  className="w-[200px] justify-between shadow-sm"
                >
                  {selectedColumns.length} selected
                  <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-[200px] p-0">
                <Command>
                  <CommandInput placeholder="Search columns..." />
                  <CommandEmpty>No columns found.</CommandEmpty>
                  <CommandGroup className="max-h-[200px] overflow-auto">
                    <CommandList>
                      {allColumns.map((column) => (
                        <CommandItem
                          key={column}
                          onSelect={() => {
                            setSelectedColumns((prev) => {
                              // Don't allow deselecting the last column
                              if (prev.length === 1 && prev.includes(column)) {
                                return prev;
                              }
                              return prev.includes(column)
                                ? prev.filter((c) => c !== column)
                                : [...prev, column];
                            });
                          }}
                          className="cursor-pointer"
                        >
                          {selectedColumns.includes(column) ? (
                            <Check className="mr-2 h-4 w-4 text-primary" />
                          ) : (
                            <EyeOff className="mr-2 h-4 w-4 text-muted-foreground" />
                          )}
                          <span
                            className={cn(
                              "transition-colors",
                              selectedColumns.length === 1 &&
                                selectedColumns.includes(column)
                                ? "font-medium text-primary"
                                : selectedColumns.includes(column)
                                ? "text-foreground"
                                : "text-muted-foreground"
                            )}
                          >
                            {column}
                          </span>
                        </CommandItem>
                      ))}
                    </CommandList>
                  </CommandGroup>
                </Command>
              </PopoverContent>
            </Popover>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-muted-foreground">
              Filters:
            </span>
            <Popover open={filterOpen} onOpenChange={setFilterOpen}>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  role="combobox"
                  className="w-[200px] justify-between shadow-sm"
                >
                  {filters.length} active filters
                  <Filter className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-[400px] p-4">
                <div className="space-y-4">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <h4 className="font-medium">Active Filters</h4>
                      {filters.length > 0 && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setFilters([])}
                          className="h-auto p-1 text-xs text-muted-foreground hover:text-destructive"
                        >
                          Clear all
                        </Button>
                      )}
                    </div>
                    <ScrollArea className="h-[120px] border bg-muted/5 p-2">
                      {filters.length > 0 ? (
                        <div className="space-y-2 p-1">
                          {filters.map((filter, index) => (
                            <div
                              key={index}
                              className="group flex items-center gap-2 border bg-background p-2 shadow-sm transition-colors hover:bg-muted/30"
                            >
                              <div className="flex flex-1 items-center gap-2">
                                <Badge
                                  variant="secondary"
                                  className="font-mono"
                                >
                                  {filter.column}
                                </Badge>
                                <span className="text-sm text-muted-foreground">
                                  {filter.operator === "e"
                                    ? "equals"
                                    : filter.operator === "gt"
                                    ? "greater than or equals"
                                    : "less than or equals"}
                                </span>
                                <Badge variant="outline" className="font-mono">
                                  {filter.value}
                                </Badge>
                              </div>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() =>
                                  setFilters((prev) =>
                                    prev.filter((_, i) => i !== index)
                                  )
                                }
                                className="h-auto p-1 opacity-0 group-hover:opacity-100 transition-opacity"
                              >
                                <X className="h-4 w-4 text-muted-foreground hover:text-destructive" />
                              </Button>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
                          No active filters
                        </div>
                      )}
                    </ScrollArea>
                  </div>

                  <Separator />

                  <div className="space-y-4">
                    <h4 className="font-medium">Add Filter</h4>
                    <div className="grid gap-4">
                      <div className="grid gap-2">
                        <Label htmlFor="column">Column</Label>
                        <Select
                          value={newFilter.column}
                          onValueChange={(value) =>
                            setNewFilter((prev) => ({ ...prev, column: value }))
                          }
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Select column" />
                          </SelectTrigger>
                          <SelectContent>
                            {columnsToShow.map((column) => (
                              <SelectItem key={column} value={column}>
                                {column}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="grid gap-2">
                        <Label htmlFor="operator">Operator</Label>
                        <Select
                          value={newFilter.operator}
                          onValueChange={(value) =>
                            setNewFilter((prev) => ({
                              ...prev,
                              operator: value as typeof newFilter.operator,
                            }))
                          }
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="e">Equals (=)</SelectItem>
                            <SelectItem value="gt">
                              Greater Than Or Equals (&gt;=)
                            </SelectItem>
                            <SelectItem value="lt">
                              Less Than Or Equals (&lt;=)
                            </SelectItem>
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="grid gap-2">
                        <Label htmlFor="value">Value</Label>
                        <Input
                          id="value"
                          value={newFilter.value}
                          onChange={(e) =>
                            setNewFilter((prev) => ({
                              ...prev,
                              value: e.target.value,
                            }))
                          }
                          placeholder="Enter filter value"
                        />
                      </div>

                      <Button
                        onClick={() => {
                          if (newFilter.column && newFilter.value) {
                            setFilters((prev) => [...prev, { ...newFilter }]);
                            setNewFilter({
                              column: "",
                              operator: "e",
                              value: "",
                            });
                          }
                        }}
                        disabled={!newFilter.column || !newFilter.value}
                      >
                        Add Filter
                      </Button>
                    </div>
                  </div>
                </div>
              </PopoverContent>
            </Popover>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-muted-foreground">
              Rows per page:
            </span>
            <Select
              value={rowsPerPage.toString()}
              onValueChange={handleRowsPerPageChange}
            >
              <SelectTrigger className="w-[100px] shadow-sm">
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
        </div>
      </motion.div>
      <MotionCard
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.2 }}
        className="shadow-sm border relative min-h-[400px]"
      >
        {!data || data.data.length === 0 ? (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex items-center justify-center h-[300px] text-sm text-muted-foreground bg-muted/5"
          >
            No preview data available
          </motion.div>
        ) : viewMode === "table" ? (
          <div className="h-full overflow-auto">
            <Table>
              <TableHeader className="bg-muted/5">
                <MotionTableRow
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.2 }}
                >
                  {columnsToShow.map((column) => (
                    <TableHead
                      key={column}
                      className="font-medium cursor-pointer hover:bg-muted/10 transition-colors"
                      onClick={() => handleSort(column)}
                    >
                      <div className="flex items-center gap-2">
                        {column}
                        {getSortIcon(column)}
                      </div>
                    </TableHead>
                  ))}
                </MotionTableRow>
              </TableHeader>
              <TableBody>
                <AnimatePresence mode="wait">
                  {data.data.map((row, idx) => (
                    <MotionTableRow
                      key={idx}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ duration: 0.1 }}
                      className="hover:bg-muted/5 transition-colors"
                    >
                      {columnsToShow.map((column) => (
                        <TableCell key={column}>
                          {row[column]?.toString() ?? "NULL"}
                        </TableCell>
                      ))}
                    </MotionTableRow>
                  ))}
                </AnimatePresence>
              </TableBody>
            </Table>
          </div>
        ) : (
          <div className="absolute inset-0">
            <SqlPreview
              value={JSON.stringify(data?.data || [], null, 2)}
              language="json"
              height="400px"
            />
          </div>
        )}
      </MotionCard>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
        className="flex items-center justify-between"
      >
        <p className="text-sm font-medium text-muted-foreground whitespace-nowrap">
          Page {currentPage}
        </p>
        <Pagination className="justify-center">
          <PaginationContent className="shadow-sm">
            <PaginationItem>
              <PaginationPrevious
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                aria-disabled={currentPage === 1}
                className={`cursor-pointer ${
                  currentPage === 1 ? "pointer-events-none opacity-50" : ""
                }`}
              />
            </PaginationItem>
            <PaginationItem>
              <PaginationNext
                onClick={() => setCurrentPage((p) => p + 1)}
                aria-disabled={!data || data.data.length < rowsPerPage}
                className={`cursor-pointer ${
                  !data || data.data.length < rowsPerPage
                    ? "pointer-events-none opacity-50"
                    : ""
                }`}
              />
            </PaginationItem>
          </PaginationContent>
        </Pagination>
      </motion.div>
    </div>
  );
}

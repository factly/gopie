"use client";

import * as React from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { SqlPreview } from "@/components/dataset/sql/sql-preview";
import { useDataset } from "@/lib/queries/dataset/get-dataset";
import { useGetTable } from "@/lib/queries/dataset/get-table";
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
  X,
  Copy,
  ChevronDown,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import { env } from "@/lib/env";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export default function RestApiPage({
  params,
}: {
  params: Promise<{ projectId: string; datasetId: string }>;
}) {
  const { datasetId, projectId } = React.use(params);
  const [page, setPage] = React.useState("1");
  const [limit, setLimit] = React.useState("20");
  const [selectedColumns, setSelectedColumns] = React.useState<string[]>([]);
  const [columnsOpen, setColumnsOpen] = React.useState(false);
  const [filters, setFilters] = React.useState<
    Array<{ column: string; operator: string; value: string }>
  >([]);
  const [newFilter, setNewFilter] = React.useState({
    column: "",
    operator: "",
    value: "",
  });

  const { data: dataset, isLoading: datasetLoading } = useDataset({
    variables: {
      datasetId,
      projectId,
    },
  });

  const tableName = dataset?.name;
  const columns = dataset?.columns.map((col) => col.column_name) || [];

  const { data: tableData, isLoading: tableDataLoading } = useGetTable({
    variables: {
      datasetId: tableName || "",
      page: parseInt(page),
      limit: parseInt(limit),
      columns: selectedColumns,
      sort: [],
      filter: filters.map((f) => ({
        column: f.column,
        operator: f.operator as "e" | "gt" | "lt",
        value: f.value,
      })),
    },
  });

  const apiUrl =
    `${env.NEXT_PUBLIC_GOPIE_API_URL}/v1/api/tables/${tableName}?` +
    new URLSearchParams({
      page,
      limit,
      ...(selectedColumns.length > 0 && { columns: selectedColumns.join(",") }),
      ...(filters.length > 0 &&
        Object.fromEntries(
          filters.map((f) => [
            `filter[${f.column}]${f.operator === "e" ? "" : f.operator}`,
            f.value,
          ]),
        )),
    }).toString();

  const copyToClipboard = (type: string) => {
    let textToCopy = apiUrl;

    switch (type) {
      case "url":
        textToCopy = apiUrl;
        break;
      case "curl-cmd":
        textToCopy = `curl -X GET "${apiUrl}"`;
        break;
      case "curl-bash":
        textToCopy = `curl -X GET '${apiUrl}'`;
        break;
      case "powershell":
        textToCopy = `Invoke-WebRequest -Uri "${apiUrl}" -Method GET`;
        break;
      case "fetch":
        textToCopy = `fetch("${apiUrl}")
  .then(response => response.json())
  .then(data => console.log(data));`;
        break;
      case "fetch-node":
        textToCopy = `fetch("${apiUrl}")
  .then(response => response.json())
  .then(data => console.log(data))
  .catch(error => console.error('Error:', error));`;
        break;
    }

    navigator.clipboard.writeText(textToCopy);
    toast.success("Copied to clipboard");
  };

  if (datasetLoading) {
    return <div>Loading...</div>;
  }

  if (!dataset) {
    return <div>Dataset not found</div>;
  }

  return (
    <div className="container mx-auto py-8 px-4 sm:px-6 lg:px-8">
      <div className="flex gap-6">
        {/* Left Panel - Options */}
        <div className="border-r pr-6">
          <div>
            <h1 className="text-xl font-semibold mb-6">Request Parameters</h1>
          </div>

          <div className="grid gap-6">
            <div className="grid gap-2">
              <label className="text-sm">Page</label>
              <Input
                type="number"
                value={page}
                onChange={(e) => setPage(e.target.value)}
                className="h-9"
              />
            </div>

            <div className="grid gap-2">
              <label className="text-sm">Limit</label>
              <Input
                type="number"
                value={limit}
                onChange={(e) => setLimit(e.target.value)}
                className="h-9"
              />
            </div>

            <div className="grid gap-2">
              <label className="text-sm">Columns to Retrieve</label>
              <Popover open={columnsOpen} onOpenChange={setColumnsOpen}>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    role="combobox"
                    aria-expanded={columnsOpen}
                    className="justify-between h-9 font-normal"
                  >
                    {selectedColumns.length === 0
                      ? "Select columns..."
                      : `${selectedColumns.length} columns selected`}
                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-[400px] p-0">
                  <Command>
                    <CommandInput placeholder="Search columns..." />
                    <CommandEmpty>No columns found.</CommandEmpty>
                    <CommandGroup>
                      <CommandList>
                        {columns.map((column) => (
                          <CommandItem
                            key={column}
                            onSelect={() => {
                              setSelectedColumns((prev) =>
                                prev.includes(column)
                                  ? prev.filter((c) => c !== column)
                                  : [...prev, column],
                              );
                            }}
                          >
                            <Check
                              className={cn(
                                "mr-2 h-4 w-4",
                                selectedColumns.includes(column)
                                  ? "opacity-100"
                                  : "opacity-0",
                              )}
                            />
                            {column}
                          </CommandItem>
                        ))}
                      </CommandList>
                    </CommandGroup>
                  </Command>
                </PopoverContent>
              </Popover>
            </div>

            <div className="grid gap-2">
              <label className="text-sm">Filters</label>
              <div className="space-y-4">
                {filters.map((filter, index) => (
                  <div
                    key={index}
                    className="flex items-center gap-2 bg-muted/50 p-2 rounded-md text-sm"
                  >
                    <code>{filter.column}</code>
                    <code>{filter.operator || "="}</code>
                    <code>{filter.value}</code>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() =>
                        setFilters((prev) => prev.filter((_, i) => i !== index))
                      }
                      className="h-6 w-6 p-0"
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  </div>
                ))}

                <div className="flex items-center gap-2">
                  <Select
                    value={newFilter.column}
                    onValueChange={(value) =>
                      setNewFilter((prev) => ({ ...prev, column: value }))
                    }
                  >
                    <SelectTrigger className="h-9 w-[180px]">
                      <SelectValue placeholder="filter column" />
                    </SelectTrigger>
                    <SelectContent>
                      {columns.map((column) => (
                        <SelectItem key={column} value={column}>
                          {column}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>

                  <Select
                    value={newFilter.operator}
                    onValueChange={(value) =>
                      setNewFilter((prev) => ({ ...prev, operator: value }))
                    }
                  >
                    <SelectTrigger className="h-9 w-[140px]">
                      <SelectValue placeholder="operator" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="e">equals</SelectItem>
                      <SelectItem value="gt">greater than</SelectItem>
                      <SelectItem value="lt">less than</SelectItem>
                    </SelectContent>
                  </Select>

                  <Input
                    placeholder="value"
                    value={newFilter.value}
                    onChange={(e) =>
                      setNewFilter((prev) => ({
                        ...prev,
                        value: e.target.value,
                      }))
                    }
                    className="h-9 w-[140px]"
                  />

                  <Button
                    variant="outline"
                    onClick={() => {
                      if (newFilter.column && newFilter.value) {
                        setFilters((prev) => [...prev, { ...newFilter }]);
                        setNewFilter({ column: "", operator: "", value: "" });
                      }
                    }}
                    className="h-9 px-3"
                  >
                    Add
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Panel - Output */}
        <div className="flex-1">
          <div className="bg-muted/50 p-4 rounded-lg mb-4">
            <div className="flex items-center justify-between">
              <div className="text-sm font-medium">API URL</div>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="sm" className="h-8 gap-2">
                    <Copy className="h-4 w-4" />
                    Copy
                    <ChevronDown className="h-3 w-3 opacity-50" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-[200px]">
                  <DropdownMenuItem onClick={() => copyToClipboard("url")}>
                    Copy URL
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => copyToClipboard("curl-cmd")}>
                    Copy as cURL (cmd)
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={() => copyToClipboard("curl-bash")}
                  >
                    Copy as cURL (bash)
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={() => copyToClipboard("powershell")}
                  >
                    Copy as PowerShell
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => copyToClipboard("fetch")}>
                    Copy as fetch
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={() => copyToClipboard("fetch-node")}
                  >
                    Copy as fetch (Node.js)
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
            <code className="text-xs mt-2 block break-all">{apiUrl}</code>
          </div>
          <div className="bg-zinc-950">
            {tableDataLoading ? (
              <div className="flex items-center justify-center h-[calc(100vh-320px)]">
                <Loader2 className="animate-spin" />
              </div>
            ) : (
              <SqlPreview
                value={JSON.stringify(tableData?.data || [], null, 2)}
                language="json"
                height="calc(100vh - 320px)"
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

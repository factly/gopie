"use client";

import { useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  PencilIcon,
  Wand2,
  X,
  Check,
  MessageSquare,
  InfoIcon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  useColumnNameStore,
  validateColumnName,
  VALID_DUCK_DB_TYPES,
  toSnakeCase,
} from "@/lib/stores/columnNameStore";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useColumnDescriptionStore } from "@/lib/stores/columnDescriptionStore";
import { ColumnDescriptionDialog } from "./column-description-dialog";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

export interface ColumnNameEditorProps {
  onDataTypeChange?: () => Promise<void>;
}

export function ColumnNameEditor({ onDataTypeChange }: ColumnNameEditorProps) {
  const [editingNameIndex, setEditingNameIndex] = useState<string | null>(null);
  const [editNameValue, setEditNameValue] = useState("");
  const [editingDataTypeIndex, setEditingDataTypeIndex] = useState<
    string | null
  >(null);
  const [editDataTypeValue, setEditDataTypeValue] = useState("");
  const [descriptionDialogOpen, setDescriptionDialogOpen] = useState(false);
  const [currentColumn, setCurrentColumn] = useState<{
    originalName: string;
    updatedName: string;
  } | null>(null);

  const columnMappings = useColumnNameStore((state) => state.columnMappings);
  const updateColumnName = useColumnNameStore(
    (state) => state.updateColumnName
  );
  const updateColumnDataType = useColumnNameStore(
    (state) => state.updateColumnDataType
  );
  const autoFixAllColumns = useColumnNameStore(
    (state) => state.autoFixAllColumns
  );

  // Column description store
  const columnDescriptions = useColumnDescriptionStore(
    (state) => state.columnDescriptions
  );
  const updateColumnDescriptionKey = useColumnDescriptionStore(
    (state) => state.updateColumnDescriptionKey
  );

  // Check if there are any invalid columns
  const hasInvalidColumns = Array.from(columnMappings.values()).some(
    (mapping) => !mapping.isValid
  );

  // Convert Map to array for easier rendering
  const mappingsArray = Array.from(columnMappings.values());

  const handleEditNameStart = (originalName: string) => {
    setEditingNameIndex(originalName);
    const mapping = columnMappings.get(originalName);
    if (mapping) {
      setEditNameValue(mapping.updatedName);
    }
  };

  const handleEditNameSave = (originalName: string) => {
    const mapping = columnMappings.get(originalName);
    const oldUpdatedName = mapping?.updatedName;

    // Update the column name in the store
    updateColumnName(originalName, editNameValue);

    // If there was a description for the old updated name, transfer it to the new name
    if (oldUpdatedName && oldUpdatedName !== editNameValue) {
      updateColumnDescriptionKey(oldUpdatedName, editNameValue);
    }

    setEditingNameIndex(null);
    setEditNameValue("");
  };

  const handleEditNameCancel = () => {
    setEditingNameIndex(null);
    setEditNameValue("");
  };

  const handleEditDataTypeStart = (originalName: string) => {
    setEditingDataTypeIndex(originalName);
    const mapping = columnMappings.get(originalName);
    if (mapping) {
      setEditDataTypeValue(mapping.updatedDataType || mapping.dataType || "");
    }
  };

  const handleEditDataTypeSave = async (originalName: string) => {
    // Update the datatype in the store
    updateColumnDataType(originalName, editDataTypeValue);

    // Reset editing state
    setEditingDataTypeIndex(null);
    setEditDataTypeValue("");

    // If there's a callback to process the type change, call it
    if (onDataTypeChange) {
      try {
        await onDataTypeChange();
      } finally {
        // Processing complete
      }
    }
  };

  const handleEditDataTypeCancel = () => {
    setEditingDataTypeIndex(null);
    setEditDataTypeValue("");
  };

  const handleOpenDescriptionDialog = (originalName: string) => {
    const mapping = columnMappings.get(originalName);
    if (mapping) {
      setCurrentColumn({
        originalName: mapping.originalName,
        updatedName: mapping.updatedName,
      });
      setDescriptionDialogOpen(true);
    }
  };

  const handleKeyDown = (
    e: React.KeyboardEvent,
    originalName: string,
    type: "name" | "dataType"
  ) => {
    if (e.key === "Enter") {
      if (type === "name") {
        handleEditNameSave(originalName);
      } else if (type === "dataType") {
        handleEditDataTypeSave(originalName);
      }
    } else if (e.key === "Escape") {
      if (type === "name") {
        handleEditNameCancel();
      } else if (type === "dataType") {
        handleEditDataTypeCancel();
      }
    }
  };

  const handleAutoFixAll = () => {
    // Get the current state before auto-fixing
    const currentMappings = Array.from(columnMappings.values());

    // Apply auto-fix
    autoFixAllColumns();

    // Update description keys for changed column names
    currentMappings.forEach((mapping) => {
      if (!mapping.isValid) {
        const fixedName = toSnakeCase(mapping.originalName);
        if (mapping.updatedName !== fixedName) {
          updateColumnDescriptionKey(mapping.updatedName, fixedName);
        }
      }
    });
  };

  const hasDescription = (columnName: string) => {
    return (
      !!columnDescriptions[columnName] &&
      columnDescriptions[columnName].trim() !== ""
    );
  };

  if (mappingsArray.length === 0) {
    return null;
  }

  return (
    <div className="mt-8 space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-medium">Column Name and Type Editor</h3>
        {hasInvalidColumns && (
          <Button
            variant="outline"
            size="sm"
            onClick={handleAutoFixAll}
            className="flex items-center gap-1.5"
          >
            <Wand2 className="h-3.5 w-3.5" />
            Auto Fix All Columns
          </Button>
        )}
      </div>

      <p className="text-sm text-muted-foreground">
        Ensure column names follow these rules:
        <ul className="list-disc pl-5 mt-2">
          <li>Must be in snake_case (lowercase with underscores)</li>
          <li>Cannot start with a digit</li>
          <li>No special characters</li>
          <li>Cannot be a single digit</li>
        </ul>
      </p>

      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[120px]">Original Name</TableHead>
              <TableHead className="w-[120px]">Updated Name</TableHead>
              <TableHead className="w-[100px]">Data Type</TableHead>
              <TableHead className="w-[250px]">Description</TableHead>
              <TableHead className="w-[80px]">Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {mappingsArray.map((mapping) => (
              <TableRow key={mapping.originalName}>
                <TableCell className="whitespace-nowrap w-[120px]">
                  {mapping.originalName}
                </TableCell>
                <TableCell>
                  {editingNameIndex === mapping.originalName ? (
                    <div className="flex gap-2">
                      <Input
                        value={editNameValue}
                        onChange={(e) => setEditNameValue(e.target.value)}
                        onKeyDown={(e) =>
                          handleKeyDown(e, mapping.originalName, "name")
                        }
                        autoFocus
                        className={`flex-1 ${
                          !validateColumnName(editNameValue)
                            ? "border-red-500"
                            : ""
                        }`}
                      />
                      <div className="flex gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() =>
                            handleEditNameSave(mapping.originalName)
                          }
                          disabled={!validateColumnName(editNameValue)}
                          className="h-8 w-8 text-green-500 hover:text-green-600 hover:bg-green-50 hover:bg-muted"
                        >
                          <Check className="h-5 w-5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={handleEditNameCancel}
                          className="h-8 w-8 text-red-500 hover:text-red-600 hover:bg-red-50 hover:bg-muted"
                        >
                          <X className="h-5 w-5" />
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-center justify-between">
                      <span className={!mapping.isValid ? "text-red-500" : ""}>
                        {mapping.updatedName}
                      </span>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() =>
                          handleEditNameStart(mapping.originalName)
                        }
                        className="h-7 w-7 bg-muted/30 ml-2 opacity-60 hover:opacity-100 hover:bg-muted/60"
                      >
                        <PencilIcon className="h-3 w-3" />
                      </Button>
                    </div>
                  )}
                </TableCell>
                <TableCell>
                  {editingDataTypeIndex === mapping.originalName ? (
                    <div className="flex gap-2">
                      <Select
                        value={editDataTypeValue}
                        onValueChange={setEditDataTypeValue}
                        defaultValue={
                          mapping.updatedDataType || mapping.dataType || ""
                        }
                      >
                        <SelectTrigger className="w-full">
                          <SelectValue placeholder="Select data type" />
                        </SelectTrigger>
                        <SelectContent>
                          {VALID_DUCK_DB_TYPES.map((type) => (
                            <SelectItem key={type} value={type}>
                              {type}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <div className="flex gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() =>
                            handleEditDataTypeSave(mapping.originalName)
                          }
                          className="h-8 w-8 text-green-500 hover:text-green-600 hover:bg-green-50 hover:bg-muted"
                        >
                          <Check className="h-5 w-5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={handleEditDataTypeCancel}
                          className="h-8 w-8 text-red-500 hover:text-red-600 hover:bg-red-50 hover:bg-muted"
                        >
                          <X className="h-5 w-5" />
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-center justify-between">
                      <span>
                        {mapping.updatedDataType || mapping.dataType || "-"}
                      </span>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() =>
                          handleEditDataTypeStart(mapping.originalName)
                        }
                        className="h-7 w-7 bg-muted/30 ml-2 opacity-60 hover:opacity-100 hover:bg-muted/60"
                      >
                        <PencilIcon className="h-3 w-3" />
                      </Button>
                    </div>
                  )}
                </TableCell>
                <TableCell>
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex-grow overflow-hidden">
                      {hasDescription(mapping.updatedName) ? (
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <div className="flex items-center gap-1.5">
                                <div className="flex items-center justify-center bg-primary/10 border border-primary/20 px-1.5 py-0 h-5 w-5">
                                  <InfoIcon className="h-3 w-3 text-primary" />
                                </div>
                                <span className="text-xs line-clamp-1">
                                  {columnDescriptions[mapping.updatedName]}
                                </span>
                              </div>
                            </TooltipTrigger>
                            <TooltipContent className="max-w-xs">
                              <p>{columnDescriptions[mapping.updatedName]}</p>
                            </TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                      ) : (
                        <span className="text-xs text-muted-foreground">
                          No description
                        </span>
                      )}
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() =>
                        handleOpenDescriptionDialog(mapping.originalName)
                      }
                      className="h-6 w-6 bg-muted/30 flex-shrink-0 opacity-60 hover:opacity-100 hover:bg-muted/60"
                    >
                      <PencilIcon className="h-3 w-3" />
                    </Button>
                  </div>
                </TableCell>
                <TableCell>
                  {mapping.isValid ? (
                    <span className="flex items-center text-green-500">
                      <CheckCircle2 className="h-4 w-4 mr-1" /> Valid
                    </span>
                  ) : (
                    <span className="flex items-center text-red-500">
                      <AlertCircle className="h-4 w-4 mr-1" /> Invalid
                    </span>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {currentColumn && (
        <ColumnDescriptionDialog
          open={descriptionDialogOpen}
          onOpenChange={setDescriptionDialogOpen}
          columnName={currentColumn.updatedName}
          originalName={currentColumn.originalName}
        />
      )}
    </div>
  );
}

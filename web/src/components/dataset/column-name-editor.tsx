"use client";

import { useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  PencilIcon,
  Wand2,
  X,
  Check,
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
} from "@/lib/stores/columnNameStore";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

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
  const [isProcessing, setIsProcessing] = useState(false);

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
    updateColumnName(originalName, editNameValue);
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
      setIsProcessing(true);
      try {
        await onDataTypeChange();
      } finally {
        setIsProcessing(false);
      }
    }
  };

  const handleEditDataTypeCancel = () => {
    setEditingDataTypeIndex(null);
    setEditDataTypeValue("");
  };

  const handleKeyDown = (
    e: React.KeyboardEvent,
    originalName: string,
    type: "name" | "dataType"
  ) => {
    if (e.key === "Enter") {
      if (type === "name") {
        handleEditNameSave(originalName);
      } else {
        handleEditDataTypeSave(originalName);
      }
    } else if (e.key === "Escape") {
      if (type === "name") {
        handleEditNameCancel();
      } else {
        handleEditDataTypeCancel();
      }
    }
  };

  const handleAutoFixAll = () => {
    autoFixAllColumns();
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
        <div className="mt-2">
          You can also edit the data types to change how DuckDB processes the
          CSV. Changes to datatypes are processed immediately.
        </div>
      </p>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Original Name</TableHead>
            <TableHead>Updated Name</TableHead>
            <TableHead>Data Type</TableHead>
            <TableHead>Status</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {mappingsArray.map((mapping) => (
            <TableRow key={mapping.originalName}>
              <TableCell>{mapping.originalName}</TableCell>
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
                        onClick={() => handleEditNameSave(mapping.originalName)}
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
                      onClick={() => handleEditNameStart(mapping.originalName)}
                      className="h-7 w-7 rounded-full bg-muted/60 ml-2"
                    >
                      <PencilIcon className="h-3.5 w-3.5" />
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
                        <SelectValue placeholder="Select type" />
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
                        disabled={isProcessing}
                        className="h-8 w-8 text-green-500 hover:text-green-600"
                      >
                        <Check className="h-5 w-5" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={handleEditDataTypeCancel}
                        disabled={isProcessing}
                        className="h-8 w-8 text-red-500 hover:text-red-600"
                      >
                        <X className="h-5 w-5" />
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-center justify-between">
                    <span
                      className={
                        mapping.updatedDataType !== mapping.dataType
                          ? "text-blue-500 font-medium"
                          : ""
                      }
                    >
                      {mapping.updatedDataType || mapping.dataType || "N/A"}
                    </span>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() =>
                        handleEditDataTypeStart(mapping.originalName)
                      }
                      disabled={isProcessing}
                      className="h-7 w-7 rounded-full bg-muted/60 ml-2"
                    >
                      <PencilIcon className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                )}
              </TableCell>
              <TableCell>
                {mapping.isValid ? (
                  <span className="flex items-center text-green-500">
                    <CheckCircle2 className="h-4 w-4 mr-1" />
                    Valid
                  </span>
                ) : (
                  <span className="flex items-center text-red-500">
                    <AlertCircle className="h-4 w-4 mr-1" />
                    Invalid
                  </span>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

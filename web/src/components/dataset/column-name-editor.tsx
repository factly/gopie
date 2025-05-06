"use client";

import { useState } from "react";
import { AlertCircle, CheckCircle2, PencilIcon, Wand2 } from "lucide-react";
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
} from "@/lib/stores/columnNameStore";

export function ColumnNameEditor() {
  const [editingIndex, setEditingIndex] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");

  const columnMappings = useColumnNameStore((state) => state.columnMappings);
  const updateColumnName = useColumnNameStore(
    (state) => state.updateColumnName
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

  const handleEditStart = (originalName: string) => {
    setEditingIndex(originalName);
    const mapping = columnMappings.get(originalName);
    if (mapping) {
      setEditValue(mapping.updatedName);
    }
  };

  const handleEditSave = (originalName: string) => {
    updateColumnName(originalName, editValue);
    setEditingIndex(null);
    setEditValue("");
  };

  const handleEditCancel = () => {
    setEditingIndex(null);
    setEditValue("");
  };

  const handleKeyDown = (e: React.KeyboardEvent, originalName: string) => {
    if (e.key === "Enter") {
      handleEditSave(originalName);
    } else if (e.key === "Escape") {
      handleEditCancel();
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
        <h3 className="text-lg font-medium">Column Name Validation</h3>
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

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Original Name</TableHead>
            <TableHead>Updated Name</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Action</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {mappingsArray.map((mapping) => (
            <TableRow key={mapping.originalName}>
              <TableCell>{mapping.originalName}</TableCell>
              <TableCell>
                {editingIndex === mapping.originalName ? (
                  <Input
                    value={editValue}
                    onChange={(e) => setEditValue(e.target.value)}
                    onKeyDown={(e) => handleKeyDown(e, mapping.originalName)}
                    autoFocus
                    className={
                      !validateColumnName(editValue) ? "border-red-500" : ""
                    }
                  />
                ) : (
                  <span className={!mapping.isValid ? "text-red-500" : ""}>
                    {mapping.updatedName}
                  </span>
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
              <TableCell>
                {editingIndex === mapping.originalName ? (
                  <div className="flex space-x-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleEditSave(mapping.originalName)}
                      disabled={!validateColumnName(editValue)}
                    >
                      Save
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleEditCancel}
                    >
                      Cancel
                    </Button>
                  </div>
                ) : (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleEditStart(mapping.originalName)}
                  >
                    <PencilIcon className="h-4 w-4 mr-1" />
                    Edit
                  </Button>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

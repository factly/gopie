"use client";

import * as React from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import {
  useColumnDescriptions,
  ColumnSummary,
} from "@/lib/queries/dataset/get-column-descriptions";
import { useUpdateColumnDescriptions } from "@/lib/mutations/dataset/update-column-descriptions";
import { Loader2, Edit2, Save, X, FileText } from "lucide-react";
import { cn } from "@/lib/utils";

interface ColumnDescriptionsModalProps {
  datasetId: string;
  datasetName?: string;
  trigger?: React.ReactNode;
}

export function ColumnDescriptionsModal({
  datasetId,
  datasetName,
  trigger,
}: ColumnDescriptionsModalProps) {
  const [open, setOpen] = React.useState(false);
  const [editingColumn, setEditingColumn] = React.useState<string | null>(null);
  const [descriptions, setDescriptions] = React.useState<Record<string, string>>({});
  const [tempDescription, setTempDescription] = React.useState("");
  const { toast } = useToast();

  const { data, isLoading, error } = useColumnDescriptions({
    datasetId,
    enabled: open,
  });

  const updateMutation = useUpdateColumnDescriptions();

  // Initialize descriptions when data is loaded
  React.useEffect(() => {
    if (data?.data?.summary) {
      const initialDescriptions: Record<string, string> = {};
      data.data.summary.forEach((column) => {
        if (column.description) {
          initialDescriptions[column.column_name] = column.description;
        }
      });
      setDescriptions(initialDescriptions);
    }
  }, [data]);

  const handleEditClick = (columnName: string) => {
    setEditingColumn(columnName);
    setTempDescription(descriptions[columnName] || "");
  };

  const handleSaveDescription = (columnName: string) => {
    setDescriptions((prev) => ({
      ...prev,
      [columnName]: tempDescription,
    }));
    setEditingColumn(null);
    setTempDescription("");
  };

  const handleCancelEdit = () => {
    setEditingColumn(null);
    setTempDescription("");
  };

  const handleSaveAll = async () => {
    // Only send descriptions that have been added or modified
    const changedDescriptions: Record<string, string> = {};
    Object.entries(descriptions).forEach(([key, value]) => {
      if (value && value.trim()) {
        changedDescriptions[key] = value.trim();
      }
    });

    if (Object.keys(changedDescriptions).length === 0) {
      toast({
        title: "No changes to save",
        description: "Please add or modify at least one column description.",
        variant: "default",
      });
      return;
    }

    try {
      await updateMutation.mutateAsync({
        datasetId,
        data: { column_descriptions: changedDescriptions },
      });
      toast({
        title: "Success",
        description: "Column descriptions updated successfully.",
      });
      setOpen(false);
    } catch {
      toast({
        title: "Error",
        description: "Failed to update column descriptions. Please try again.",
        variant: "destructive",
      });
    }
  };

  const getColumnTypeColor = (type: string) => {
    const typeUpper = type.toUpperCase();
    if (typeUpper.includes("VARCHAR") || typeUpper.includes("TEXT")) return "bg-blue-100 text-blue-800";
    if (typeUpper.includes("INT") || typeUpper.includes("BIGINT")) return "bg-green-100 text-green-800";
    if (typeUpper.includes("FLOAT") || typeUpper.includes("DOUBLE") || typeUpper.includes("DECIMAL")) return "bg-purple-100 text-purple-800";
    if (typeUpper.includes("DATE") || typeUpper.includes("TIME")) return "bg-orange-100 text-orange-800";
    if (typeUpper.includes("BOOL")) return "bg-pink-100 text-pink-800";
    return "bg-gray-100 text-gray-800";
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger || (
          <Button variant="outline" size="sm">
            <FileText className="mr-2 h-4 w-4" />
            Column Descriptions
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="max-w-4xl max-h-[80vh]">
        <DialogHeader>
          <DialogTitle>Column Descriptions</DialogTitle>
          <DialogDescription>
            {datasetName ? `Dataset: ${datasetName}` : "View and edit descriptions for each column to help with AI-powered queries"}
          </DialogDescription>
        </DialogHeader>

        {isLoading && (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        )}

        {error && (
          <div className="text-center py-8 text-destructive">
            Failed to load column descriptions. Please try again.
          </div>
        )}

        {data?.data?.summary && (
          <>
            <ScrollArea className="h-[500px] pr-4">
              <div className="space-y-4">
                {data.data.summary.map((column: ColumnSummary) => (
                  <div
                    key={column.column_name}
                    className="border rounded-lg p-4 space-y-3"
                  >
                    <div className="flex items-start justify-between">
                      <div className="space-y-1 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="text-base font-semibold">
                            {column.column_name}
                          </span>
                          <Badge
                            variant="secondary"
                            className={cn("text-xs", getColumnTypeColor(column.column_type))}
                          >
                            {column.column_type}
                          </Badge>
                        </div>
                        <div className="text-sm text-muted-foreground space-y-1">
                          {column.count > 0 && (
                            <div className="flex flex-wrap gap-3">
                              <span>Count: {column.count.toLocaleString()}</span>
                              {column.approx_unique > 0 && (
                                <span>Unique: ~{column.approx_unique.toLocaleString()}</span>
                              )}
                              {column.null_percentage !== null && (
                                <span>
                                  Nulls: {
                                    typeof column.null_percentage === 'number' 
                                      ? column.null_percentage.toFixed(1)
                                      : column.null_percentage.Value.toFixed(1)
                                  }%
                                </span>
                              )}
                              {column.min && <span>Min: {column.min}</span>}
                              {column.max && <span>Max: {column.max}</span>}
                            </div>
                          )}
                        </div>
                      </div>
                      {editingColumn !== column.column_name && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleEditClick(column.column_name)}
                        >
                          <Edit2 className="h-4 w-4" />
                        </Button>
                      )}
                    </div>

                    {editingColumn === column.column_name ? (
                      <div className="space-y-2">
                        <Textarea
                          value={tempDescription}
                          onChange={(e) => setTempDescription(e.target.value)}
                          placeholder="Enter a description for this column..."
                          className="min-h-[80px]"
                          autoFocus
                        />
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            onClick={() => handleSaveDescription(column.column_name)}
                          >
                            <Save className="mr-1 h-3 w-3" />
                            Save
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={handleCancelEdit}
                          >
                            <X className="mr-1 h-3 w-3" />
                            Cancel
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <div className="text-sm">
                        {descriptions[column.column_name] ? (
                          <p className="text-foreground">{descriptions[column.column_name]}</p>
                        ) : (
                          <p className="text-muted-foreground italic">
                            No description available. Click edit to add one.
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </ScrollArea>

            <div className="flex justify-end gap-2 pt-4 border-t">
              <Button variant="outline" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button
                onClick={handleSaveAll}
                disabled={updateMutation.isPending}
              >
                {updateMutation.isPending && (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                )}
                Save All Changes
              </Button>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
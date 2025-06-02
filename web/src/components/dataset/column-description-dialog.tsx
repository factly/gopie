"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { useColumnDescriptionStore } from "@/lib/stores/columnDescriptionStore";

interface ColumnDescriptionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  columnName: string;
  originalName: string;
}

export function ColumnDescriptionDialog({
  open,
  onOpenChange,
  columnName,
  originalName,
}: ColumnDescriptionDialogProps) {
  const columnDescriptions = useColumnDescriptionStore(
    (state) => state.columnDescriptions
  );
  const setColumnDescription = useColumnDescriptionStore(
    (state) => state.setColumnDescription
  );

  const [description, setDescription] = useState<string>(
    columnDescriptions[columnName] || ""
  );

  const handleSave = () => {
    setColumnDescription(columnName, description);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Column Description</DialogTitle>
          <DialogDescription>
            Add a description for the column &quot;{columnName}&quot; to help
            users understand this data.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-4">
          <div className="grid grid-cols-4 items-start gap-4">
            <Label htmlFor="original-name" className="text-right pt-2">
              Original Name
            </Label>
            <div
              id="original-name"
              className="col-span-3 text-muted-foreground pt-2"
            >
              {originalName}
            </div>
          </div>

          <div className="grid grid-cols-4 items-start gap-4">
            <Label htmlFor="column-name" className="text-right pt-2">
              Column Name
            </Label>
            <div id="column-name" className="col-span-3 font-medium pt-2">
              {columnName}
            </div>
          </div>

          <div className="grid grid-cols-4 items-start gap-4">
            <Label htmlFor="description" className="text-right pt-2">
              Description
            </Label>
            <div className="col-span-3">
              <Textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe what this column represents..."
                className="min-h-[120px]"
              />
              <p className="text-xs text-muted-foreground mt-2">
                A clear description helps users understand the data. Include
                details like data format, units of measurement, or any specific
                context.
              </p>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSave}>Save Description</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

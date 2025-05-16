"use client";

import { useState, useEffect } from "react";
import { z } from "zod";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

// Zod schema for validation
const uploadFormSchema = z.object({
  datasetName: z.string().trim().min(1, "Dataset name is required"),
  description: z
    .string()
    .trim()
    .min(10, "Description must be at least 10 characters"),
});

interface UploadConfirmationDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (datasetName: string, description: string) => void;
  defaultName: string;
  fileName: string;
}

export function UploadConfirmationDialog({
  isOpen,
  onClose,
  onConfirm,
  defaultName,
  fileName,
}: UploadConfirmationDialogProps) {
  const [datasetName, setDatasetName] = useState<string>(defaultName);
  const [description, setDescription] = useState<string>(
    "Uploaded from GoPie Web"
  );
  const [errors, setErrors] = useState<{ [key: string]: string }>({});
  const [isValid, setIsValid] = useState<boolean>(true);

  // Validate form when input changes
  useEffect(() => {
    validateForm();
  }, [datasetName, description]);

  const validateForm = () => {
    try {
      uploadFormSchema.parse({
        datasetName,
        description,
      });
      setErrors({});
      setIsValid(true);
      return true;
    } catch (error) {
      if (error instanceof z.ZodError) {
        const newErrors: { [key: string]: string } = {};
        error.errors.forEach((err) => {
          if (err.path) {
            newErrors[err.path[0]] = err.message;
          }
        });
        setErrors(newErrors);
        setIsValid(Object.keys(newErrors).length === 0);
        return false;
      }
      return true;
    }
  };

  const handleConfirm = () => {
    if (validateForm()) {
      onConfirm(datasetName, description);
      onClose();
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Confirm Dataset Upload</DialogTitle>
          <DialogDescription>
            Provide a name and description for your dataset before uploading.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="grid grid-cols-4 items-center gap-4">
            <Label htmlFor="file-name" className="text-right">
              File
            </Label>
            <div className="col-span-3 text-sm text-muted-foreground">
              {fileName}
            </div>
          </div>
          <div className="grid grid-cols-4 items-center gap-4">
            <Label htmlFor="dataset-name" className="text-right">
              Dataset Name
            </Label>
            <div className="col-span-3 space-y-1">
              <Input
                id="dataset-name"
                value={datasetName}
                onChange={(e) => setDatasetName(e.target.value)}
                className={errors.datasetName ? "border-red-500" : ""}
              />
              {errors.datasetName && (
                <p className="text-xs text-red-500">{errors.datasetName}</p>
              )}
            </div>
          </div>
          <div className="grid grid-cols-4 items-center gap-4">
            <Label htmlFor="description" className="text-right">
              Description
            </Label>
            <div className="col-span-3 space-y-1">
              <Textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className={errors.description ? "border-red-500" : ""}
                rows={3}
              />
              {errors.description && (
                <p className="text-xs text-red-500">{errors.description}</p>
              )}
              <p className="text-xs text-muted-foreground">
                Description must be at least 10 characters
              </p>
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="button" onClick={handleConfirm} disabled={!isValid}>
            Upload Dataset
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

"use client";

import { useState, useRef } from "react";
import { toast } from "sonner";
import { UploadCloud, File, X, CheckCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";
import { UploadConfirmationDialog } from "./upload-confirmation-dialog";

interface CustomFileUploaderProps {
  onFileSelected: (file: File) => void;
  onUpload: (datasetName?: string, description?: string) => Promise<void>;
  isUploading: boolean;
  progress: number;
  selectedFile: File | null;
  canUpload: boolean;
  onClearFile: () => void;
  className?: string;
}

export function CustomFileUploader({
  onFileSelected,
  onUpload,
  isUploading,
  progress,
  selectedFile,
  canUpload,
  onClearFile,
  className,
}: CustomFileUploaderProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isConfirmDialogOpen, setIsConfirmDialogOpen] = useState(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      const file = files[0];
      // Check if it's a CSV file
      if (!file.name.endsWith(".csv") && file.type !== "text/csv") {
        toast.error("Only CSV files are supported");
        return;
      }
      onFileSelected(file);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      const file = files[0];
      // Check if it's a CSV file
      if (!file.name.endsWith(".csv") && file.type !== "text/csv") {
        toast.error("Only CSV files are supported");
        return;
      }
      onFileSelected(file);
    }
  };

  const handleUploadClick = () => {
    if (canUpload) {
      // Show confirmation dialog instead of uploading immediately
      setIsConfirmDialogOpen(true);
    } else {
      toast.error(
        "Please fix all column name validation errors before uploading"
      );
    }
  };

  const handleConfirmUpload = async (
    datasetName: string,
    description: string
  ) => {
    try {
      await onUpload(datasetName, description);
    } catch (error) {
      toast.error(
        `Upload failed: ${
          error instanceof Error ? error.message : "Unknown error"
        }`
      );
    }
  };

  const formatFileSize = (size: number) => {
    if (size < 1024) return `${size} B`;
    if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
    if (size < 1024 * 1024 * 1024)
      return `${(size / (1024 * 1024)).toFixed(1)} MB`;
    return `${(size / (1024 * 1024 * 1024)).toFixed(1)} GB`;
  };

  // Get the default dataset name from the file name
  const getDefaultDatasetName = () => {
    if (!selectedFile) return "";
    return selectedFile.name
      .replace(/\.csv$/, "")
      .replace(/[^a-zA-Z0-9.-]/g, "_");
  };

  return (
    <div className={cn("w-full", className)}>
      {!selectedFile ? (
        <div
          className={cn(
            "border-2 border-dashed rounded-lg p-8 flex flex-col items-center justify-center cursor-pointer transition-colors",
            isDragging
              ? "border-primary bg-primary/10"
              : "border-border hover:border-primary/50"
          )}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            className="hidden"
            accept=".csv,text/csv"
          />
          <UploadCloud className="h-10 w-10 text-muted-foreground mb-2" />
          <h3 className="text-lg font-medium mb-1">Upload CSV Dataset</h3>
          <p className="text-sm text-muted-foreground text-center mb-2">
            Drag and drop a CSV file here or click to browse
          </p>
          <p className="text-xs text-muted-foreground">
            Files will be validated before upload
          </p>
        </div>
      ) : (
        <div className="border rounded-lg p-4">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center">
              <File className="h-8 w-8 text-primary mr-3" />
              <div>
                <p className="font-medium text-sm">{selectedFile.name}</p>
                <p className="text-xs text-muted-foreground">
                  {formatFileSize(selectedFile.size)}
                </p>
              </div>
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={onClearFile}
              disabled={isUploading}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>

          {isUploading ? (
            <div className="space-y-2">
              <Progress value={progress} className="h-2" />
              <p className="text-xs text-center text-muted-foreground">
                Uploading: {progress}%
              </p>
            </div>
          ) : (
            <Button
              className="w-full"
              onClick={handleUploadClick}
              disabled={!canUpload}
            >
              {canUpload ? (
                <>
                  <CheckCircle className="h-4 w-4 mr-2" />
                  Upload File
                </>
              ) : (
                "Fix validation errors"
              )}
            </Button>
          )}
        </div>
      )}

      {/* Confirmation Dialog */}
      <UploadConfirmationDialog
        isOpen={isConfirmDialogOpen}
        onClose={() => setIsConfirmDialogOpen(false)}
        onConfirm={handleConfirmUpload}
        defaultName={getDefaultDatasetName()}
        fileName={selectedFile?.name || ""}
      />
    </div>
  );
}

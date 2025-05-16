"use client";

import { useState, useEffect } from "react";
import { toast } from "sonner";
import Uppy, { UppyFile, Meta } from "@uppy/core";
import AwsS3 from "@uppy/aws-s3";
import {
  validateCsvWithDuckDb,
  ValidationResult,
} from "@/lib/validation/validate-csv";
import { useDuckDb } from "@/hooks/useDuckDb";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { AlertCircle, CheckCircle2 } from "lucide-react";
import { useColumnNameStore } from "@/lib/stores/columnNameStore";
import { ColumnNameEditor } from "@/components/dataset/column-name-editor";
import { CustomFileUploader } from "./custom-file-uploader";

export interface CsvValidationUppyProps {
  projectId: string;
  onUploadSuccess?: (
    file: UppyFile<Meta, Record<string, never>>,
    response: unknown,
    columnMappings?: Record<string, string>
  ) => Promise<void>;
  width?: string | number;
}

function sanitizeFileName(name: string): string {
  // Remove non-alphanumeric characters except for dots and hyphens
  return name.replace(/[^a-zA-Z0-9.-]/g, "_");
}

export function CsvValidationUppy({
  projectId,
  onUploadSuccess,
  width = "100%",
}: CsvValidationUppyProps) {
  // Uppy instance
  const [uppy, setUppy] = useState<Uppy | null>(null);

  // File state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

  // Validation state
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [validationResult, setValidationResult] =
    useState<ValidationResult | null>(null);
  const { db, isInitialized, isInitializing, error: duckDbError } = useDuckDb();

  // Access column name store hooks
  const columnMappings = useColumnNameStore((state) => state.columnMappings);
  const setColumnMappings = useColumnNameStore(
    (state) => state.setColumnMappings
  );
  const setProjectId = useColumnNameStore((state) => state.setProjectId);
  const resetColumnMappings = useColumnNameStore(
    (state) => state.resetColumnMappings
  );
  const getColumnMappings = useColumnNameStore(
    (state) => state.getColumnMappings
  );

  // Calculate if all column names are valid
  const allColumnsValid = Array.from(columnMappings.values()).every(
    (mapping) => mapping.isValid
  );
  const canUpload =
    selectedFile !== null &&
    allColumnsValid &&
    validationResult?.isValid === true;

  // Set project ID in store when component mounts or project ID changes
  useEffect(() => {
    setProjectId(projectId);

    // Reset state when component unmounts
    return () => {
      resetColumnMappings();
      setSelectedFile(null);
      setValidationResult(null);
      setUploadError(null);
      if (uppy) {
        uppy.cancelAll();
      }
    };
  }, [projectId, setProjectId, resetColumnMappings, uppy]);

  // Initialize Uppy
  useEffect(() => {
    const uppyInstance = new Uppy({
      id: "dataset-uploader",
      restrictions: {
        maxNumberOfFiles: 1,
        allowedFileTypes: ["text/csv", ".csv"],
        // No maxFileSize - allow files of any size
      },
      autoProceed: false,
      allowMultipleUploads: false,
    });

    uppyInstance.use(AwsS3, {
      endpoint:
        process.env.NEXT_PUBLIC_COMPANION_URL || "http://localhost:3020",
    });

    // Handle upload progress
    uppyInstance.on("upload-progress", (file, progress) => {
      const bytesTotal = progress.bytesTotal || 0;
      if (bytesTotal > 0) {
        setUploadProgress(
          Math.round((progress.bytesUploaded / bytesTotal) * 100)
        );
      }
    });

    // Handle upload start
    uppyInstance.on("upload", () => {
      setIsUploading(true);
    });

    // Handle upload success
    uppyInstance.on("upload-success", async (file, response) => {
      try {
        // Get column mappings
        const mappings = getColumnMappings();

        // Log file metadata for debugging
        if (file) {
          console.log("Upload success file metadata:", file.meta);
        }

        // Call onUploadSuccess callback if provided
        if (onUploadSuccess && file) {
          await onUploadSuccess(file, response, mappings);
        }

        toast.success("File uploaded successfully!");

        // Reset states
        setSelectedFile(null);
        setValidationResult(null);
        resetColumnMappings();
        setUploadProgress(0);
        setIsUploading(false);
      } catch (error) {
        const errorMessage =
          error instanceof Error ? error.message : "Unknown error";
        setUploadError(`Upload success handler failed: ${errorMessage}`);
        toast.error(`Upload success handler failed: ${errorMessage}`);
      }
    });

    // Handle upload error
    uppyInstance.on("upload-error", (file, error) => {
      setUploadError(error.message);
      toast.error(`Upload failed: ${error.message}`);
      setIsUploading(false);
    });

    setUppy(uppyInstance);

    // Clean up function
    return () => {
      uppyInstance.cancelAll();
    };
  }, [projectId, onUploadSuccess, getColumnMappings, resetColumnMappings]);

  // Handle file selection
  const handleFileSelected = async (file: File) => {
    // Reset states
    setSelectedFile(file);
    setUploadError(null);
    setValidationResult(null);
    resetColumnMappings();

    if (!isInitialized || !db) {
      toast.warning(
        "DuckDB is not initialized for validation. Upload will proceed without validation."
      );
      return;
    }

    try {
      const fileSize = file.size;

      // Skip detailed validation for files > 1GB
      if (fileSize > 1000 * 1000 * 1000) {
        setValidationResult({
          isValid: true,
          error:
            "File is larger than 1GB. Will be uploaded and validated on the server.",
        });
        toast.info(
          "Large file detected. Client-side validation skipped, will validate on server."
        );
        return;
      }

      // Read file as ArrayBuffer for validation
      const buffer = await file.arrayBuffer();

      // Validate CSV with DuckDB
      const result = await validateCsvWithDuckDb(db, buffer, fileSize);
      setValidationResult(result);

      if (!result.isValid) {
        toast.error(`Validation failed: ${result.error}`);
        // Keep the file selected so user can see the error
      } else {
        toast.success("CSV validation successful!");

        // If validation successful and we have column names, update the column name store
        if (result.columnNames) {
          setColumnMappings(result.columnNames, result.columnTypes);
        }
      }
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "Unknown error";
      setUploadError(`Error processing file: ${errorMessage}`);
      toast.error(`Error processing file: ${errorMessage}`);
    }
  };

  // Clear selected file
  const handleClearFile = () => {
    setSelectedFile(null);
    setValidationResult(null);
    resetColumnMappings();
    setUploadError(null);
    if (uppy) {
      uppy.cancelAll();
    }
  };

  // Handle file upload
  const handleUpload = async (datasetName?: string, description?: string) => {
    if (!uppy || !selectedFile || !canUpload) {
      toast.error("Please fix all validation errors before uploading");
      return;
    }

    try {
      // Clear any previous uploads
      uppy.cancelAll();

      // Create timestamp for file name
      const timestamp = new Date().getTime();
      const sanitizedName = sanitizeFileName(selectedFile.name);

      // Format path according to [projectId]/dataset_[time]_filename.csv
      const path = `${projectId}/dataset_${timestamp}_${sanitizedName}`;

      // Get column mappings from store
      const mappings = getColumnMappings();

      // Use provided dataset name or sanitized filename
      const alias = datasetName || sanitizedName.replace(/\.csv$/, "");

      // Add file to Uppy with the custom dataset name stored properly in metadata
      uppy.addFile({
        name: path, // This is the file path for storage
        type: selectedFile.type,
        data: selectedFile,
        meta: {
          alias: alias, // Store the dataset name as 'alias' to be more clear
          datasetName: alias, // Also store as datasetName for redundancy
          projectId,
          type: "dataset",
          columnMappings: JSON.stringify(mappings),
          description: description || "Uploaded from GoPie Web",
        },
      });

      // Start upload
      uppy.upload();
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "Unknown error";
      setUploadError(`Upload preparation failed: ${errorMessage}`);
      toast.error(`Upload preparation failed: ${errorMessage}`);
    }
  };

  if (isInitializing) {
    return <div>Initializing DuckDB for CSV validation...</div>;
  }

  if (duckDbError) {
    toast.error(`DuckDB initialization error: ${duckDbError.message}`);
  }

  return (
    <div>
      {uploadError && (
        <Alert variant="destructive" className="mb-4">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Upload Error</AlertTitle>
          <AlertDescription>{uploadError}</AlertDescription>
        </Alert>
      )}

      {validationResult && (
        <Alert
          variant={validationResult.isValid ? "default" : "destructive"}
          className="mb-4"
        >
          {validationResult.isValid ? (
            validationResult.error &&
            validationResult.error.includes("too large") ? (
              <AlertCircle className="h-4 w-4 text-blue-500" />
            ) : (
              <CheckCircle2 className="h-4 w-4 text-green-500" />
            )
          ) : (
            <AlertCircle className="h-4 w-4" />
          )}
          <AlertTitle>
            {validationResult.isValid
              ? validationResult.error &&
                validationResult.error.includes("too large")
                ? "Large File Detected"
                : "DuckDB Validation Successful"
              : "DuckDB Validation Failed"}
          </AlertTitle>
          <AlertDescription>
            {validationResult.error
              ? validationResult.error
              : validationResult.columnNames && (
                  <div className="mt-2">
                    <p>
                      CSV file is valid with {validationResult.columnCount}{" "}
                      columns:
                    </p>
                    <p className="text-xs mt-1 max-h-20 overflow-y-auto">
                      {validationResult.columnNames.join(", ")}
                    </p>
                  </div>
                )}
          </AlertDescription>
        </Alert>
      )}

      {/* Custom file uploader */}
      <CustomFileUploader
        onFileSelected={handleFileSelected}
        onUpload={handleUpload}
        isUploading={isUploading}
        progress={uploadProgress}
        selectedFile={selectedFile}
        canUpload={canUpload}
        onClearFile={handleClearFile}
        className={typeof width === "number" ? `w-[${width}px]` : width}
      />

      {/* Column name editor */}
      {validationResult?.isValid && <ColumnNameEditor />}
    </div>
  );
}

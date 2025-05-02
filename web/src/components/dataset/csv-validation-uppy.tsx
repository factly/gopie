"use client";

import { useState, useEffect } from "react";
import Uppy, { UppyFile, Meta } from "@uppy/core";
import AwsS3 from "@uppy/aws-s3";
import { Dashboard } from "@uppy/react";
import { toast } from "sonner";
import {
  validateCsvWithDuckDb,
  ValidationResult,
} from "@/lib/validation/validate-csv";
import { useDuckDb } from "@/hooks/useDuckDb";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { AlertCircle, CheckCircle2 } from "lucide-react";

export interface CsvValidationUppyProps {
  projectId: string;
  onUploadSuccess?: (
    file: UppyFile<Meta, Record<string, never>>,
    response: unknown
  ) => Promise<void>;
  metaFields?: Array<{ id: string; name: string; placeholder?: string }>;
  height?: number;
  width?: string | number;
}

function sanitizeFileName(name: string): string {
  // Remove non-alphanumeric characters except for dots and hyphens
  return name.replace(/[^a-zA-Z0-9.-]/g, "_");
}

export function CsvValidationUppy({
  projectId,
  onUploadSuccess,
  metaFields,
  height = 400,
  width = "100%",
}: CsvValidationUppyProps) {
  const [uppy, setUppy] = useState<Uppy | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [validationResult, setValidationResult] =
    useState<ValidationResult | null>(null);
  const { db, isInitialized, isInitializing, error: duckDbError } = useDuckDb();

  useEffect(() => {
    // Initialize Uppy inside useEffect to avoid recreating it on every render
    const uppyInstance = new Uppy({
      id: "dataset-uploader",
      restrictions: {
        maxNumberOfFiles: 1,
        allowedFileTypes: ["text/csv", ".csv"],
        // No maxFileSize - allow files of any size
        requiredMetaFields: ["name"],
      },
      autoProceed: false,
      allowMultipleUploads: false,
      onBeforeUpload: (files) => {
        const updatedFiles: {
          [key: string]: UppyFile<Meta, Record<string, never>>;
        } = {};
        Object.keys(files).forEach((fileID) => {
          const file = files[fileID];
          const timestamp = new Date().getTime();
          const sanitizedName = sanitizeFileName(file.name || "");
          const path = `${projectId}/dataset_${timestamp}_${sanitizedName}`;

          updatedFiles[fileID] = {
            ...file,
            name: sanitizedName,
            meta: {
              ...file.meta,
              name: path,
              projectId,
              type: "dataset",
            },
          };
        });
        return updatedFiles;
      },
    });

    uppyInstance.use(AwsS3, {
      endpoint:
        process.env.NEXT_PUBLIC_COMPANION_URL || "http://localhost:3020",
    });

    // Add validation logic for CSV files
    uppyInstance.on("file-added", async (file) => {
      // Reset validation states
      setUploadError(null);
      setValidationResult(null);

      if (!isInitialized || !db) {
        // DuckDB not ready, but we'll still let the upload proceed
        toast.warning(
          "DuckDB is not initialized for validation. Upload will proceed without validation."
        );
        return;
      }

      try {
        const fileSize = file.size || 0;

        // Skip validation for files > 1GB
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

        // Read file as ArrayBuffer
        const fileArrayBuffer = await file.data.arrayBuffer();

        // Validate CSV with DuckDB
        const result = await validateCsvWithDuckDb(
          db,
          fileArrayBuffer,
          fileSize
        );
        setValidationResult(result);

        if (!result.isValid) {
          // Remove the file if validation fails
          uppyInstance.removeFile(file.id);
          toast.error(`Validation failed: ${result.error}`);
        } else {
          toast.success("CSV validation successful!");
        }
      } catch (error) {
        setUploadError(`Error processing file: ${(error as Error).message}`);
        uppyInstance.removeFile(file.id);
        toast.error(`Error processing file: ${(error as Error).message}`);
      }
    });

    // Handle upload success
    uppyInstance.on("upload-success", async (file, response) => {
      if (!file) {
        toast.error("No file data available");
        setUploadError("No file data available");
        return;
      }

      try {
        setUploadError(null);

        // Call the onUploadSuccess callback if provided
        if (onUploadSuccess) {
          await onUploadSuccess(file, response);
        }
      } catch (error) {
        const errorMessage =
          error instanceof Error ? error.message : "Unknown error occurred";
        setUploadError(errorMessage);
        toast.error(`Upload error: ${errorMessage}`);
        uppyInstance.cancelAll();
      }
    });

    uppyInstance.on("upload-error", (file, error) => {
      setUploadError(error.message);
      toast.error(`Upload failed: ${error.message}`);
    });

    uppyInstance.on("restriction-failed", (file, error) => {
      setUploadError(error.message);
      toast.error(error.message);
    });

    setUppy(uppyInstance);

    // Clean up Uppy instance on unmount
    return () => {
      uppyInstance.cancelAll();
    };
  }, [db, isInitialized, projectId, onUploadSuccess]);

  if (!uppy) {
    return <div>Loading uploader...</div>;
  }

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
                : "Validation Successful"
              : "Validation Failed"}
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

      <Dashboard
        uppy={uppy}
        proudlyDisplayPoweredByUppy={false}
        showProgressDetails={true}
        showRemoveButtonAfterComplete={true}
        height={height}
        width={width}
        theme="light"
        className="!bg-background !border-border !shadow-none rounded-lg"
        metaFields={metaFields}
      />
    </div>
  );
}

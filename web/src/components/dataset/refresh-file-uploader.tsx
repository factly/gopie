"use client";

import * as React from "react";
import {
  useState,
  useEffect,
  forwardRef,
  useImperativeHandle,
  useRef,
} from "react";
import { useTheme } from "next-themes";
import { toast } from "sonner";
import Uppy, { UppyFile, Meta } from "@uppy/core";
import Dashboard from "@uppy/dashboard";
import GoogleDrive from "@uppy/google-drive";
import Url from "@uppy/url";
import AwsS3Multipart from "@uppy/aws-s3";

// Import Uppy styles and our custom theme
import "@uppy/core/dist/style.min.css";
import "@uppy/dashboard/dist/style.min.css";
import "@/app/uppy-theme.css";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {  AlertCircle } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import {
  validateFileWithDuckDb,
  detectFileFormat,
  SUPPORTED_FORMATS,
} from "@/lib/validation/validate-file";
import { useDuckDb } from "@/hooks/useDuckDb";
import { compareSchemas } from "@/lib/utils/schema-comparison";
import { ColumnInfo } from "@/lib/queries/dataset/get-schema";
import { useUploadStore } from "@/lib/stores/uploadStore";
import { sanitizeAndUniquifyFilename } from "@/lib/utils/sanitize-filename";


// Possible states during the validation process
type ValidationStateType =
  | "idle" // No file selected or cleared
  | "validating" // DuckDB check in progress
  | "schema_match" // DuckDB check done, schema is compatible
  | "schema_mismatch" // DuckDB check done, schema is incompatible
  | "validation_error" // DuckDB check failed (bad file, etc.)
  | "no_schema_to_compare" // Parent didn't provide existing schema
  | "validation_unavailable"; // DuckDB couldn't initialize

export interface RefreshFileUploaderProps {
  existingSchema: ColumnInfo[] | null | undefined;
  onValidationStateChange: (state: ValidationStateType, message?: string) => void;
  onUploadSuccess: (
    file: UppyFile<Meta, Record<string, never>>,
    response: unknown
  ) => void;
  onUploadError: (error: string) => void;
}

export interface RefreshFileUploaderRef {
  triggerUpload: () => Promise<void>;
  clearUploader: () => void;
}

export const RefreshFileUploader = forwardRef<
  RefreshFileUploaderRef,
  RefreshFileUploaderProps
>(function RefreshFileUploader(
  { existingSchema, onValidationStateChange, onUploadSuccess, onUploadError },
  ref
) {
  const { resolvedTheme } = useTheme();
  const { db, isInitialized, error: duckDbError } = useDuckDb();

  const [uppy, setUppy] = useState<Uppy | null>(null);
  const [selectedFile, setSelectedFile] = useState<UppyFile<Meta, Record<string, never>> | null>(null);
  const [schemaComparisonResult, setSchemaComparisonResult] = useState<{ areMatching: boolean; error?: string } | null>(null);

  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const dashboardRef = useRef<HTMLDivElement>(null);
  const setUploadedFileRef = useRef(useUploadStore.getState().setUploadedFile);

  // --- Uppy Initialization ---
  useEffect(() => {
    if (!dashboardRef.current) return;

    const companionUrl =
      process.env.NEXT_PUBLIC_COMPANION_URL || "http://localhost:3020";

    const uppyInstance = new Uppy({
      id: "refresh-file-uploader",
      autoProceed: false,
      allowMultipleUploads: false,
      restrictions: {
        maxNumberOfFiles: 1,
         allowedFileTypes: [
           ".csv", ".parquet", ".json", ".xlsx", ".xls", ".duckdb",
           "text/csv", "application/json",
           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
           "application/vnd.ms-excel",
         ],
      },
      debug: process.env.NODE_ENV === "development",
      onBeforeFileAdded: (currentFile) => {
          const originalName = currentFile?.name || '';
          const modifiedName = sanitizeAndUniquifyFilename(originalName);

          const modifiedFile = {
              ...currentFile,
              name: modifiedName, // Update the primary name
              meta: {
                  ...currentFile.meta,
                  name: modifiedName, // Also update meta name if needed by plugins
                  originalName: originalName, // Store original name in meta if needed later
              },
          };
          console.log(`Original filename: "${originalName}", Sanitized: "${modifiedName}"`);
          return modifiedFile;
      }
    });

    uppyInstance.use(Dashboard, {
      target: dashboardRef.current,
      inline: true,
      width: "100%",
      height: 400,
      showProgressDetails: true,
      hideUploadButton: true,
      hideRetryButton: true,
      hidePauseResumeButton: true,
      proudlyDisplayPoweredByUppy: false,
      note: "Select the replacement file",
      theme: resolvedTheme === "dark" ? "dark" : "light",
      doneButtonHandler: null,
    });
     // eslint-disable-next-line @typescript-eslint/no-explicit-any
    uppyInstance.use(GoogleDrive, { target: Dashboard as any, companionUrl });
     // eslint-disable-next-line @typescript-eslint/no-explicit-any
    uppyInstance.use(Url, { target: Dashboard as any, companionUrl });

    if (companionUrl) {
      uppyInstance.use(AwsS3Multipart, {
        endpoint: companionUrl,
      });
    } else {
        console.error("Companion URL is not defined. S3 uploads might fail.");
    }

    // --- Core Logic: Handle file selection and validation ---
    uppyInstance.on("file-added", async (file) => {
      setSelectedFile(null);
      setSchemaComparisonResult(null);
      setUploadError(null);
      onValidationStateChange("validating");

      try {
        if (!file) {
            throw new Error("File selection resulted in an undefined file object.");
        }
        setSelectedFile(file);
        setUploadedFileRef.current(file);

        const format = detectFileFormat(
          file.name || "",
          file.type || "application/octet-stream"
        );
        if (!format) {
          throw new Error(
            `Unsupported file format. Supported: ${Object.keys(
              SUPPORTED_FORMATS
            ).join(", ")}`
          );
        }

        if (!isInitialized || !db) {
            onValidationStateChange("validation_unavailable");
            return;
        }

        // --- THIS IS THE FIX ---
        // Use `as unknown` before checking instanceof
        const fileData = file.data as unknown;
        if (!fileData || !(fileData instanceof Blob || fileData instanceof ArrayBuffer)) {
             throw new Error("File data is missing or not in a readable format (Blob/ArrayBuffer). Cannot validate.");
        }
        // --- END OF FIX ---


        let buffer: ArrayBuffer;
        // Now it's safe to use instanceof after the assertion above
        if (fileData instanceof Blob) {
            buffer = await fileData.arrayBuffer();
        } else { // It must be ArrayBuffer
            buffer = fileData;
        }


        const validation = await validateFileWithDuckDb(
            db,
            buffer,
            file.name || "",
            file.size || 0,
            file.type || "application/octet-stream"
        );


        if (!validation.isValid) {
            throw new Error(
            validation.error || "File validation failed during schema inference."
            );
        }

        if (!existingSchema || existingSchema.length === 0) {
             onValidationStateChange("no_schema_to_compare");
             return;
        }

        const comparison = compareSchemas(existingSchema, validation);
        setSchemaComparisonResult(comparison);

        if (!comparison.areMatching) {
            onValidationStateChange("schema_mismatch", comparison.error);
        } else {
            toast.success("Schema validation successful!");
            onValidationStateChange("schema_match");
        }

      } catch (error) {
        const errorMessage =
          error instanceof Error ? error.message : "File processing error";
        toast.error(errorMessage);
        onValidationStateChange("validation_error", errorMessage);
        if (file && uppyInstance.getFile(file.id)) {
            uppyInstance.removeFile(file.id);
        }
        setSelectedFile(null);
      }
    });

    uppyInstance.on("file-removed", (file) => {
      if (selectedFile?.id === file?.id) {
        setSelectedFile(null);
        setSchemaComparisonResult(null);
        setIsUploading(false);
        setUploadProgress(0);
        setUploadError(null);
        onValidationStateChange("idle");
      }
    });

    uppyInstance.on("upload", () => {
        setIsUploading(true);
        setUploadProgress(0);
        setUploadError(null);
    });

    uppyInstance.on("upload-progress", (file, progress) => {
      const totalBytes = progress.bytesTotal || 1;
      setUploadProgress(
        Math.round((progress.bytesUploaded / totalBytes) * 100)
      );
    });

    uppyInstance.on("upload-success", (file, response) => {
      if (file) {
          setIsUploading(false);
          setUploadProgress(100);
          onUploadSuccess(file, response);
      } else {
          const errorMsg = "S3 Upload succeeded but file data is missing.";
          setIsUploading(false);
          setUploadError(errorMsg);
          onUploadError(errorMsg);
          toast.error(errorMsg);
      }
    });

    uppyInstance.on("upload-error", (file, error, response) => {
      setIsUploading(false);
       // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const responseBody = (response as any)?.body;
      const serverMessage = typeof responseBody === 'object' && responseBody?.message ? responseBody.message : (typeof responseBody === 'string' ? responseBody : null);
      const errorMsg = `Storage Upload failed: ${serverMessage || error.message}`;
      setUploadError(errorMsg);
      onUploadError(errorMsg);
      toast.error(errorMsg);
    });

    uppyInstance.on("complete", (result) => {
      if (result && result.failed && result.failed.length > 0) {
          // Error handled
      } else {
          // Success handled
      }
      setIsUploading(false);
    });


    setUppy(uppyInstance);

    return () => {
      uppyInstance.destroy();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isInitialized, db, resolvedTheme]);


  // Handle theme changes
  useEffect(() => {
    if (uppy && dashboardRef.current) {
        const dashboard = uppy.getPlugin("Dashboard") as Dashboard<Meta, Record<string, never>>;
        if (dashboard) {
            dashboard.setOptions({ theme: resolvedTheme === "dark" ? "dark" : "light" });
            const container = dashboardRef.current.querySelector(".uppy-Dashboard");
            if (container) {
                container.classList.remove("uppy-theme-dark", "uppy-theme-light");
                container.classList.add(`uppy-theme-${resolvedTheme === "dark" ? "dark" : "light"}`);
            }
        }
    }
  }, [uppy, resolvedTheme]);

  // Expose triggerUpload and clearUploader via ref
  useImperativeHandle(ref, () => ({
    triggerUpload: async () => {
      if (!uppy || !selectedFile) {
        throw new Error("No file selected for upload.");
      }
      if (schemaComparisonResult?.areMatching !== true) {
         throw new Error("Cannot upload: Schema does not match or validation pending.");
      }
      setUploadError(null);
      setIsUploading(true);
      setUploadProgress(0);
      try {
        await uppy.upload();
      } catch (uploadError) {
          setIsUploading(false);
          const errorMessage = uploadError instanceof Error ? uploadError.message : "Upload initiation failed";
          setUploadError(errorMessage);
          onUploadError(errorMessage);
          throw new Error(errorMessage);
      }
    },
    clearUploader: () => {
      if (uppy) {
        uppy.cancelAll();
        uppy.getFiles().forEach((file) => uppy.removeFile(file.id));
      }
      setSelectedFile(null);
      setSchemaComparisonResult(null);
      setIsUploading(false);
      setUploadProgress(0);
      setUploadError(null);
      onValidationStateChange("idle");
    },
  }));

  return (
    <div className="space-y-4">
      {/* --- Status Alerts --- */}
      {duckDbError && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Initialization Error</AlertTitle>
          <AlertDescription>
            In-browser validator (DuckDB) could not initialize: {String(duckDbError)}
          </AlertDescription>
        </Alert>
      )}
      {/* Uppy Dashboard */}
      <div className="border rounded-lg overflow-hidden bg-card">
        <div
          ref={dashboardRef}
          className={`uppy-theme-wrapper ${
            resolvedTheme === "dark" ? "uppy-theme-dark" : "uppy-theme-light"
          }`}
        />
      </div>

      {/* S3 Upload Progress & Error */}
      {isUploading && (
        <div className="space-y-2 pt-4">
          <div className="flex justify-between text-sm">
            <span>Uploading to storage...</span>
            <span>{uploadProgress}%</span>
          </div>
          <Progress value={uploadProgress} />
        </div>
      )}
      {uploadError && (
         <Alert variant="destructive" className="mt-4">
           <AlertCircle className="h-4 w-4" />
           <AlertTitle>Storage Upload Error</AlertTitle>
           <AlertDescription>{uploadError}</AlertDescription>
         </Alert>
       )}
    </div>
  );
});

RefreshFileUploader.displayName = "RefreshFileUploader";
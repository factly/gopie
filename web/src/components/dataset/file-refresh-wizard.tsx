"use client";

import * as React from "react";
import { useState, useCallback, useRef } from "react";
import { UppyFile, Meta } from "@uppy/core";
import { toast } from "sonner";
import {
  AlertCircle,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Stepper, StepperContent, Step } from "@/components/ui/stepper";
import {
  RefreshFileUploader, // Import the new uploader
  RefreshFileUploaderRef,
} from "@/components/dataset/refresh-file-uploader";
import { useQueryClient } from "@tanstack/react-query";
import { useUploadStore } from "@/lib/stores/uploadStore";
import { useDuckDb } from "@/hooks/useDuckDb";
import { CenteredLoading } from "@/components/ui/loading";
import { useSchema } from "@/lib/queries/dataset/get-schema";
import { ColumnInfo } from "@/lib/queries/dataset/get-schema"; // Assuming ColumnInfo is exported
import { useRefreshDataset } from "@/lib/mutations/dataset/refresh-dataset";
import { useParams } from "next/navigation";
import { useDatasetById } from "@/lib/queries/dataset/get-dataset-by-id";

// Simplified steps for the refresh flow
const REFRESH_STEPS: Step[] = [
  {
    id: "upload",
    title: "Validate & Upload ",
    description: "Select file and check schema",
  },
  {
    id: "confirm",
    title: "Confirm Refresh",
    description: "Upload and finalize",
  },
];

type ValidationStateType =
  | "idle"
  | "validating"
  | "schema_match"
  | "schema_mismatch"
  | "validation_error"
  | "no_schema_to_compare" // Added state
  | "validation_unavailable"; // Added state

export interface FileRefreshWizardProps {
  projectId: string;
  datasetId: string;
  onRefreshComplete: () => void;
}

export function FileRefreshWizard({
  projectId,
  onRefreshComplete,
}: FileRefreshWizardProps) {
  const refreshDataset = useRefreshDataset();
  const [currentStep, setCurrentStep] = useState(1);
  const { datasetId } = useParams() as {
    projectId: string;
    datasetId: string;
  };

  const { data: datasetData , isLoading } = useDatasetById({
        variables: { datasetId:datasetId },
        enabled: !!datasetId,
      });

  
  const [apiError, setApiError] = useState<string | null>(null); // For final API call errors
  const [isProcessingApi, setIsProcessingApi] = useState<boolean>(false);
  const [validationState, setValidationState] =
    useState<ValidationStateType>("idle");
  const [validationMessage, setValidationMessage] = useState<string | null>(
    null
  );

  // Store hooks for S3 response
  const setUploadResponse = useUploadStore((state) => state.setUploadResponse);
  const resetUploadState = useUploadStore((state) => state.resetUploadState);

  const uploaderRef = useRef<RefreshFileUploaderRef>(null);
  const queryClient = useQueryClient();

  const { isInitializing: isDuckDbInitializing } = useDuckDb();

  // 1. Fetch the existing dataset's schema
  const {
    data: existingSchemaData,
    isLoading: isLoadingSchema,
    isError: isSchemaError,
    error: schemaFetchError,
  } = useSchema({
    variables: { datasetId: datasetData?.name||''},
    enabled: !!datasetData?.name,
  });

  // 2. Callback for the RefreshFileUploader
  const handleValidationStateChange = useCallback(
    (state: ValidationStateType, message?: string) => {
      setValidationState(state);
      setValidationMessage(message || null);
      setApiError(null); // Clear API errors when validation state changes

      if (state === "schema_match") {
        // Allow moving to next step only on schema match
      } else {
        // If mismatch or error, stay on step 1
        if (currentStep !== 1) setCurrentStep(1);
      }
    },
    [currentStep] // Depend on currentStep to prevent unnecessary re-renders
  );
    const callRefreshApiEndpoint = useCallback(async () => {
    setIsProcessingApi(true);
    setApiError(null);
    let s3Url = "";

    try {
      // Get S3 URL from store
      const uploadResponse = useUploadStore.getState().uploadResponse;
      let uploadURL: string | undefined;

      if (uploadResponse && typeof uploadResponse === "object") {
        const response = uploadResponse as Record<string, unknown>;
        uploadURL = ((response as Record<string, unknown>).uploadURL ||
          (response as Record<string, unknown>).url ||
          (response.body as Record<string, unknown>)?.uploadURL ||
          (response.body as Record<string, unknown>)?.url ||
          (response.body as Record<string, unknown>)?.location ||
          (response.body as Record<string, unknown>)?.Location ||
          (response as Record<string, unknown>).Location) as string;
      }

      if (!uploadURL) {
        throw new Error("S3 URL not found after upload.");
      }

      // Parse S3 URL
      if (uploadURL.startsWith("s3://")) {
        s3Url = uploadURL;
      } else if (
        uploadURL.startsWith("http://") ||
        uploadURL.startsWith("https://")
      ) {
        const url = new URL(uploadURL);
        const pathParts = url.pathname.split("/").filter(Boolean);

        if (
          url.hostname.includes("s3") &&
          (url.hostname.includes("amazonaws.com") ||
            url.hostname.includes("wasabisys.com"))
        ) {
          // --- Handle standard S3 or Wasabi patterns ---
          if (url.hostname.startsWith("s3")) {
            // Format: https://s3.region.amazonaws.com/bucket/key
            const bucket = pathParts[0];
            const key = pathParts.slice(1).join("/");
            s3Url = `s3://${bucket}/${key}`;
          } else {
            // Format: https://bucket.s3.region.amazonaws.com/key
            const bucket = url.hostname.split(".")[0];
            const key = pathParts.join("/");
            s3Url = `s3://${bucket}/${key}`;
          }
        } else {
          // --- Handle MinIO / localhost / generic object storage ---
          if (pathParts.length >= 2) {
            const bucket = pathParts[0];
            const key = pathParts.slice(1).join("/");
            s3Url = `s3://${bucket}/${key}`;
          } else if (pathParts.length === 1) {
            s3Url = `s3://${pathParts[0]}`;
          } else {
            throw new Error("No path found in upload URL");
          }
        }
      } else {
        console.error("Unknown upload URL format:", uploadURL);
        throw new Error(`Invalid upload URL format: ${uploadURL}`);
      }

      toast.loading("Sending refresh request to server...", {
        id: "api-refresh",
      });
     console.log("datasetData", datasetData?.name)
      await refreshDataset.mutateAsync({
        datasetName: datasetData?.name||'',
        projectId: projectId,
        s3Url: s3Url,
        source: 'file'
      });
      toast.success("Dataset refresh complete!", { id: "api-refresh" });

      // Invalidate queries and call completion callback
      queryClient.invalidateQueries({ queryKey: ["project", projectId] });
      queryClient.invalidateQueries({ queryKey: ["datasets", projectId] });
      queryClient.invalidateQueries({ queryKey: ["get-schema", datasetData?.name] });
      queryClient.invalidateQueries({ queryKey: ["dataset", datasetData?.id] });

      resetUploadState();
      onRefreshComplete(); // Navigate back
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "An unknown error occurred.";
      setApiError(errorMessage);
      toast.error(`Refresh failed: ${errorMessage}`, { id: "api-refresh" });
    } finally {
      setIsProcessingApi(false);
    }
  }, [
  projectId,
  queryClient,
  refreshDataset,
  resetUploadState,
  onRefreshComplete,
  ]);

  // 3. Callback for the RefreshFileUploader (after S3 upload)
  const handleUploadComplete = useCallback(
    (_file: UppyFile<Meta, Record<string, never>>, response: unknown) => {
      setUploadResponse(response);
      // S3 upload is complete, now we can call the final API endpoint
      callRefreshApiEndpoint();
    },
    [setUploadResponse,callRefreshApiEndpoint,datasetData?.name] // Add callRefreshApiEndpoint to dependencies if needed, or define it inside useCallback
  );

  // 4. Function to call the final API endpoint





  // 5. Triggered by the "Confirm and Refresh" button
  const handleConfirmAndUpload = () => {
    if (uploaderRef.current && validationState === "schema_match") {
      setApiError(null); // Clear previous API error before starting
      uploaderRef.current.triggerUpload().catch((err) => {
        // Error during S3 upload trigger (e.g., file removed)
        setApiError(err.message || "Failed to start upload.");
        toast.error(err.message || "Failed to start upload.");
      });
      // The actual API call happens in handleUploadComplete after S3 finishes
    } else {
      toast.error(
        "Cannot start upload. Ensure a file with a matching schema is selected."
      );
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleNext = () => {
    // Only allow proceeding if schema matches
    if (validationState === "schema_match") {
      if (currentStep < REFRESH_STEPS.length) {
        setCurrentStep(currentStep + 1);
      }
    } else {
      toast.error("Please upload a file with a matching schema first.");
    }
  };

  const handleClearUpload = () => {
    if (uploaderRef.current) {
      uploaderRef.current.clearUploader();
    }
    resetUploadState();
    setApiError(null);
    setValidationState("idle");
    setValidationMessage(null);
    if (currentStep !== 1) setCurrentStep(1); // Go back to step 1
  };

  if (isDuckDbInitializing || isLoadingSchema) {
    return (
      <div className="container max-w-5xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
        <Stepper
          steps={REFRESH_STEPS}
          currentStep={currentStep}
          className="mb-8"
        />
        <div className="bg-card border rounded-lg p-6">
          <CenteredLoading
            text={
              isDuckDbInitializing
                ? "Initializing validator..."
                : "Loading dataset schema..."
            }
          />
        </div>
      </div>
    );
  }

  if (isSchemaError) {
    return (
      <Alert variant="destructive" className="mb-4">
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>Error Loading Schema</AlertTitle>
        <AlertDescription>
          Could not load the schema for the existing dataset. Please ensure the
          dataset exists and try again.
          <br />
          {schemaFetchError instanceof Error ? schemaFetchError.message : ""}
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="container max-w-5xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
      <Stepper
        steps={REFRESH_STEPS}
        currentStep={currentStep}
        className="mb-8"
      />
      <StepperContent>
        {/* Step 1: Upload File & Validate Schema */}
        <div style={{ display: currentStep === 1 ? "block" : "none" }}>
          <div className="space-y-6">
            <div className="flex justify-end items-center">
              {validationState !== "idle" &&
                validationState !== "validating" && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleClearUpload}
                    className="flex items-center gap-1.5"
                  >
                    <X className="h-3.5 w-3.5" />
                    Clear
                  </Button>
                )}
            </div>
            <div className="bg-card border p-6">
              <h2 className="text-xl font-semibold mb-1">
                Validate & Upload  File
              </h2>
              <p className="text-sm text-muted-foreground mb-4">
                Select the new file. Its schema (column names,order and data types) will be
                compared against the existing dataset.
              </p>

              {/* Status messages based on validationState */}
              {validationState === "validating" && (
                <Alert className="mb-4 border-blue-200 bg-blue-50 dark:bg-blue-950/30">
                  <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
                  <AlertTitle className="text-blue-800">
                    Validating...
                  </AlertTitle>
                  <AlertDescription className="text-blue-700">
                    Checking file format and schema.
                  </AlertDescription>
                </Alert>
              )}
              {validationState === "schema_mismatch" && (
                <Alert variant="destructive" className="mb-4">
                  <AlertCircle className="h-4 w-4" />
                  <AlertTitle>Schema Mismatch</AlertTitle>
                  <AlertDescription>
                    {validationMessage || "Schema does not match."}
                  </AlertDescription>
                </Alert>
              )}
              {validationState === "validation_error" && (
                <Alert variant="destructive" className="mb-4">
                  <AlertCircle className="h-4 w-4" />
                  <AlertTitle>Validation Error</AlertTitle>
                  <AlertDescription>
                    {validationMessage || "Could not validate file."}
                  </AlertDescription>
                </Alert>
              )}
              {validationState === "schema_match" && (
                <Alert className="mb-4 bg-green-50 dark:bg-green-950/30 border-green-200 dark:border-green-900">
                  <CheckCircle2 className="h-4 w-4 text-green-600 dark:text-green-400" />
                  <AlertTitle className="text-green-800 dark:text-green-200">
                    Schema Match Confirmed!
                  </AlertTitle>
                  <AlertDescription className="text-green-700 dark:text-green-300">
                    You can proceed to the next step.
                  </AlertDescription>
                </Alert>
              )}
              {validationState === "no_schema_to_compare" && (
                <Alert variant="destructive" className="mb-4">
                  <AlertCircle className="h-4 w-4" />
                  <AlertTitle>Schema Error</AlertTitle>
                  <AlertDescription>
                    Could not retrieve existing schema for comparison.
                  </AlertDescription>
                </Alert>
              )}
              {validationState === "validation_unavailable" && (
                <Alert variant="destructive" className="mb-4">
                  <AlertCircle className="h-4 w-4" />
                  <AlertTitle>Validation Unavailable</AlertTitle>
                  <AlertDescription>
                    Could not initialize in-browser validator (DuckDB).
                  </AlertDescription>
                </Alert>
              )}

              {<RefreshFileUploader
                ref={uploaderRef}
                existingSchema={existingSchemaData?.schema as ColumnInfo[]} // Pass existing schema
                onValidationStateChange={handleValidationStateChange}
                onUploadSuccess={handleUploadComplete}
                onUploadError={(msg) => setApiError(msg)} // S3 upload errors shown as API errors
              />}
            </div>
            <div className="flex justify-end items-center">
              <Button
                size="sm"
                onClick={handleNext}
                disabled={validationState !== "schema_match"}
              >
                Next
              </Button>
            </div>
          </div>
        </div>

        {/* Step 2: Confirm Refresh */}
        <div style={{ display: currentStep === 2 ? "block" : "none" }}>
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={handleBack}>
                  Back
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleClearUpload} // Allow clearing from confirm step too
                  className="flex items-center gap-1.5"
                >
                  <X className="h-3.5 w-3.5" />
                  Cancel
                </Button>
              </div>
              <Button
                size="sm"
                onClick={handleConfirmAndUpload}
                disabled={isProcessingApi || validationState !== "schema_match"}
              >
                {isProcessingApi ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    Refreshing...
                  </>
                ) : (
                  "Confirm and Refresh"
                )}
              </Button>
            </div>

            <div className="bg-card border p-6">
              <h2 className="text-xl font-semibold mb-4">Confirm Refresh</h2>
              <p className="text-sm text-muted-foreground">
                You are about to replace the data in dataset{" "}
                <strong>{datasetData?.name}</strong>. This action will upload the new
                file and trigger the refresh process on the server.
              </p>
              <Alert className="mt-4" variant="destructive">
                <AlertTriangle className="h-4 w-4" />
                <AlertTitle>This action is irreversible.</AlertTitle>
                <AlertDescription>
                  The current data in this dataset will be overwritten by the
                  contents of the new file.
                </AlertDescription>
              </Alert>
              {apiError && (
                <Alert variant="destructive" className="mt-4">
                  <AlertCircle className="h-4 w-4" />
                  <AlertTitle>Refresh Error</AlertTitle>
                  <AlertDescription>{apiError}</AlertDescription>
                </Alert>
              )}
            </div>
          </div>
        </div>
      </StepperContent>
    </div>
  );
}

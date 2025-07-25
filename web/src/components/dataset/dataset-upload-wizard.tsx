"use client";

import * as React from "react";
import { useState, useCallback, useRef } from "react";
import { UppyFile, Meta } from "@uppy/core";
import { toast } from "sonner";
import { AlertCircle, Database, Loader2, LinkIcon, CheckCircle2, AlertTriangle, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Stepper, StepperContent, Step } from "@/components/ui/stepper";
import { CsvValidationUppy, FileValidationUppyRef } from "@/components/dataset/csv-validation-uppy";
import { DatabaseSourceForm } from "@/components/dataset/database-source-form";
import { UrlUploader } from "@/components/dataset/url-uploader";
import { ColumnNameEditor } from "@/components/dataset/column-name-editor";
import { useRouter } from "next/navigation";
import { useSourceDataset } from "@/lib/mutations/dataset/source-dataset";
import { useGenerateColumnDescriptions } from "@/lib/mutations/ai/generate-column-descriptions";
import { useQueryClient } from "@tanstack/react-query";
import { useColumnNameStore } from "@/lib/stores/columnNameStore";
import { useColumnDescriptionStore } from "@/lib/stores/columnDescriptionStore";
import { ValidationResult } from "@/lib/validation/validate-file";
import { useUploadStore } from "@/lib/stores/uploadStore";


const WIZARD_STEPS: Step[] = [
  {
    id: "upload",
    title: "Upload Dataset",
    description: "Choose data source"
  },
  {
    id: "validate",
    title: "Validate Dataset", 
    description: "Review validation"
  },
  {
    id: "configure",
    title: "AI Readiness",
    description: "Configure columns"
  },
  {
    id: "confirm",
    title: "Confirmation",
    description: "Create dataset"
  }
];

export interface DatasetUploadWizardProps {
  projectId: string;
}

export function DatasetUploadWizard({ projectId }: DatasetUploadWizardProps) {
  const [currentStep, setCurrentStep] = useState(1);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [isGeneratingDescriptions, setIsGeneratingDescriptions] = useState<boolean>(false);
  const [createdDataset, setCreatedDataset] = useState<{
    id: string;
    alias: string;
    formatDisplay: string;
    columnMappings?: Record<string, string>;
    columnDescriptions?: Record<string, string>;
    validationResult?: ValidationResult;
  } | null>(null);
  
  // Dataset creation form state
  const [datasetNameTouched, setDatasetNameTouched] = useState<boolean>(false);
  const [datasetDescriptionTouched, setDatasetDescriptionTouched] = useState<boolean>(false);
  
  // Use upload store for persistent state
  const uploadedFile = useUploadStore((state) => state.uploadedFile);
  const validationResult = useUploadStore((state) => state.validationResult);
  const datasetName = useUploadStore((state) => state.datasetName);
  const datasetDescription = useUploadStore((state) => state.datasetDescription);
  const setUploadedFile = useUploadStore((state) => state.setUploadedFile);
  const setUploadResponse = useUploadStore((state) => state.setUploadResponse);
  const setValidationResult = useUploadStore((state) => state.setValidationResult);
  const setDatasetName = useUploadStore((state) => state.setDatasetName);
  const setDatasetDescription = useUploadStore((state) => state.setDatasetDescription);
  const resetUploadState = useUploadStore((state) => state.resetUploadState);
  
  // Database dialog state
  const [isDbDialogOpen, setIsDbDialogOpen] = useState(false);
  const [selectedDriver, setSelectedDriver] = useState<"postgres" | "mysql" | null>(null);
  const [isValidationWarningDialogOpen, setIsValidationWarningDialogOpen] = useState(false);
  
  // Ref for CSV validation component to trigger upload
  const csvValidationRef = useRef<FileValidationUppyRef>(null);
  // Track if we've auto-navigated to prevent re-navigation
  const hasAutoNavigatedRef = useRef(false);
  
  const sourceDataset = useSourceDataset();
  const queryClient = useQueryClient();
  const router = useRouter();
  
  const getColumnMappings = useColumnNameStore((state) => state.getColumnMappings);
  const getColumnDescriptions = useColumnDescriptionStore((state) => state.getColumnDescriptions);
  const setColumnDescription = useColumnDescriptionStore((state) => state.setColumnDescription);
  const resetColumnMappings = useColumnNameStore((state) => state.resetColumnMappings);
  const clearColumnDescriptions = useColumnDescriptionStore((state) => state.clearColumnDescriptions);
  const { mutateAsync: generateColumnDescriptions } = useGenerateColumnDescriptions();
  const setColumnMappings = useColumnNameStore((state) => state.setColumnMappings);
  
  const handleAutoGenerateDescriptions = useCallback(async (
    summary: Record<string, unknown>,
    rows: string[][]
  ) => {
    if (!summary || !rows || rows.length === 0) {
      return;
    }

    try {
      setIsGeneratingDescriptions(true);
      toast.loading("Generating AI column descriptions...", {
        id: "generate-descriptions",
      });

      const result = await generateColumnDescriptions({
        summary,
        rows,
      });

      if (result.descriptions) {
        // Auto-populate the column description store
        Object.entries(result.descriptions).forEach(
          ([columnName, description]) => {
            setColumnDescription(columnName, description);
          }
        );

        toast.success("Column descriptions generated successfully!", {
          id: "generate-descriptions",
        });
      }
    } catch (error) {
      const errorMessage =
        error instanceof Error
          ? error.message
          : "Failed to generate descriptions";
      toast.error(`Error generating descriptions: ${errorMessage}`, {
        id: "generate-descriptions",
      });
    } finally {
      setIsGeneratingDescriptions(false);
    }
  }, [generateColumnDescriptions, setColumnDescription]);

  const handleFileValidated = useCallback((file: UppyFile<Meta, Record<string, never>>, response: unknown, validation: ValidationResult) => {
    console.log('handleFileValidated called with:', { file: file?.name, validation, response });
    setUploadedFile(file);
    setValidationResult(validation);
    setUploadError(null);
    
    // If we have a response, it means the file was uploaded
    if (response) {
      console.log('File was uploaded, storing response');
      setUploadResponse(response);
    }
  }, [setUploadedFile, setValidationResult, setUploadResponse]);

  const handleUploadError = useCallback((error: string) => {
    setUploadError(error);
    setValidationResult(null);
    setUploadedFile(null);
    setUploadResponse(null);
  }, [setUploadedFile, setValidationResult, setUploadResponse]);

  const handleCreateDataset = async () => {
    if (!validationResult) {
      toast.error("No validation data available");
      return;
    }

    try {
      setUploadError(null);
      setIsProcessing(true);

      console.log('Starting dataset creation process...');
      console.log('Dataset name:', datasetName);
      console.log('Dataset description:', datasetDescription);
      
      // Check if we already have the upload response
      let uploadURL: string | undefined;
      const currentUploadResponse = useUploadStore.getState().uploadResponse;
      console.log('Current upload response from store:', currentUploadResponse);
      
      if (currentUploadResponse && typeof currentUploadResponse === 'object') {
        const response = currentUploadResponse as Record<string, unknown>;
        // S3 responses might have the URL in different places
        uploadURL = ((response as Record<string, unknown>).uploadURL || 
                   (response as Record<string, unknown>).url || 
                   (response.body as Record<string, unknown>)?.uploadURL || 
                   (response.body as Record<string, unknown>)?.url ||
                   (response.body as Record<string, unknown>)?.location ||
                   (response.body as Record<string, unknown>)?.Location ||
                   (response as Record<string, unknown>).Location) as string;
      }
      
      // If we don't have the URL yet, trigger upload through the CSV validation component
      if (!uploadURL && csvValidationRef.current) {
        console.log('No URL found, triggering S3 upload through CSV validation component...');
        
        try {
          // Show loading state
          toast.loading("Uploading file to S3...", { id: "s3-upload" });
          
          // Trigger the upload through the ref
          await csvValidationRef.current.triggerUpload(datasetName.trim(), datasetDescription.trim());
          
          // Wait a bit longer for the store to update with the upload response
          await new Promise(resolve => setTimeout(resolve, 2000));
          
          // Check again for the URL from the updated store
          const newUploadResponse = useUploadStore.getState().uploadResponse;
          console.log('New upload response after trigger:', newUploadResponse);
          
          if (newUploadResponse && typeof newUploadResponse === 'object') {
            const response = newUploadResponse as Record<string, unknown>;
            // Companion server typically returns the URL in body.uploadURL or body.location
            uploadURL = ((response as Record<string, unknown>).uploadURL || 
                       (response as Record<string, unknown>).url || 
                       (response.body as Record<string, unknown>)?.uploadURL || 
                       (response.body as Record<string, unknown>)?.url ||
                       (response.body as Record<string, unknown>)?.location ||  // Companion server uses lowercase
                       (response.body as Record<string, unknown>)?.Location ||  // S3 direct uses uppercase
                       (response as Record<string, unknown>).Location) as string;
          }
          
          if (!uploadURL) {
            toast.error("Failed to get S3 URL after upload", { id: "s3-upload" });
            throw new Error('File upload completed but S3 URL not found in response');
          }
          
          toast.success("File uploaded to S3 successfully!", { id: "s3-upload" });
        } catch (error) {
          console.error('Upload error:', error);
          toast.error(`Upload failed: ${error instanceof Error ? error.message : "Unknown error"}`, { id: "s3-upload" });
          throw error;
        }
      }
      
      if (!uploadURL) {
        throw new Error("No upload URL available. Please try uploading the file again.");
      }
      
      console.log('Extracted uploadURL:', uploadURL);
      
      // Construct S3 URL for dataset creation
      let s3Url = "";
      try {
        // Check if it's already an S3 URL
        if (uploadURL.startsWith('s3://')) {
          s3Url = uploadURL;
        } else if (uploadURL.startsWith('http://') || uploadURL.startsWith('https://')) {
          const url = new URL(uploadURL);
          console.log('Parsing URL:', {
            hostname: url.hostname,
            pathname: url.pathname,
            href: url.href
          });
          
          // Extract bucket and key from the URL
          // URL format: https://bucket.s3.region.amazonaws.com/path/to/file
          // or: https://bucket.s3.region.wasabisys.com/path/to/file
          // or: https://s3.region.amazonaws.com/bucket/path/to/file
          const pathParts = url.pathname.split('/').filter(part => part.length > 0);
          
          if (url.hostname.includes('s3') && (url.hostname.includes('amazonaws.com') || url.hostname.includes('wasabisys.com'))) {
            // Standard S3 or S3-compatible URL format
            if (url.hostname.startsWith('s3')) {
              // Format: https://s3.region.amazonaws.com/bucket/key
              // pathParts[0] is bucket, rest is key
              const bucket = pathParts[0];
              const key = pathParts.slice(1).join('/');
              s3Url = `s3://${bucket}/${key}`;
            } else {
              // Format: https://bucket.s3.region.amazonaws.com/key
              // or: https://bucket.s3.region.wasabisys.com/key
              const bucket = url.hostname.split('.')[0];
              const key = pathParts.join('/');
              s3Url = `s3://${bucket}/${key}`;
            }
          } else {
            // Non-S3 URL, might be MinIO, presigned URL, or proxy
            // For localhost:9000 (MinIO) or similar, the format is usually: http://localhost:9000/bucket/key
            // Try to extract path assuming format: /bucket/key
            if (pathParts.length >= 2) {
              const bucket = pathParts[0];
              const key = pathParts.slice(1).join('/');
              s3Url = `s3://${bucket}/${key}`;
              console.log('Parsed non-AWS S3 URL:', { bucket, key, s3Url });
            } else if (pathParts.length === 1) {
              // Only one path part, assume it's just the bucket
              s3Url = `s3://${pathParts[0]}`;
            } else {
              // No path parts, this shouldn't happen
              throw new Error('No path found in upload URL');
            }
          }
        } else {
          // Unknown format, log error
          console.error('Unknown upload URL format:', uploadURL);
          throw new Error('Invalid upload URL format');
        }
      } catch (error) {
        console.error('Error parsing upload URL:', error);
        // If we can't parse it, we can't proceed
        throw new Error(`Failed to parse S3 URL from upload response: ${uploadURL}`);
      }
      
      console.log('Final s3Url for dataset creation:', s3Url);
      
      // Get file format from validation result
      const fileFormat = validationResult.format || "csv";
      const formatDisplay = fileFormat.toUpperCase();

      // Use form data for dataset name and description
      const finalDatasetName = datasetName.trim();
      const finalDatasetDescription = datasetDescription.trim();
      const alter_column_names = getColumnMappings();
      const column_descriptions = getColumnDescriptions();

      const res = await sourceDataset.mutateAsync({
        datasetUrl: s3Url,
        projectId,
        alias: finalDatasetName,
        createdBy: "system",
        description: finalDatasetDescription,
        alter_column_names: alter_column_names,
        column_descriptions: column_descriptions,
      });

      if (!res?.data.dataset.id) {
        throw new Error("Invalid response from server: Dataset ID not found.");
      }

      setCreatedDataset({
        ...res.data.dataset,
        formatDisplay,
        columnMappings: alter_column_names,
        columnDescriptions: column_descriptions,
        validationResult
      });

      toast.success(
        `Dataset ${res.data.dataset.alias} (${formatDisplay}) created successfully`
      );
      queryClient.invalidateQueries({ queryKey: ["project", projectId] });
      queryClient.invalidateQueries({ queryKey: ["datasets", projectId] });

      // Clear upload store after successful creation
      resetUploadState();
      resetColumnMappings();
      clearColumnDescriptions();
      hasAutoNavigatedRef.current = false;

      // Dataset created successfully - stay in Step 4 but show success message
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "Unknown error occurred";
      setUploadError(errorMessage);
      toast.error(`Failed to source dataset: ${errorMessage}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDbSourceSuccess = (datasetAlias: string, datasetId: string) => {
    toast.success(
      `Dataset ${datasetAlias} (from ${selectedDriver}) created successfully`
    );
    queryClient.invalidateQueries({ queryKey: ["project", projectId] });
    queryClient.invalidateQueries({ queryKey: ["datasets", projectId] });
    setIsDbDialogOpen(false);
    setSelectedDriver(null);
    // Reset upload state when using database source
    resetUploadState();
    resetColumnMappings();
    clearColumnDescriptions();
    router.push(`/projects/${projectId}/datasets/${datasetId}`);
  };

  const handleDbSourceError = (errorMessage: string) => {
    toast.error(
      `Failed to create dataset from ${
        selectedDriver || "database"
      }: ${errorMessage}`
    );
  };

  const openDbDialog = (driver: "postgres" | "mysql") => {
    setSelectedDriver(driver);
    setUploadError(null);
    setIsDbDialogOpen(true);
  };

  const handleNext = () => {
    // Check if we're on step 2 (validation) and have data type warnings
    if (currentStep === 2 && validationResult?.rejectedRows && validationResult.rejectedRows.length > 0) {
      setIsValidationWarningDialogOpen(true);
      return;
    }
    
    if (currentStep < WIZARD_STEPS.length) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handleProceedWithWarnings = () => {
    setIsValidationWarningDialogOpen(false);
    if (currentStep < WIZARD_STEPS.length) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
      setUploadError(null);
      // Don't reset state when going back - user might want to modify something
    }
  };

  const handleClearUpload = () => {
    // Reset all upload-related state
    resetUploadState();
    setUploadError(null);
    setDatasetNameTouched(false);
    setDatasetDescriptionTouched(false);
    resetColumnMappings();
    clearColumnDescriptions();
    hasAutoNavigatedRef.current = false;
    
    // Reset to step 1
    setCurrentStep(1);
  };
  
  const handleFinish = () => {
    // Clean up stores
    resetColumnMappings();
    clearColumnDescriptions();
    
    if (createdDataset?.id) {
      router.push(`/projects/${projectId}/datasets/${createdDataset.id}`);
    } else {
      router.push(`/projects/${projectId}`);
    }
  };

  // const canProceedFromStep1 = uploadedFile && validationResult;
  const canProceedFromStep2 = validationResult;
  const canProceedFromStep3 = !isProcessing;

  // Ensure column store is populated when advancing to Step 3
  React.useEffect(() => {
    if (currentStep === 3 && validationResult?.columnNames?.length) {
      setColumnMappings(validationResult.columnNames, validationResult.columnTypes);
    }
  }, [currentStep, validationResult?.columnNames, validationResult?.columnTypes, setColumnMappings]);

  // Auto-generate descriptions when validation succeeds
  React.useEffect(() => {
    if (validationResult?.isValid && validationResult.previewData && !isGeneratingDescriptions && currentStep === 1) {
      const summary = {
        columns: validationResult.columnNames || [],
        rowCount: validationResult.previewRowCount || 0
      };
      handleAutoGenerateDescriptions(summary, validationResult.previewData as string[][]).catch(() => {
        // Ignore errors in auto-generation
      });
    }
  }, [validationResult, isGeneratingDescriptions, currentStep, handleAutoGenerateDescriptions]);

  return (
    <div className="container max-w-5xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
      <Stepper steps={WIZARD_STEPS} currentStep={currentStep} className="mb-8" />

      <StepperContent>
        {/* Keep CSV validation component mounted but hidden to preserve Uppy instance */}
        <div style={{ display: currentStep === 1 ? 'block' : 'none' }}>
          <div className="space-y-8">
            {/* Clear button when file is uploaded */}
            {uploadedFile && (
              <div className="flex justify-end">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleClearUpload}
                  className="flex items-center gap-1.5"
                >
                  <X className="h-3.5 w-3.5" />
                  Clear Upload
                </Button>
              </div>
            )}
            
            <div className="bg-card border p-6">
              {uploadError && (
                <Alert variant="destructive" className="mb-4">
                  <AlertCircle className="h-4 w-4" />
                  <AlertTitle>File Upload Error</AlertTitle>
                  <AlertDescription>{uploadError}</AlertDescription>
                </Alert>
              )}
              {isGeneratingDescriptions && (
                <Alert className="mb-4 bg-muted/50 border-muted-foreground/20">
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                  <AlertTitle>Generating Column Descriptions</AlertTitle>
                  <AlertDescription>
                    AI is analyzing your data to generate helpful column descriptions.
                    This may take a few moments...
                  </AlertDescription>
                </Alert>
              )}
              <CsvValidationUppy
                ref={csvValidationRef}
                projectId={projectId}
                onUploadSuccess={handleFileValidated}
                onUploadError={handleUploadError}
                onAutoGenerateDescriptions={handleAutoGenerateDescriptions}
                onValidationSuccess={() => {
                  if (!hasAutoNavigatedRef.current) {
                    hasAutoNavigatedRef.current = true;
                    setCurrentStep(2);
                  }
                }}
              />
            </div>

            <div className="bg-card border p-6">
              <h2 className="text-xl font-semibold mb-1 flex items-center">
                <LinkIcon className="h-5 w-5 mr-2" /> Import from URL
              </h2>
              <p className="text-sm text-muted-foreground mb-4">
                Import a dataset directly from a publicly accessible URL. Supports CSV, JSON, and other data formats.
              </p>
              <UrlUploader
                projectId={projectId}
                onUploadSuccess={handleFileValidated}
                onUploadError={handleUploadError}
                onAutoGenerateDescriptions={handleAutoGenerateDescriptions}
                onValidationSuccess={() => {
                  if (!hasAutoNavigatedRef.current) {
                    hasAutoNavigatedRef.current = true;
                    setCurrentStep(2);
                  }
                }}
              />
            </div>

            <div className="bg-card border p-6">
              <h2 className="text-xl font-semibold mb-1 flex items-center">
                <Database className="h-5 w-5 mr-2" /> Connect to Database
              </h2>
              <p className="text-sm text-muted-foreground mb-4">
                Create a dataset by connecting to your existing database or cloud storage.
              </p>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3 sm:gap-4">
                <div 
                  onClick={() => openDbDialog("postgres")} 
                  className="cursor-pointer group relative flex items-center justify-center py-3 sm:py-4 px-3 border rounded-lg hover:border-primary/50 hover:shadow-md transition-all duration-200 bg-muted/10 dark:bg-muted/20 aspect-[2/1] min-h-[60px]"
                >
                  <img src="/images/databases/postgres.svg" alt="PostgreSQL" className="w-full h-3/4 object-contain dark:brightness-90" />
                </div>
                <div 
                  onClick={() => openDbDialog("mysql")} 
                  className="cursor-pointer group relative flex items-center justify-center py-3 sm:py-4 px-3 border rounded-lg hover:border-primary/50 hover:shadow-md transition-all duration-200 bg-muted/10 dark:bg-muted/20 aspect-[2/1] min-h-[60px]"
                >
                  <img src="/images/databases/mysql.svg" alt="MySQL" className="w-full h-3/4 object-contain dark:brightness-90" />
                </div>
                <div className="cursor-pointer group relative flex items-center justify-center py-3 sm:py-4 px-3 border rounded-lg hover:border-primary/50 hover:shadow-md transition-all duration-200 bg-muted/10 dark:bg-muted/20 aspect-[2/1] min-h-[60px]">
                  <div className="absolute top-1 left-1 bg-muted text-muted-foreground text-xs px-2 py-0.5 rounded-md font-medium opacity-0 group-hover:opacity-100 transition-opacity duration-200">Coming Soon</div>
                  <img src="/images/databases/snowflake.svg" alt="Snowflake" className="w-full h-3/4 object-contain dark:brightness-90" />
                </div>
                <div className="cursor-pointer group relative flex items-center justify-center py-3 sm:py-4 px-3 border rounded-lg hover:border-primary/50 hover:shadow-md transition-all duration-200 bg-muted/10 dark:bg-muted/20 aspect-[2/1] min-h-[60px]">
                  <div className="absolute top-1 left-1 bg-muted text-muted-foreground text-xs px-2 py-0.5 rounded-md font-medium opacity-0 group-hover:opacity-100 transition-opacity duration-200">Coming Soon</div>
                  <img src="/images/databases/google-big-query.svg" alt="BigQuery" className="w-full h-3/4 object-contain dark:brightness-90" />
                </div>
                <div className="cursor-pointer group relative flex items-center justify-center py-3 sm:py-4 px-3 border rounded-lg hover:border-primary/50 hover:shadow-md transition-all duration-200 bg-muted/10 dark:bg-muted/20 aspect-[2/1] min-h-[60px]">
                  <div className="absolute top-1 left-1 bg-muted text-muted-foreground text-xs px-2 py-0.5 rounded-md font-medium opacity-0 group-hover:opacity-100 transition-opacity duration-200">Coming Soon</div>
                  <img src="/images/databases/amazon-redshift.svg" alt="Redshift" className="w-full h-3/4 object-contain dark:brightness-90" />
                </div>
                <div className="cursor-pointer group relative flex items-center justify-center py-3 sm:py-4 px-3 border rounded-lg hover:border-primary/50 hover:shadow-md transition-all duration-200 bg-muted/10 dark:bg-muted/20 aspect-[2/1] min-h-[60px]">
                  <div className="absolute top-1 left-1 bg-muted text-muted-foreground text-xs px-2 py-0.5 rounded-md font-medium opacity-0 group-hover:opacity-100 transition-opacity duration-200">Coming Soon</div>
                  <img src="/images/databases/amazon-s3.svg" alt="Amazon S3" className="w-full h-3/4 object-contain dark:brightness-90" />
                </div>
                <div className="cursor-pointer group relative flex items-center justify-center py-3 sm:py-4 px-3 border rounded-lg hover:border-primary/50 hover:shadow-md transition-all duration-200 bg-muted/10 dark:bg-muted/20 aspect-[2/1] min-h-[60px]">
                  <div className="absolute top-1 left-1 bg-muted text-muted-foreground text-xs px-2 py-0.5 rounded-md font-medium opacity-0 group-hover:opacity-100 transition-opacity duration-200">Coming Soon</div>
                  <img src="/images/databases/azure-blob-storage.svg" alt="Azure Blob" className="w-full h-3/4 object-contain dark:brightness-90" />
                </div>
                <div className="cursor-pointer group relative flex items-center justify-center py-3 sm:py-4 px-3 border rounded-lg hover:border-primary/50 hover:shadow-md transition-all duration-200 bg-muted/10 dark:bg-muted/20 aspect-[2/1] min-h-[60px]">
                  <div className="absolute top-1 left-1 bg-muted text-muted-foreground text-xs px-2 py-0.5 rounded-md font-medium opacity-0 group-hover:opacity-100 transition-opacity duration-200">Coming Soon</div>
                  <img src="/images/databases/gcs.svg" alt="Google Cloud Storage" className="w-full h-3/4 object-contain dark:brightness-90" />
                </div>
                <div className="cursor-pointer group relative flex items-center justify-center py-3 sm:py-4 px-3 border rounded-lg hover:border-primary/50 hover:shadow-md transition-all duration-200 bg-muted/10 dark:bg-muted/20 aspect-[2/1] min-h-[60px]">
                  <div className="absolute top-1 left-1 bg-muted text-muted-foreground text-xs px-2 py-0.5 rounded-md font-medium opacity-0 group-hover:opacity-100 transition-opacity duration-200">Coming Soon</div>
                  <img src="/images/databases/duckdb.svg" alt="DuckDB" className="w-full h-3/4 object-contain dark:brightness-90" />
                </div>
                <div className="cursor-pointer group relative flex items-center justify-center py-3 sm:py-4 px-3 border rounded-lg hover:border-primary/50 hover:shadow-md transition-all duration-200 bg-muted/10 dark:bg-muted/20 aspect-[2/1] min-h-[60px]">
                  <div className="absolute top-1 left-1 bg-muted text-muted-foreground text-xs px-2 py-0.5 rounded-md font-medium opacity-0 group-hover:opacity-100 transition-opacity duration-200">Coming Soon</div>
                  <img src="/images/databases/motherduck.svg" alt="MotherDuck" className="w-full h-3/4 object-contain dark:brightness-90" />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Step 2: Dataset Validation */}
        <div style={{ display: currentStep === 2 ? 'block' : 'none' }}>
          <div className="space-y-6">
            {/* Top Navigation */}
            <div className="flex justify-between items-center">
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={handleBack}>
                  Back
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleClearUpload}
                  className="flex items-center gap-1.5"
                >
                  <X className="h-3.5 w-3.5" />
                  Cancel Upload
                </Button>
              </div>
              <Button 
                size="sm"
                onClick={handleNext}
                disabled={!canProceedFromStep2}
              >
                Next
              </Button>
            </div>
            
            <div className="bg-card border p-6">
              <h2 className="text-xl font-semibold mb-4">Validation Results</h2>
              
              {!validationResult ? (
                <div className="text-center py-8 text-muted-foreground">
                  <p>No validation data available. Please go back and upload a file.</p>
                </div>
              ) : (
                <>
              {/* Success Alert */}
                <Alert className="mb-4 bg-green-50 dark:bg-green-950/30 border-green-200 dark:border-green-900">
                  <CheckCircle2 className="h-4 w-4 text-green-600 dark:text-green-400" />
                  <AlertTitle className="text-green-800 dark:text-green-200">DuckDB {validationResult.format?.toUpperCase()} Validation Successful</AlertTitle>
                  <AlertDescription className="text-green-700 dark:text-green-300">
                    {validationResult.format?.toUpperCase()} file is valid with {validationResult.columnNames?.length || 0} columns:
                    <div className="mt-2 text-sm font-mono">
                      {validationResult.columnNames?.join(", ")}
                    </div>
                  </AlertDescription>
                </Alert>

              {/* Data Type Warnings (if any) */}
              {validationResult?.rejectedRows && validationResult.rejectedRows.length > 0 && (
                <Alert className="mb-4 bg-yellow-50 dark:bg-yellow-950/30 border-yellow-200 dark:border-yellow-900">
                  <AlertTriangle className="h-4 w-4 text-yellow-600 dark:text-yellow-400" />
                  <AlertTitle className="text-yellow-800 dark:text-yellow-200">Data Type Validation Warnings</AlertTitle>
                  <AlertDescription className="text-yellow-700 dark:text-yellow-300">
                    {validationResult.rejectedRows.length} row(s) contain data that doesn&apos;t match the expected types and will be excluded from the dataset:
                    <div className="mt-2 space-y-1 text-sm">
                      {validationResult?.rejectedRows?.slice(0, 5).map((error, index) => (
                        <div key={index} className="bg-yellow-100 dark:bg-yellow-900/50 p-2 rounded border border-yellow-300 dark:border-yellow-800">
                          <div className="font-medium text-yellow-800 dark:text-yellow-200">Row {error.rowNumber}: Column &apos;{error.columnName}&apos; expected a {error.expectedType} type but is empty</div>
                          <div className="text-xs text-yellow-600 dark:text-yellow-400">Error when converting column &apos;{error.columnName}&apos;: Could not convert string &apos;Uncontested&apos; to &apos;DOUBLE&apos;</div>
                        </div>
                      ))}
                      {validationResult?.rejectedRows && validationResult.rejectedRows.length > 5 && (
                        <div className="text-sm text-yellow-600 dark:text-yellow-400">
                          ... and {validationResult.rejectedRows.length - 5} more issue(s)
                        </div>
                      )}
                    </div>
                    <div className="mt-3 text-sm text-yellow-700 dark:text-yellow-300">
                      You can proceed with the upload (rejected rows will be skipped) or fix the data and try again.
                    </div>
                  </AlertDescription>
                </Alert>
              )}
              </>
              )}

            </div>
          </div>
        </div>

        {/* Step 3: AI Readiness */}
        <div style={{ display: currentStep === 3 ? 'block' : 'none' }}>
          <div className="space-y-6">
            {/* Top Navigation */}
            <div className="flex justify-between items-center">
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={handleBack}>
                  Back
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleClearUpload}
                  className="flex items-center gap-1.5"
                >
                  <X className="h-3.5 w-3.5" />
                  Cancel Upload
                </Button>
              </div>
              <Button 
                size="sm"
                onClick={handleNext}
                disabled={!canProceedFromStep3}
              >
                Next
              </Button>
            </div>
            
            <div className="bg-card border p-6">
              <h2 className="text-xl font-semibold mb-4">Configure Columns for AI Readiness</h2>
              <p className="text-sm text-muted-foreground mb-4">
                Review and edit column names, data types, and descriptions to optimize your dataset for AI analysis.
              </p>
              
              {isProcessing && (
                <Alert className="mb-4 bg-primary/10 border-primary/20">
                  <Loader2 className="h-4 w-4 animate-spin text-primary" />
                  <AlertTitle>Creating Dataset</AlertTitle>
                  <AlertDescription>
                    Your dataset is being created on the server. This may take a few moments...
                  </AlertDescription>
                </Alert>
              )}

              <ColumnNameEditor />
            </div>
          </div>
        </div>

        {/* Step 4: Dataset Details */}
        <div style={{ display: currentStep === 4 && !createdDataset ? 'block' : 'none' }}>
          <div className="space-y-6">
            {/* Top Navigation */}
            <div className="flex justify-between items-center">
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={handleBack}>
                  Back
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleClearUpload}
                  className="flex items-center gap-1.5"
                >
                  <X className="h-3.5 w-3.5" />
                  Cancel Upload
                </Button>
              </div>
              <Button 
                size="sm"
                onClick={handleCreateDataset}
                disabled={!datasetName.trim() || datasetDescription.length < 10 || isProcessing}
              >
                {isProcessing ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    Creating Dataset...
                  </>
                ) : (
                  "Create Dataset"
                )}
              </Button>
            </div>
            
            <div className="bg-card border p-6">
              <h2 className="text-xl font-semibold mb-4">Dataset Details</h2>
              <p className="text-sm text-muted-foreground mb-6">
                Provide a name and description for your dataset before creating it.
              </p>
              
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="dataset-name">Dataset Name *</Label>
                  <Input
                    id="dataset-name"
                    placeholder="Enter dataset name"
                    value={datasetName}
                    onChange={(e) => setDatasetName(e.target.value)}
                    onBlur={() => setDatasetNameTouched(true)}
                    className={datasetNameTouched && !datasetName.trim() ? "border-red-300" : ""}
                  />
                  {datasetNameTouched && !datasetName.trim() && (
                    <p className="text-sm text-red-600">Dataset name is required</p>
                  )}
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="dataset-description">Description *</Label>
                  <Textarea
                    id="dataset-description"
                    placeholder="Enter dataset description"
                    value={datasetDescription}
                    onChange={(e) => setDatasetDescription(e.target.value)}
                    onBlur={() => setDatasetDescriptionTouched(true)}
                    rows={3}
                    className={datasetDescriptionTouched && datasetDescription.length < 10 ? "border-red-300" : ""}
                  />
                  {datasetDescriptionTouched && datasetDescription.length < 10 && (
                    <p className="text-sm text-red-600">Description must be at least 10 characters</p>
                  )}
                </div>
              </div>

            </div>
          </div>
        </div>
        
        {/* Step 4: Success Message (after dataset creation) */}
        <div style={{ display: currentStep === 4 && createdDataset ? 'block' : 'none' }}>
          <div className="space-y-6">
            <div className="bg-card border p-6">
              <div className="text-center space-y-4">
                <CheckCircle2 className="h-16 w-16 text-green-600 mx-auto" />
                <h2 className="text-2xl font-semibold text-green-800">Dataset Created Successfully!</h2>
                <p className="text-muted-foreground">
                  Your dataset has been uploaded and is ready for analysis.
                </p>
                <div className="pt-4">
                  <Button onClick={handleFinish}>
                    View Dataset
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </StepperContent>



      <Dialog open={isDbDialogOpen} onOpenChange={setIsDbDialogOpen}>
        <DialogContent className="sm:max-w-lg">
          {selectedDriver && (
            <DatabaseSourceForm
              projectId={projectId}
              driver={selectedDriver}
              onCloseDialog={() => {
                setIsDbDialogOpen(false);
                setSelectedDriver(null);
              }}
              onSuccess={handleDbSourceSuccess}
              onError={handleDbSourceError}
            />
          )}
        </DialogContent>
      </Dialog>

      {/* Validation Warning Dialog */}
      <Dialog open={isValidationWarningDialogOpen} onOpenChange={setIsValidationWarningDialogOpen}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-yellow-600" />
              Data Type Validation Warnings
            </DialogTitle>
            <DialogDescription>
              Some rows in your dataset contain data that doesn&apos;t match the expected types.
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4">
            <div className="bg-yellow-50 dark:bg-yellow-950/30 border border-yellow-200 dark:border-yellow-900 rounded-lg p-4">
              <div className="text-sm text-yellow-800 dark:text-yellow-200 mb-3">
                <strong>{validationResult?.rejectedRows?.length || 0} row(s)</strong> will be excluded from your dataset due to data type mismatches:
              </div>
              
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {validationResult?.rejectedRows?.slice(0, 5).map((error, index) => (
                  <div key={index} className="bg-yellow-100 dark:bg-yellow-900/50 p-2 rounded border border-yellow-300 dark:border-yellow-800">
                    <div className="font-medium text-yellow-800 dark:text-yellow-200 text-sm">
                      Row {error.rowNumber}: Column &apos;{error.columnName}&apos; expected a {error.expectedType} type but is empty
                    </div>
                    <div className="text-xs text-yellow-600 dark:text-yellow-400 mt-1">
                      Error when converting column &apos;{error.columnName}&apos;: Could not convert string &apos;Uncontested&apos; to &apos;DOUBLE&apos;
                    </div>
                  </div>
                ))}
                {validationResult?.rejectedRows && validationResult.rejectedRows.length > 5 && (
                  <div className="text-sm text-yellow-600 dark:text-yellow-400 font-medium">
                    ... and {validationResult.rejectedRows.length - 5} more issue(s)
                  </div>
                )}
              </div>
            </div>
            
            <div className="bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-900 rounded-lg p-4">
              <div className="text-sm text-blue-800 dark:text-blue-200">
                <strong>What happens if you continue:</strong>
                <ul className="mt-2 space-y-1 list-disc list-inside">
                  <li>Rows with data type issues will be automatically skipped</li>
                  <li>Your dataset will be created with the remaining valid rows</li>
                </ul>
              </div>
            </div>
          </div>
          
          <div className="flex justify-end gap-3 pt-4">
            <Button 
              variant="outline" 
              onClick={() => setIsValidationWarningDialogOpen(false)}
            >
              Go Back to Fix Data
            </Button>
            <Button 
              onClick={handleProceedWithWarnings}
              className="bg-yellow-600 hover:bg-yellow-700"
            >
              Continue with {validationResult?.rejectedRows?.length || 0} Rows Skipped
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

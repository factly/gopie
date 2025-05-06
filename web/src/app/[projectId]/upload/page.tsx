"use client";

import * as React from "react";
import { useState } from "react";
import { UppyFile, Meta } from "@uppy/core";
import { toast } from "sonner";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import "@uppy/core/dist/style.css";
import "@uppy/dashboard/dist/style.css";
import { useSourceDataset } from "@/lib/mutations/dataset/source-dataset";
import { useQueryClient } from "@tanstack/react-query";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { AlertCircle } from "lucide-react";
import { CsvValidationUppy } from "@/components/dataset/csv-validation-uppy";
import { useRouter } from "next/navigation";
import { useColumnNameStore } from "@/lib/stores/columnNameStore";

export default function UploadDatasetPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  // Unwrap params Promise with React.use()
  const { projectId } = React.use(params);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const sourceDataset = useSourceDataset();
  const queryClient = useQueryClient();
  const router = useRouter();
  const getColumnMappings = useColumnNameStore(
    (state) => state.getColumnMappings
  );

  const handleUploadSuccess = async (
    file: UppyFile<Meta, Record<string, never>>,
    response: unknown
  ) => {
    if (!file) {
      toast.error("No file data available");
      setUploadError("No file data available");
      return;
    }

    try {
      setUploadError(null);

      // Extract s3Url from response
      const uploadURL = (response as { uploadURL?: string })?.uploadURL;
      const s3Url = uploadURL ? `s3:/${new URL(uploadURL).pathname}` : "";

      // Get dataset name and description from file metadata if available
      const datasetName =
        file.meta.datasetName?.toString() ||
        file.meta.alias?.toString() ||
        (file.name || "dataset").replace(/\.csv$/, "");
      const datasetDescription =
        file.meta.description?.toString() || "Uploaded from GoPie Web";

      console.log("File metadata:", file.meta);
      console.log("Dataset name being used:", datasetName);

      // Get the column name mappings
      const alter_column_names = getColumnMappings();

      const res = await sourceDataset.mutateAsync({
        datasetUrl: s3Url,
        projectId,
        alias: datasetName,
        createdBy: "system",
        description: datasetDescription,
        alter_column_names: alter_column_names,
      });

      if (!res?.data.dataset.name) {
        throw new Error("Invalid response from server");
      }

      toast.success(`Dataset ${datasetName} uploaded successfully`);
      queryClient.invalidateQueries({
        queryKey: ["project"],
      });
      queryClient.invalidateQueries({
        queryKey: ["datasets"],
      });

      // Navigate back to project page after successful upload
      router.push(`/${projectId}`);
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "Unknown error occurred";

      setUploadError(errorMessage);

      if (
        error instanceof Error &&
        error.message.includes("add dataset to project")
      ) {
        toast.error(`Failed to add dataset to project: ${errorMessage}`);
      } else {
        toast.error(`Failed to source dataset: ${errorMessage}`);
      }
    }
  };

  return (
    <div className="container max-w-3xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
      <div className="mb-6">
        <Button
          variant="ghost"
          size="sm"
          className="flex items-center gap-1 mb-4"
          onClick={() => router.push(`/${projectId}`)}
        >
          <ArrowLeft className="h-4 w-4" />
          Back to project
        </Button>

        <h1 className="text-2xl font-semibold">Upload Dataset</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Upload a CSV file to create a new dataset for your project
        </p>
      </div>

      <div className="bg-card border rounded-lg p-6">
        {uploadError && (
          <Alert variant="destructive" className="mb-4">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Upload Error</AlertTitle>
            <AlertDescription>{uploadError}</AlertDescription>
          </Alert>
        )}

        <CsvValidationUppy
          projectId={projectId}
          onUploadSuccess={handleUploadSuccess}
          width="100%"
        />
      </div>
    </div>
  );
}

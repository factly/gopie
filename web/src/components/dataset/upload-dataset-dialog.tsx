"use client";

import { useState } from "react";
import { UppyFile, Meta } from "@uppy/core";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { UploadIcon } from "lucide-react";
import { toast } from "sonner";
import "@uppy/core/dist/style.css";
import "@uppy/dashboard/dist/style.css";
import { useSourceDataset } from "@/lib/mutations/dataset/source-dataset";
import { useQueryClient } from "@tanstack/react-query";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { AlertCircle } from "lucide-react";
import { CsvValidationUppy } from "./csv-validation-uppy";

export function UploadDatasetDialog({ projectId }: { projectId: string }) {
  const [open, setOpen] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const sourceDataset = useSourceDataset();
  const queryClient = useQueryClient();

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

      const res = await sourceDataset.mutateAsync({
        datasetUrl: s3Url,
        projectId,
        alias: (file.name || "dataset").replace(/\.csv$/, ""),
        createdBy: "system",
      });

      if (!res?.data.name) {
        throw new Error("Invalid response from server");
      }

      toast.success(`Dataset ${file.name} uploaded successfully`);
      queryClient.invalidateQueries({
        queryKey: ["project"],
      });
      queryClient.invalidateQueries({
        queryKey: ["datasets"],
      });
      setOpen(false);
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
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm" className="h-9">
          <UploadIcon className="mr-2 size-4" />
          Upload Dataset
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-xl">
        <DialogHeader className="pb-4 border-b">
          <DialogTitle className="text-xl font-semibold">
            Upload Dataset
          </DialogTitle>
          <p className="text-sm text-muted-foreground mt-1">
            Upload a CSV file to create a new dataset for your project
          </p>
        </DialogHeader>
        <div className="max-h-[70vh] overflow-y-auto py-4">
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
            height={400}
            width="100%"
            metaFields={[
              {
                id: "description",
                name: "Description",
                placeholder: "Describe the contents of your dataset...",
              },
            ]}
          />
        </div>
      </DialogContent>
    </Dialog>
  );
}

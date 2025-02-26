"use client";

import { useState } from "react";
import Uppy, { UppyFile, Meta } from "@uppy/core";
import AwsS3 from "@uppy/aws-s3";
import { Dashboard } from "@uppy/react";
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
import { useAddDatasetToProject } from "@/lib/mutations/project/add-dataset";
import { useQueryClient } from "@tanstack/react-query";

function sanitizeFileName(name: string): string {
  // Remove non-alphanumeric characters except for dots and hyphens
  return name.replace(/[^a-zA-Z0-9.-]/g, "_");
}

export function UploadDatasetDialog({ projectId }: { projectId: string }) {
  const [open, setOpen] = useState(false);
  const sourceDataset = useSourceDataset();
  const addDatasetToProject = useAddDatasetToProject();
  const queryClient = useQueryClient();

  const uppy = new Uppy({
    id: "dataset-uploader",
    restrictions: {
      maxNumberOfFiles: 1,
      allowedFileTypes: ["text/csv", ".csv"],
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

  uppy.use(AwsS3, {
    endpoint: process.env.NEXT_PUBLIC_COMPANION_URL || "http://localhost:3020",
  });

  uppy.on("upload-success", async (file, response) => {
    if (!file) {
      toast.error("No file data available");
      return;
    }

    try {
      const s3Url = response.uploadURL
        ? `s3:/${new URL(response.uploadURL).pathname}`
        : "";
      const res = await sourceDataset.mutateAsync({
        datasetUrl: s3Url,
        projectId,
        alias: (file.name || "dataset").replace(/\.csv$/, ""),
        createdBy: "system",
      });

      if (!res?.tableName) {
        throw new Error("Invalid response from server");
      }

      await addDatasetToProject.mutateAsync({
        projectId,
        datasetId: res.tableName,
      });

      toast.success(`Dataset ${file.name} uploaded successfully`);
      queryClient.invalidateQueries({
        queryKey: ["project"],
      });
      setOpen(false);
      uppy.cancelAll();
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "Unknown error occurred";

      if (
        error instanceof Error &&
        error.message.includes("add dataset to project")
      ) {
        toast.error(`Failed to add dataset to project: ${errorMessage}`);
      } else {
        toast.error(`Failed to source dataset: ${errorMessage}`);
      }

      uppy.cancelAll();
    }
  });

  uppy.on("upload-error", (file, error) => {
    toast.error(`Upload failed: ${error.message}`);
  });

  uppy.on("restriction-failed", (file, error) => {
    toast.error(error.message);
  });

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
          <Dashboard
            uppy={uppy}
            proudlyDisplayPoweredByUppy={false}
            showRemoveButtonAfterComplete={true}
            height={400}
            width="100%"
            theme="light"
            className="!bg-background !border-border !shadow-none rounded-lg"
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

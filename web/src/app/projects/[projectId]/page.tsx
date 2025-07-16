"use client";

import * as React from "react";
import { useProject } from "@/lib/queries/project/get-project";
import { Skeleton } from "@/components/ui/skeleton";
import { TableIcon, UploadIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DatasetCard } from "@/components/dataset/dataset-card";
import { motion } from "framer-motion";
import { useDatasets } from "@/lib/queries/dataset/list-datasets";
import { deleteDataset } from "@/lib/mutations/dataset/delete-dataset";
import { useToast } from "@/hooks/use-toast";
import { useQueryClient } from "@tanstack/react-query";
import { InlineProjectEditor } from "@/components/project/inline-project-editor";
import Link from "next/link";

export default function ProjectPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = React.use(params);
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const {
    data: project,
    isLoading,
    error,
  } = useProject({
    variables: {
      projectId,
    },
  });

  const { data: datasets } = useDatasets({
    variables: {
      projectId,
    },
  });

  const handleDeleteDataset = async (datasetId: string) => {
    try {
      await deleteDataset(projectId, datasetId);
      await queryClient.invalidateQueries({
        queryKey: ["datasets"],
      });
      toast({
        title: "Dataset deleted",
        description: "The dataset has been deleted successfully.",
      });
    } catch (error) {
      console.error(error);
      toast({
        title: "Error",
        description: "Failed to delete dataset. Please try again.",
        variant: "destructive",
      });
    }
  };

  if (isLoading) {
    return (
      <div className="container max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8 space-y-8">
        {/* Project header */}
        <div className="space-y-4">
          <Skeleton className="h-[44px] w-[300px]" /> {/* Title */}
          <Skeleton className="h-[28px] w-full max-w-[800px]" />{" "}
          {/* Description */}
        </div>

        {/* Datasets section */}
        <div className="pt-8">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-2">
              <Skeleton className="h-[32px] w-[100px]" /> {/* Datasets text */}
              <Skeleton className="h-[22px] w-[30px]" />{" "}
              {/* Count badge */}
            </div>
            <Skeleton className="h-9 w-[135px]" /> {/* Upload button */}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="space-y-3">
                <Skeleton className="h-[28px] w-3/4" /> {/* Dataset name */}
                <Skeleton className="h-[20px] w-1/2" /> {/* Dataset info */}
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
        <div className="border border-destructive/50 bg-destructive/5 p-4">
          <h2 className="text-lg font-semibold text-destructive">Error</h2>
          <p className="text-sm text-destructive/80">{error.message}</p>
        </div>
      </div>
    );
  }

  if (!project) return null;

  return (
    <div className="mx-auto py-8 px-4 sm:px-6 lg:px-8 space-y-8">
      <InlineProjectEditor project={project} />

      <div className="pt-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-medium tracking-tight text-foreground/90 flex items-center">
            Datasets
            <Badge variant="secondary" className="ml-2 font-normal">
              {datasets?.total || 0}
            </Badge>
          </h2>
          <Link href={`/projects/${projectId}/upload`}>
            <Button size="sm" className="h-9">
              <UploadIcon className="mr-2 size-4" />
              Create Dataset
            </Button>
          </Link>
        </div>

        {datasets?.total === 0 ? (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex flex-col items-center justify-center py-16 space-y-4 border bg-muted/50"
          >
            <TableIcon className="h-8 w-8 text-muted-foreground" />
            <p className="text-base text-muted-foreground">
              No datasets added yet
            </p>
            <Link href={`/projects/${projectId}/upload`}>
              <Button size="sm" className="h-9">
                <UploadIcon className="mr-2 size-4" />
                Create Dataset
              </Button>
            </Link>
          </motion.div>
        ) : (
          <motion.div
            className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            {datasets?.results?.map((dataset, idx) => (
              <motion.div
                key={dataset.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.1 }}
              >
                <DatasetCard
                  dataset={dataset}
                  projectId={projectId}
                  onDelete={handleDeleteDataset}
                />
              </motion.div>
            ))}
          </motion.div>
        )}
      </div>
    </div>
  );
}

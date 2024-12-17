"use client";

import * as React from "react";
import { useProject } from "@/lib/queries/project/get-project";
import { Skeleton } from "@/components/ui/skeleton";
import { FolderIcon, UploadIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export default function ProjectPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = React.use(params);
  const {
    data: project,
    isLoading,
    error,
  } = useProject({
    variables: {
      projectId,
    },
  });

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
              <Skeleton className="h-[22px] w-[30px] rounded-full" />{" "}
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
        <div className="rounded-lg border border-destructive/50 bg-destructive/5 p-4">
          <h2 className="text-lg font-semibold text-destructive">Error</h2>
          <p className="text-sm text-destructive/80">{error.message}</p>
        </div>
      </div>
    );
  }

  if (!project) return null;

  return (
    <div className="container max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8 space-y-8">
      <div className="space-y-4">
        <h1 className="text-4xl font-semibold tracking-tight text-foreground/90">
          {project.name}
        </h1>
        {project.description && (
          <p className="text-lg text-muted-foreground/90 max-w-[800px]">
            {project.description}
          </p>
        )}
      </div>

      <div className="pt-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-medium tracking-tight text-foreground/90 flex items-center">
            Datasets
            <Badge variant="secondary" className="ml-2 font-normal">
              {project.datasets?.length}
            </Badge>
          </h2>
          <Button size="sm" className="h-9">
            <UploadIcon className="mr-2 size-4" />
            Upload Dataset
          </Button>
        </div>

        {project.datasets?.length === 0 ? (
          <div className="text-muted-foreground text-base">
            No datasets added yet
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Dataset cards will go here */}
          </div>
        )}
      </div>
    </div>
  );
}

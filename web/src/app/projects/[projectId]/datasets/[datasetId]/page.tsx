"use client";

import * as React from "react";
import { motion } from "framer-motion";
import { DataPreview } from "@/components/dataset/data-preview";
import { Skeleton } from "@/components/ui/skeleton";
import { SchemaTable } from "@/components/dataset/schema-table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { DatasetHeader } from "@/components/dataset/dataset-header";
import { useQueryClient } from "@tanstack/react-query";
import { useDataset } from "@/lib/queries/dataset/get-dataset";

export default function DatasetPage({
  params,
}: {
  params: Promise<{ projectId: string; datasetId: string }>;
}) {
  const { datasetId, projectId } = React.use(params);
  const queryClient = useQueryClient();

  const { data: dataset, isLoading } = useDataset({
    variables: {
      datasetId,
      projectId,
    },
  });

  const tableSchema = dataset?.columns || [];

  const handleUpdate = async () => {
    await queryClient.invalidateQueries({
      queryKey: ["datasets"],
    });
  };

  if (isLoading) {
    return (
      <div className="py-10">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 space-y-6">
          {/* Loading Header */}
          <div className="bg-background p-8 rounded-xl shadow-sm border">
            <div className="space-y-6">
              {/* Breadcrumb Skeleton */}
              <div className="flex items-center gap-2">
                <Skeleton className="h-4 w-4" />
                <Skeleton className="h-4 w-20" />
                <Skeleton className="h-4 w-4" />
                <Skeleton className="h-4 w-32" />
              </div>

              {/* Main Header Skeleton */}
              <div className="flex items-start gap-6">
                {/* Left Section */}
                <div className="flex items-start gap-4 flex-1">
                  <Skeleton className="h-12 w-12 rounded-lg" />
                  <div className="space-y-3 flex-1">
                    {/* Title */}
                    <div className="flex items-center gap-3">
                      <Skeleton className="h-8 w-64" />
                      <Skeleton className="h-7 w-7 rounded-full" />
                      <Skeleton className="h-6 w-12 rounded" />
                    </div>
                    {/* Description */}
                    <div className="space-y-2">
                      <Skeleton className="h-4 w-full" />
                      <Skeleton className="h-4 w-3/4" />
                      <Skeleton className="h-4 w-1/2" />
                    </div>
                    {/* Quick Stats */}
                    <div className="flex items-center gap-4">
                      <Skeleton className="h-5 w-16" />
                      <Skeleton className="h-5 w-20" />
                      <Skeleton className="h-7 w-24" />
                    </div>
                  </div>
                </div>
                {/* Right Section - Action Buttons */}
                <div className="flex items-center gap-2">
                  <Skeleton className="h-9 w-9" />
                  <Skeleton className="h-9 w-9" />
                  <Skeleton className="h-9 w-9" />
                </div>
              </div>
            </div>
          </div>

          {/* Loading Content */}
          <div className="bg-background rounded-xl shadow-sm border overflow-hidden">
            <div className="px-6 pt-6">
              <Skeleton className="h-9 w-[400px]" />
            </div>
            <div className="p-6 pt-4">
              <Skeleton className="h-[400px] w-full" />
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!dataset) {
    return <div>Dataset not found</div>;
  }

  return (
    <div className="min-h-screen bg-background/50 py-10">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 space-y-6">
        {/* Dataset Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/50 p-8 rounded-xl shadow-sm border"
        >
          <DatasetHeader
            dataset={dataset}
            projectId={projectId}
            onUpdate={handleUpdate}
          />
        </motion.div>

        {/* Content Tabs */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/50 rounded-xl shadow-sm border overflow-hidden"
        >
          <Tabs defaultValue="preview" className="h-full">
            <div className="px-6 pt-6">
              <TabsList className="w-full max-w-[400px] grid grid-cols-2">
                <TabsTrigger value="preview" className="flex-1">
                  Data Preview
                </TabsTrigger>
                <TabsTrigger value="schema" className="flex-1">
                  Schema
                </TabsTrigger>
              </TabsList>
            </div>
            <TabsContent value="preview" className="p-6 pt-4">
              <DataPreview datasetId={dataset.name} />
            </TabsContent>
            <TabsContent value="schema" className="p-6 pt-4">
              <SchemaTable schema={tableSchema || []} />
            </TabsContent>
          </Tabs>
        </motion.div>
      </div>
    </div>
  );
}

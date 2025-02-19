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
      <div className="">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 space-y-6">
          {/* Loading Header */}
          <div className="bg-background p-6 rounded-lg shadow-sm border">
            <div className="space-y-4">
              <div className="flex items-start justify-between">
                <div className="space-y-2">
                  <div className="flex items-center gap-3">
                    <Skeleton className="h-12 w-[300px]" />
                    <Skeleton className="h-6 w-16" />
                  </div>
                  <Skeleton className="h-6 w-[200px]" />
                </div>
                <Skeleton className="h-9 w-[150px]" />
              </div>

              <div className="flex items-center gap-8 pt-4 mt-4 border-t border-border/40">
                <div className="flex flex-col gap-0.5">
                  <Skeleton className="h-5 w-20" />
                  <Skeleton className="h-8 w-24" />
                </div>
                <div className="flex flex-col gap-0.5">
                  <Skeleton className="h-5 w-20" />
                  <Skeleton className="h-8 w-24" />
                </div>
              </div>
            </div>
          </div>

          {/* Loading Content */}
          <div className="bg-background rounded-lg shadow-sm border p-6">
            <Skeleton className="h-10 w-[200px] mb-6" />
            <Skeleton className="h-[400px] w-full" />
          </div>
        </div>
      </div>
    );
  }

  if (!dataset) {
    return <div>Dataset not found</div>;
  }

  return (
    <div className="">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 space-y-6">
        {/* Dataset Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-background p-6 rounded-lg shadow-sm border"
        >
          <DatasetHeader dataset={dataset} onUpdate={handleUpdate} />
        </motion.div>

        {/* Content Tabs */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="bg-background rounded-lg shadow-sm border p-6"
        >
          <Tabs defaultValue="preview" className="space-y-4">
            <TabsList>
              <TabsTrigger value="preview">Data Preview</TabsTrigger>
              <TabsTrigger value="schema">Schema</TabsTrigger>
            </TabsList>
            <TabsContent value="preview" className="space-y-4">
              <DataPreview datasetId={dataset.name} />
            </TabsContent>
            <TabsContent value="schema" className="space-y-4">
              <SchemaTable schema={tableSchema || []} />
            </TabsContent>
          </Tabs>
        </motion.div>
      </div>
    </div>
  );
}

"use client";

import * as React from "react";
import { motion } from "framer-motion";
import { DownloadIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { DataPreview } from "@/components/dataset/data-preview";
import { useDatasetSql } from "@/lib/queries/dataset/sql";
import { Skeleton } from "@/components/ui/skeleton";
import { useGetSchema } from "@/lib/queries/dataset/get-schema";
import { SchemaTable } from "@/components/dataset/schema-table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function DatasetPage({
  params,
}: {
  params: Promise<{ projectId: string; datasetId: string }>;
}) {
  const { datasetId } = React.use(params);

  const { data: totalRowsData, isLoading: isTotalRowsLoading } = useDatasetSql<
    Array<{ cnt: number }>
  >({
    variables: {
      sql: `SELECT COUNT(*) as cnt FROM ${datasetId}`,
    },
  });
  const totalRows = totalRowsData?.[0]?.cnt;

  const { data: tableSchema, isLoading: isSchemaLoading } = useGetSchema({
    variables: {
      datasetId,
    },
  });

  const isLoading = isTotalRowsLoading || isSchemaLoading;

  if (isLoading) {
    return (
      <div className="min-h-screen">
        <div className="container max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8 space-y-6">
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

  return (
    <div className="min-h-screen">
      <div className="container max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8 space-y-6">
        {/* Dataset Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-background p-6 rounded-lg shadow-sm border"
        >
          <div className="space-y-4">
            <div className="flex items-start justify-between">
              <div className="space-y-2">
                <div className="flex items-center gap-3">
                  <motion.h1
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.2 }}
                    className="text-4xl font-bold tracking-tight bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text text-transparent"
                  >
                    {datasetId}
                  </motion.h1>
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ type: "spring", delay: 0.3 }}
                  >
                    <Badge variant="secondary" className="h-6 font-medium">
                      CSV
                    </Badge>
                  </motion.div>
                </div>
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.4 }}
                  className="flex items-center gap-4 text-muted-foreground"
                >
                  <div className="flex items-center gap-1.5">
                    <span className="font-medium">Rows:</span>
                    <span>
                      {new Intl.NumberFormat().format(totalRows ?? 0)}
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="font-medium">Columns:</span>
                    <span>{tableSchema?.length}</span>
                  </div>
                </motion.div>
              </div>
              <Button
                variant="outline"
                size="sm"
                className="h-9 hover:shadow-md transition-shadow"
              >
                <DownloadIcon className="mr-2 h-4 w-4" />
                Download Dataset
              </Button>
            </div>
          </div>
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
              <DataPreview datasetId={datasetId} />
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

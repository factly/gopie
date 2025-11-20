"use client";

import * as React from "react";
import { use } from "react";
import { useRouter } from "next/navigation";
import { useDatasetById } from "@/lib/queries/dataset/get-dataset-by-id";
import { FileRefreshWizard } from "@/components/dataset/file-refresh-wizard";
import { useQueryClient } from "@tanstack/react-query";


interface RefreshDatasetPageProps {
  params: Promise<{
    projectId: string;
    datasetId: string;
  }>;
}

export default function RefreshDatasetPage({ params }: RefreshDatasetPageProps) {
  const queryClient = useQueryClient();
  const { projectId, datasetId } = use(params);
  const { data: datasetData  } = useDatasetById({
      variables: { datasetId },
      enabled: !!datasetId,
    });
  const router = useRouter();

  const handleRefreshComplete = React.useCallback(async() => {
    await queryClient.invalidateQueries({
        queryKey: ["get-table"],
      });
    router.push(`/projects/${projectId}/datasets/${datasetId}`);
  }, [datasetId, projectId, router, queryClient]);

  if (!projectId || !datasetId) {
    return <div>Loading parameters...</div>;
  }
  return (
      <FileRefreshWizard
        projectId={projectId}
        datasetId={datasetData?.name||''}
        onRefreshComplete={handleRefreshComplete}
      />
  );
}

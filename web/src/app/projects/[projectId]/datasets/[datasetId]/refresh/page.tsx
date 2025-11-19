"use client";

import * as React from "react";
import { use } from "react";
import { useRouter } from "next/navigation";
import { useDatasetById } from "@/lib/queries/dataset/get-dataset-by-id";
import { FileRefreshWizard } from "@/components/dataset/file-refresh-wizard";


interface RefreshDatasetPageProps {
  params: Promise<{
    projectId: string;
    datasetId: string;
  }>;
}

export default function RefreshDatasetPage({ params }: RefreshDatasetPageProps) {
  const { projectId, datasetId } = use(params);
  const { data: datasetData , isLoading } = useDatasetById({
      variables: { datasetId },
      enabled: !!datasetId,
    });
  const router = useRouter();

  const handleRefreshComplete = React.useCallback(() => {
    router.push(`/projects/${projectId}/datasets/${datasetId}`);
  }, [datasetId, projectId, router]);

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

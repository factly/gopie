"use client";

import * as React from "react";
import { DatasetUploadWizard } from "@/components/dataset/dataset-upload-wizard";
import { useAuthStore } from "@/lib/stores/auth-store";
import { useProject } from "@/lib/queries/project/get-project";
import { useRouter } from "next/navigation";

export default function UploadDatasetPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = React.use(params);
  const { role, user } = useAuthStore();
  const router = useRouter();

  const { data: project, isLoading } = useProject({
    variables: { projectId },
  });

  React.useEffect(() => {
    if (!isLoading && project) {
      const canEdit = role === "admin" || project.created_by === user?.id;
      if (!canEdit) {
        router.replace(`/projects/${projectId}`);
      }
    }
  }, [isLoading, project, role, user, projectId, router]);

  if (isLoading || !project) return null;

  const canEdit = role === "admin" || project.created_by === user?.id;
  if (!canEdit) return null;

  return <DatasetUploadWizard projectId={projectId} />;
}

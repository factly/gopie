"use client";

import * as React from "react";
import { DatasetUploadWizard } from "@/components/dataset/dataset-upload-wizard";

export default function UploadDatasetPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = React.use(params);

  return <DatasetUploadWizard projectId={projectId} />;
}

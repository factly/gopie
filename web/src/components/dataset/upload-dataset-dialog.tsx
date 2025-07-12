"use client";

import { Button } from "@/components/ui/button";
import { UploadIcon } from "lucide-react";
import Link from "next/link";

export function UploadDatasetDialog({ projectId }: { projectId: string }) {
  return (
    <Link href={`/projects/${projectId}/upload`}>
      <Button size="sm" className="h-9">
        <UploadIcon className="mr-2 size-4" />
        Upload Dataset
      </Button>
    </Link>
  );
}

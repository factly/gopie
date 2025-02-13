"use client";

import * as React from "react";
import {
  TableIcon,
  CodeIcon,
  MessageSquareIcon,
  NetworkIcon,
} from "lucide-react";
import { Tabs } from "@/components/navigation/tabs";

export default function DatasetLayout({
  children,
  params,
}: Readonly<{
  children: React.ReactNode;
  params: Promise<{ projectId: string; datasetId: string }>;
}>) {
  const { projectId, datasetId } = React.use(params);

  const tabs = [
    {
      name: "Dataset",
      href: `/${projectId}/${datasetId}`,
      icon: TableIcon,
      exact: true,
    },
    {
      name: "Data",
      href: `/${projectId}/${datasetId}/data`,
      icon: CodeIcon,
    },
    {
      name: "Chat",
      href: `/${projectId}/${datasetId}/chat`,
      icon: MessageSquareIcon,
    },
    {
      name: "Rest API",
      href: `/${projectId}/${datasetId}/api`,
      icon: NetworkIcon,
    },
  ];

  return (
    <div className="flex flex-col min-h-screen">
      <Tabs tabs={tabs} />
      <div className="flex-1">{children}</div>
    </div>
  );
}

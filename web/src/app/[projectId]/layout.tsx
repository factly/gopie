"use client";

import * as React from "react";
import { TableIcon, DatabaseIcon } from "lucide-react";
import { Tabs } from "@/components/navigation/tabs";

export default function ProjectLayout({
  children,
  params,
}: Readonly<{
  children: React.ReactNode;
  params: Promise<{ projectId: string }>;
}>) {
  const { projectId } = React.use(params);

  const tabs = [
    {
      name: "Datasets",
      href: `/${projectId}`,
      icon: TableIcon,
      exact: true,
    },
    {
      name: "Schemas",
      href: `/${projectId}/schemas`,
      icon: DatabaseIcon,
    },
  ];

  return (
    <div className="flex flex-col min-h-screen">
      <Tabs tabs={tabs} />
      <div className="flex-1">{children}</div>
    </div>
  );
}

"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { TableIcon, CodeIcon, MessageSquareIcon } from "lucide-react";

export default function DatasetLayout({
  children,
  params,
}: Readonly<{
  children: React.ReactNode;
  params: Promise<{ projectId: string; datasetId: string }>;
}>) {
  const pathname = usePathname();
  const { projectId, datasetId } = React.use(params);

  const tabs = [
    {
      name: "Dataset",
      href: `/${projectId}/${datasetId}`,
      icon: TableIcon,
      exact: true,
    },
    {
      name: "SQL",
      href: `/${projectId}/${datasetId}/sql`,
      icon: CodeIcon,
    },
    {
      name: "Chat",
      href: `/${projectId}/${datasetId}/chat`,
      icon: MessageSquareIcon,
    },
  ];

  return (
    <div className="flex flex-col min-h-screen">
      <div className="sticky top-[57px] z-30 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex -mb-px">
            {tabs.map((tab) => {
              const isActive = tab.exact
                ? pathname === tab.href
                : pathname.startsWith(tab.href);

              return (
                <Link
                  key={tab.href}
                  href={tab.href}
                  className={cn(
                    "flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors hover:text-foreground",
                    isActive
                      ? "border-primary text-foreground"
                      : "border-transparent text-muted-foreground hover:border-border"
                  )}
                >
                  <tab.icon className="h-4 w-4" />
                  {tab.name}
                </Link>
              );
            })}
          </div>
        </div>
      </div>
      <div className="flex-1">{children}</div>
    </div>
  );
}

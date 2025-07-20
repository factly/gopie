"use client";

import Link from "next/link";
import { usePathname, useParams } from "next/navigation";
import { useProject } from "@/lib/queries/project/get-project";
import { useDatasetById } from "@/lib/queries/dataset/get-dataset-by-id";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { Separator } from "@/components/ui/separator";
import { SidebarTrigger } from "@/components/ui/sidebar";

// Define route mappings for better breadcrumb labels
const routeLabels: Record<string, string> = {
  dashboard: "Dashboard",
  chat: "Chat",
  upload: "Upload",
  schemas: "Schemas",
  projects: "Projects",
  datasets: "Datasets",
  api: "API",
};

// Helper function to detect if a segment looks like an ID
function isIdSegment(segment: string): boolean {
  // Check for UUID-like patterns or long alphanumeric strings
  return (
    /^[a-fA-F0-9]{8,}$/.test(segment.replace(/[-\s]/g, "")) ||
    /^[a-zA-Z0-9]{20,}$/.test(segment)
  );
}

function useBreadcrumbData() {
  const params = useParams();
  const projectId = params?.projectId as string;
  const datasetId = params?.datasetId as string;

  // Fetch project data if we have a projectId
  const { data: projectData } = useProject({
    variables: { projectId },
    enabled: !!projectId,
  });

  // Fetch dataset data if we have a datasetId
  const { data: datasetData } = useDatasetById({
    variables: { datasetId },
    enabled: !!datasetId,
  });

  return { projectData, datasetData };
}

function generateBreadcrumbs(
  pathname: string,
  projectData?: { id: string; name?: string; title?: string },
  datasetData?: { id: string; name?: string; title?: string }
) {
  // Skip breadcrumbs for home page
  if (pathname === "/") {
    return [];
  }

  const segments = pathname.split("/").filter(Boolean);
  const breadcrumbs: Array<{
    label: string;
    href?: string;
    isCurrentPage?: boolean;
  }> = [];

  // Special handling for Projects page - treat it as Home
  if (pathname === "/projects") {
    return [];
  }

  // Always add Home as first breadcrumb
  breadcrumbs.push({
    label: "Home",
    href: "/",
  });

  // Extract project and dataset IDs from the path
  let projectId: string | undefined;
  let datasetId: string | undefined;

  // Parse the segments to find project and dataset IDs
  for (let i = 0; i < segments.length; i++) {
    if (segments[i] === "projects" && i + 1 < segments.length) {
      projectId = segments[i + 1];
    }
    if (segments[i] === "datasets" && i + 1 < segments.length) {
      datasetId = segments[i + 1];
    }
  }

  // Add project breadcrumb if we have a project
  if (projectId && projectData) {
    breadcrumbs.push({
      label: projectData.name || projectData.title || "Project",
      href: `/projects/${projectId}`,
      isCurrentPage: !datasetId, // Current page if no dataset
    });
  }

  // Add dataset breadcrumb if we have a dataset
  if (datasetId && datasetData) {
    breadcrumbs.push({
      label: datasetData.alias || datasetData.title || datasetData.name || "Dataset",
      href: undefined, // No href for current page
      isCurrentPage: true,
    });
  }

  return breadcrumbs;
}

export function AppHeader() {
  const pathname = usePathname();
  const { projectData, datasetData } = useBreadcrumbData();
  const breadcrumbs = generateBreadcrumbs(pathname, projectData, datasetData);

  // Hide header on home page, projects page (treated as home), and chat
  if (pathname === "/" || pathname === "/projects" || pathname.startsWith("/chat")) {
    return null;
  }

  return (
    <header className="flex h-16 shrink-0 items-center gap-2 transition-[width,height] ease-linear group-has-[[data-collapsible=icon]]/sidebar-wrapper:h-12">
      <div className="flex items-center gap-2 px-4">
        <SidebarTrigger className="-ml-1" />
        <Separator orientation="vertical" className="mr-2 h-4" />
        {breadcrumbs && breadcrumbs.length > 1 && (
          <Breadcrumb>
            <BreadcrumbList>
              {breadcrumbs.map((crumb, index) => (
                <div key={index} className="flex items-center gap-2">
                  <BreadcrumbItem className="hidden md:block">
                    {crumb.isCurrentPage ? (
                      <BreadcrumbPage>{crumb.label}</BreadcrumbPage>
                    ) : (
                      <BreadcrumbLink asChild>
                        <Link href={crumb.href || "#"}>{crumb.label}</Link>
                      </BreadcrumbLink>
                    )}
                  </BreadcrumbItem>
                  {index < breadcrumbs.length - 1 && (
                    <BreadcrumbSeparator className="hidden md:block" />
                  )}
                </div>
              ))}
            </BreadcrumbList>
          </Breadcrumb>
        )}
      </div>
    </header>
  );
}

"use client";

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

  // Always add Home as first breadcrumb
  breadcrumbs.push({
    label: "Home",
    href: "/",
  });

  // Build breadcrumbs from path segments
  let currentPath = "";
  segments.forEach((segment, index) => {
    currentPath += `/${segment}`;
    const isLast = index === segments.length - 1;

    let label: string;

    // Check if this segment is an ID and try to get friendly name
    if (isIdSegment(segment)) {
      // Check if this is a project ID
      if (projectData && segment === projectData.id) {
        label = projectData.name || projectData.title || "Project";
      }
      // Check if this is a dataset ID
      else if (datasetData && segment === datasetData.id) {
        label = datasetData.title || datasetData.name || "Dataset";
      }
      // Fallback for unknown IDs - truncate for better display
      else {
        label = `${segment.substring(0, 8)}...`;
      }
    }
    // Use predefined labels or format the segment
    else {
      label =
        routeLabels[segment] ||
        segment.replace(/-/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
    }

    breadcrumbs.push({
      label,
      href: isLast ? undefined : currentPath,
      isCurrentPage: isLast,
    });
  });

  return breadcrumbs;
}

export function AppHeader() {
  const pathname = usePathname();
  const { projectData, datasetData } = useBreadcrumbData();
  const breadcrumbs = generateBreadcrumbs(pathname, projectData, datasetData);

  // Hide header on home page
  if (pathname === "/") {
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
                      <BreadcrumbLink href={crumb.href || "#"}>
                        {crumb.label}
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

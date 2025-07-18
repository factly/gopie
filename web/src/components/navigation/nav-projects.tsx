"use client";

import {
  ChevronDown,
  TableIcon,
  // DatabaseIcon,
  CodeIcon,
  // MessageSquareIcon,
  NetworkIcon,
} from "lucide-react";
import Link from "next/link";
import { useParams, usePathname } from "next/navigation";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  SidebarGroup,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuAction,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar";
import { useProject } from "@/lib/queries/project/get-project";
import { useProjects } from "@/lib/queries/project/list-projects";
import { useDatasets } from "@/lib/queries/dataset/list-datasets";

export function NavProjects() {
  const { isMobile } = useSidebar();
  const params = useParams();
  const pathname = usePathname();
  const projectId = params?.projectId as string;
  const datasetId = params?.datasetId as string;

  const { data: projects } = useProjects({
    variables: {
      limit: 100,
    },
  });

  const { data: project } = useProject(
    projectId
      ? {
          variables: { projectId },
          enabled: Boolean(projectId),
        }
      : { enabled: false }
  );

  const { data: datasets } = useDatasets({
    variables: {
      projectId,
    },
    enabled: Boolean(projectId),
  });

  // Hide projects section on home page
  if (pathname === "/") {
    return null;
  }

  const isActive = (href: string, exact = false) => {
    if (exact) {
      return pathname === href;
    }
    if (datasetId && href.includes(datasetId)) {
      return pathname.startsWith(href);
    }
    return pathname === href;
  };

  // Project navigation items
  const projectNavItems = project
    ? [
        {
          title: "Datasets",
          url: `/${projectId}`,
          icon: TableIcon,
          isActive: isActive(`/${projectId}`, true),
        },
        // {
        //   title: "Relationships",
        //   url: `/${projectId}/schemas`,
        //   icon: DatabaseIcon,
        //   isActive: isActive(`/${projectId}/schemas`, true),
        // },
      ]
    : [];

  // Dataset navigation items
  const datasetNavItems =
    datasetId && datasets?.results
      ? [
          {
            title: "Overview",
            url: `/${projectId}/${datasetId}`,
            icon: TableIcon,
            isActive: isActive(`/${projectId}/${datasetId}`, true),
          },
          // {
          //   title: "Chat",
          //   url: `/${projectId}/${datasetId}/chat`,
          //   icon: MessageSquareIcon,
          //   isActive: isActive(`/${projectId}/${datasetId}/chat`),
          // },
          {
            title: "SQL Playground",
            url: `/${projectId}/${datasetId}/data`,
            icon: CodeIcon,
            isActive: isActive(`/${projectId}/${datasetId}/data`),
          },
          {
            title: "API Playground",
            url: `/${projectId}/${datasetId}/api`,
            icon: NetworkIcon,
            isActive: isActive(`/${projectId}/${datasetId}/api`),
          },
        ]
      : [];

  return (
    <>
      {/* Project Navigation */}
      {project && (
        <SidebarGroup className="group-data-[collapsible=icon]:hidden">
          <SidebarGroupLabel className="flex items-center justify-between">
            <span className="truncate font-medium">{project.name}</span>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <SidebarMenuAction showOnHover>
                  <ChevronDown className="h-3 w-3" />
                  <span className="sr-only">Switch Project</span>
                </SidebarMenuAction>
              </DropdownMenuTrigger>
              <DropdownMenuContent
                className="w-[200px]"
                side={isMobile ? "bottom" : "right"}
                align={isMobile ? "end" : "start"}
              >
                {projects?.results?.map((p) => (
                  <DropdownMenuItem asChild key={p.id}>
                    <Link href={`/${p.id}`}>
                      <span className="truncate">{p.name}</span>
                      {p.id === project.id && (
                        <span className="ml-auto text-xs text-muted-foreground">
                          Current
                        </span>
                      )}
                    </Link>
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          </SidebarGroupLabel>
          <SidebarMenu>
            {projectNavItems.map((item) => (
              <SidebarMenuItem key={item.title}>
                <SidebarMenuButton asChild isActive={item.isActive}>
                  <Link href={item.url}>
                    <item.icon />
                    <span>{item.title}</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            ))}
          </SidebarMenu>
        </SidebarGroup>
      )}

      {/* Dataset Navigation */}
      {datasetId && datasets?.results && (
        <SidebarGroup className="group-data-[collapsible=icon]:hidden">
          <SidebarGroupLabel className="flex items-center justify-between">
            <span className="truncate font-medium">
              {datasets.results.find((d) => d.id === datasetId)?.alias ||
                datasets.results.find((d) => d.id === datasetId)?.name ||
                "Select Dataset"}
            </span>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <SidebarMenuAction showOnHover>
                  <ChevronDown className="h-3 w-3" />
                  <span className="sr-only">Switch Dataset</span>
                </SidebarMenuAction>
              </DropdownMenuTrigger>
              <DropdownMenuContent
                className="w-[200px]"
                side={isMobile ? "bottom" : "right"}
                align={isMobile ? "end" : "start"}
              >
                {datasets.results.map((dataset) => (
                  <DropdownMenuItem asChild key={dataset.id}>
                    <Link href={`/projects/${projectId}/datasets/${dataset.id}`}>
                      <span className="truncate">
                        {dataset.alias || dataset.name}
                      </span>
                      {dataset.id === datasetId && (
                        <span className="ml-auto text-xs text-muted-foreground">
                          Current
                        </span>
                      )}
                    </Link>
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          </SidebarGroupLabel>
          <SidebarMenu>
            {datasetNavItems.map((item) => (
              <SidebarMenuItem key={item.title}>
                <SidebarMenuButton asChild isActive={item.isActive}>
                  <Link href={item.url}>
                    <item.icon />
                    <span>{item.title}</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            ))}
          </SidebarMenu>
        </SidebarGroup>
      )}
    </>
  );
}

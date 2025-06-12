"use client";

import {
  DatabaseIcon,
  TableIcon,
  MessageSquareIcon,
  CodeIcon,
  NetworkIcon,
  ChevronDown,
} from "lucide-react";
import Link from "next/link";
import { useParams, usePathname } from "next/navigation";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import {
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { useProject } from "@/lib/queries/project/get-project";
import { useProjects } from "@/lib/queries/project/list-projects";
import { useDatasets } from "@/lib/queries/dataset/list-datasets";

export function NavProjects() {
  const params = useParams();
  const pathname = usePathname();
  const projectId = params?.projectId as string;
  const datasetId = params?.datasetId as string;

  const { data: allProjects } = useProjects({
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

  const isActive = (href: string, exact = false) => {
    if (exact) {
      return pathname === href;
    }
    // For dataset routes, we want to match the prefix
    if (datasetId && href.includes(datasetId)) {
      return pathname.startsWith(href);
    }
    return pathname === href;
  };

  // Don't show project navigation on chat page
  if (pathname === "/chat") {
    return null;
  }

  return (
    <>
      {/* Projects Navigation */}
      <SidebarGroup>
        <SidebarGroupLabel className="flex items-center justify-between">
          <span className="truncate font-medium">
            {project?.name || "Select Project"}
          </span>
          {project && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-5 px-2 text-xs flex items-center gap-1"
                >
                  <span>Switch</span>
                  <ChevronDown className="h-3 w-3 opacity-50" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-[200px]">
                {allProjects?.results?.map((p) => (
                  <Link href={`/${p.id}`} key={p.id}>
                    <DropdownMenuItem>
                      <span className="truncate">{p.name}</span>
                      {p.id === project.id && (
                        <span className="ml-auto text-xs text-muted-foreground">
                          Current
                        </span>
                      )}
                    </DropdownMenuItem>
                  </Link>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          )}
        </SidebarGroupLabel>
        {project && (
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  asChild
                  isActive={isActive(`/${projectId}`, true)}
                >
                  <Link href={`/${projectId}`}>
                    <TableIcon className="h-4 w-4" />
                    <span>Datasets</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  asChild
                  isActive={isActive(`/${projectId}/schemas`, true)}
                >
                  <Link href={`/${projectId}/schemas`}>
                    <DatabaseIcon className="h-4 w-4" />
                    <span>Relationships</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        )}
      </SidebarGroup>

      {/* Datasets Navigation */}
      {datasetId && datasets?.results && (
        <SidebarGroup>
          <SidebarGroupLabel className="flex items-center justify-between">
            <span className="truncate font-medium">
              {datasets.results.find((d) => d.id === datasetId)?.alias ||
                datasets.results.find((d) => d.id === datasetId)?.name ||
                "Select Dataset"}
            </span>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-5 px-2 text-xs flex items-center gap-1"
                >
                  <span>Switch</span>
                  <ChevronDown className="h-3 w-3 opacity-50" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-[200px]">
                {datasets.results.map((dataset) => (
                  <Link href={`/${projectId}/${dataset.id}`} key={dataset.id}>
                    <DropdownMenuItem>
                      <span className="truncate">
                        {dataset.alias || dataset.name}
                      </span>
                      {dataset.id === datasetId && (
                        <span className="ml-auto text-xs text-muted-foreground">
                          Current
                        </span>
                      )}
                    </DropdownMenuItem>
                  </Link>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  asChild
                  isActive={isActive(`/${projectId}/${datasetId}`, true)}
                >
                  <Link href={`/${projectId}/${datasetId}`}>
                    <TableIcon className="h-4 w-4" />
                    <span>Overview</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  asChild
                  isActive={isActive(`/${projectId}/${datasetId}/chat`)}
                >
                  <Link href={`/${projectId}/${datasetId}/chat`}>
                    <MessageSquareIcon className="h-4 w-4" />
                    <span>Chat</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  asChild
                  isActive={isActive(`/${projectId}/${datasetId}/data`)}
                >
                  <Link href={`/${projectId}/${datasetId}/data`}>
                    <CodeIcon className="h-4 w-4" />
                    <span>Query</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  asChild
                  isActive={isActive(`/${projectId}/${datasetId}/api`)}
                >
                  <Link href={`/${projectId}/${datasetId}/api`}>
                    <NetworkIcon className="h-4 w-4" />
                    <span>Rest API</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      )}
    </>
  );
}

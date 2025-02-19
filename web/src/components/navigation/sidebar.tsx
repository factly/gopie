"use client";

import * as React from "react";
import {
  TableIcon,
  DatabaseIcon,
  CodeIcon,
  MessageSquareIcon,
  NetworkIcon,
  ChevronDown,
  PanelLeftIcon,
  HomeIcon,
} from "lucide-react";
import { useParams, usePathname, useRouter } from "next/navigation";
import Link from "next/link";

import {
  Sidebar,
  SidebarContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarFooter,
  SidebarTrigger,
  useSidebar,
} from "@/components/ui/sidebar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ThemeToggle } from "@/components/theme/toggle";
import { useProject } from "@/lib/queries/project/get-project";
import { useProjects } from "@/lib/queries/project/list-projects";
import { useDatasets } from "@/lib/queries/dataset/list-datasets";
import { CommandSearch } from "@/components/search/command-search";

export function AppSidebar() {
  const router = useRouter();
  const params = useParams();
  const pathname = usePathname();
  const { open: isSidebarOpen } = useSidebar();
  const projectId = params?.projectId as string;
  const datasetId = params?.datasetId as string;

  const { data: projects } = useProjects();
  const { data: project } = useProject(
    projectId
      ? {
          variables: { projectId },
          enabled: Boolean(projectId),
        }
      : { enabled: false },
  );
  const { data: datasets } = useDatasets({
    variables: {
      projectId,
    },
    enabled: Boolean(projectId),
  });

  // Hide sidebar on home page
  if (pathname === "/") {
    return null;
  }

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

  return (
    <Sidebar collapsible="icon" className="border-r">
      <SidebarHeader className="border-b px-2 py-3">
        {isSidebarOpen ? (
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={() => router.push("/")}
                title="Back to Home"
              >
                <HomeIcon className="h-4 w-4" />
              </Button>
              <span className="font-semibold">Gopie</span>
            </div>
            <div className="flex items-center gap-2">
              <ThemeToggle />
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                title="Toggle Sidebar"
                onClick={() => {
                  const trigger = document.querySelector(
                    '[data-sidebar="trigger"]',
                  ) as HTMLButtonElement;
                  if (trigger) {
                    trigger.click();
                  }
                }}
              >
                <PanelLeftIcon className="h-4 w-4" />
              </Button>
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() => router.push("/")}
              title="Back to Home"
            >
              <HomeIcon className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              title="Toggle Sidebar"
              onClick={() => {
                const trigger = document.querySelector(
                  '[data-sidebar="trigger"]',
                ) as HTMLButtonElement;
                if (trigger) {
                  trigger.click();
                }
              }}
            >
              <PanelLeftIcon className="h-4 w-4" />
            </Button>
          </div>
        )}
        <SidebarTrigger className="hidden" />
      </SidebarHeader>

      <SidebarContent>
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
                    className="h-5 px-2 text-xs flex items-center gap-1 group-data-[collapsed=true]:w-8 group-data-[collapsed=true]:px-0 group-data-[collapsed=true]:h-8"
                  >
                    <span className="group-data-[collapsed=true]:hidden">
                      Switch
                    </span>
                    <ChevronDown className="h-3 w-3 opacity-50" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-[200px]">
                  {projects?.results.map((p) => (
                    <DropdownMenuItem
                      key={p.id}
                      onSelect={() => router.push(`/${p.id}`)}
                    >
                      <span className="truncate">{p.name}</span>
                      {p.id === project.id && (
                        <span className="ml-auto text-xs text-muted-foreground">
                          Current
                        </span>
                      )}
                    </DropdownMenuItem>
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
                      <span>Schemas</span>
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
                {datasets.results.find((d) => d.id === datasetId)?.name ||
                  "Select Dataset"}
              </span>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-5 px-2 text-xs flex items-center gap-1 group-data-[collapsed=true]:w-8 group-data-[collapsed=true]:px-0 group-data-[collapsed=true]:h-8"
                  >
                    <span className="group-data-[collapsed=true]:hidden">
                      Switch
                    </span>
                    <ChevronDown className="h-3 w-3 opacity-50" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-[200px]">
                  {datasets.results.map((dataset) => (
                    <DropdownMenuItem
                      key={dataset.id}
                      onSelect={() =>
                        router.push(`/${projectId}/${dataset.id}`)
                      }
                    >
                      <span className="truncate">{dataset.name}</span>
                      {dataset.id === datasetId && (
                        <span className="ml-auto text-xs text-muted-foreground">
                          Current
                        </span>
                      )}
                    </DropdownMenuItem>
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
      </SidebarContent>

      <SidebarFooter className="border-t p-2">
        <div className="flex flex-col gap-2">
          {!isSidebarOpen && (
            <div className="flex justify-center">
              <ThemeToggle />
            </div>
          )}
          <CommandSearch projectId={projectId} onNavigate={router.push} />
        </div>
      </SidebarFooter>
    </Sidebar>
  );
}

export default AppSidebar;

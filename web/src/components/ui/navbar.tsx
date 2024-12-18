"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ChevronRight, HomeIcon, ChevronDown } from "lucide-react";

import { cn } from "@/lib/utils";
import { useProject } from "@/lib/queries/project/get-project";
import { useProjects } from "@/lib/queries/project/get-projects";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

function Navbar({ className, ...props }: React.ComponentProps<"nav">) {
  return (
    <nav
      className={cn(
        "sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 py-3",
        className,
      )}
      {...props}
    />
  );
}

function Breadcrumb({
  className,
  ...props
}: React.HTMLAttributes<HTMLElement>) {
  const router = useRouter();
  const pathname = usePathname();
  const segments = pathname.split("/").filter(Boolean);

  const projectId = segments[0];
  const datasetId = segments[1];

  const { data: projects } = useProjects();
  const { data: project, isLoading: isLoadingProject } = useProject(
    projectId
      ? {
          variables: { projectId },
          enabled: segments.length > 0,
        }
      : { enabled: false },
  );

  return (
    <nav
      aria-label="Breadcrumb"
      className={cn("flex h-9 items-center space-x-2", className)}
      {...props}
    >
      <ol className="flex items-center space-x-2">
        {/* Home Link */}
        <li>
          <Link
            href="/"
            className="flex items-center text-sm text-muted-foreground hover:text-foreground"
          >
            <HomeIcon className="size-4" />
            <span className="sr-only">Home</span>
          </Link>
        </li>

        {segments.map((segment, index) => {
          const path = `/${segments.slice(0, index + 1).join("/")}`;
          const isLast = index === segments.length - 1;

          // Project Segment (First)
          if (index === 0) {
            if (isLoadingProject) {
              return (
                <React.Fragment key={path}>
                  <ChevronRight className="size-4 text-muted-foreground" />
                  <li>
                    <Skeleton className="h-4 w-[100px]" />
                  </li>
                </React.Fragment>
              );
            }

            if (project) {
              return (
                <React.Fragment key={path}>
                  <ChevronRight className="size-4 text-muted-foreground" />
                  <li>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          variant="link"
                          className="h-auto p-0 text-sm font-medium text-foreground hover:no-underline flex items-center gap-1"
                        >
                          {project.name}
                          <ChevronDown className="size-3 opacity-50" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="start">
                        {projects?.map((p) => (
                          <DropdownMenuItem
                            key={p.id}
                            onSelect={() => router.push(`/${p.id}`)}
                            className="min-w-[200px]"
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
                  </li>
                </React.Fragment>
              );
            }
          }

          // Dataset Segment (Second)
          if (index === 1 && project) {
            return (
              <React.Fragment key={path}>
                <ChevronRight className="size-4 text-muted-foreground" />
                <li>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        variant="link"
                        className="h-auto p-0 text-sm font-medium text-foreground hover:no-underline flex items-center gap-1"
                      >
                        {segment}
                        <ChevronDown className="size-3 opacity-50" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="start">
                      {project.datasets?.map((dataset) => (
                        <DropdownMenuItem
                          key={dataset}
                          onSelect={() =>
                            router.push(`/${projectId}/${dataset}`)
                          }
                          className="min-w-[200px]"
                        >
                          <span className="truncate">{dataset}</span>
                          {dataset === datasetId && (
                            <span className="ml-auto text-xs text-muted-foreground">
                              Current
                            </span>
                          )}
                        </DropdownMenuItem>
                      ))}
                    </DropdownMenuContent>
                  </DropdownMenu>
                </li>
              </React.Fragment>
            );
          }

          // Other segments (if any)
          return (
            <React.Fragment key={path}>
              <ChevronRight className="size-4 text-muted-foreground" />
              <li>
                <Link
                  href={path}
                  className={cn(
                    "text-sm hover:text-foreground leading-none",
                    isLast
                      ? "font-medium text-foreground"
                      : "text-muted-foreground",
                  )}
                  aria-current={isLast ? "page" : undefined}
                >
                  {segment}
                </Link>
              </li>
            </React.Fragment>
          );
        })}
      </ol>
    </nav>
  );
}

export { Navbar, Breadcrumb };

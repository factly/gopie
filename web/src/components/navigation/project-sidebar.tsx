"use client";

import * as React from "react";
import {
  LoaderIcon,
  FolderOpen,
} from "lucide-react";
import { useRouter, usePathname } from "next/navigation";
import { Project } from "@/lib/api-client";
import { useProjects } from "@/lib/queries/project/list-projects";
import {
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
} from "@/components/ui/sidebar";

export function ProjectsSidebar() {
  const router = useRouter();
  const pathname = usePathname();

  // Always declare hooks at the top level
  const [page, setPage] = React.useState(1);
  const [allProjects, setAllProjects] = React.useState<Project[]>([]);
  const [hasMore, setHasMore] = React.useState(true);
  const [isLoadingMore, setIsLoadingMore] = React.useState(false);
  const observerRef = React.useRef<IntersectionObserver | null>(null);
  const lastProjectRef = React.useRef<HTMLDivElement | null>(null);

  const { data: projects, isLoading: isProjectsLoading } = useProjects({
    variables: {
      limit: 20,
      page,
    },
    enabled: pathname === "/chat",
  });

  // Update allProjects when new data is fetched
  React.useEffect(() => {
    if (pathname === "/chat" && projects?.results) {
      if (page === 1) {
        setAllProjects(projects.results);
      } else {
        setAllProjects((prev) => [...prev, ...projects.results]);
      }

      // Check if there are more projects to load
      setHasMore(projects.total > allProjects.length + projects.results.length);
      setIsLoadingMore(false);
    }
  }, [projects, page, allProjects.length, pathname]);

  // Set up intersection observer for infinite scrolling
  React.useEffect(() => {
    // Only set up observer if we're on the chat page
    if (pathname !== "/chat" || isLoadingMore || !hasMore) return;

    if (observerRef.current) {
      observerRef.current.disconnect();
    }

    const options = {
      root: null,
      rootMargin: "0px",
      threshold: 0.1,
    };

    observerRef.current = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting && hasMore && !isLoadingMore) {
        setIsLoadingMore(true);
        setPage((prevPage) => prevPage + 1);
      }
    }, options);

    if (lastProjectRef.current) {
      observerRef.current.observe(lastProjectRef.current);
    }

    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect();
      }
    };
  }, [isLoadingMore, hasMore, allProjects, pathname]);

  // Function to navigate to a project
  const navigateToProject = (projectId: string) => {
    router.push(`/projects/${projectId}`);
  };

  // Only render for the chat page
  if (pathname !== "/chat") {
    return null;
  }

  return (
    <SidebarGroup>
      <SidebarGroupLabel className="flex items-center justify-between">
        <span className="truncate font-medium">Projects</span>
      </SidebarGroupLabel>
      <SidebarGroupContent>
        <div className="overflow-y-auto max-h-[min(500px,calc(100vh-300px))]">
          <SidebarMenu>
            {isProjectsLoading && page === 1 ? (
              <div className="flex flex-col items-center justify-center py-4 space-y-2">
                <LoaderIcon
                  className={`${"h-6 w-6"} animate-spin text-primary/70`}
                />
                <p className="text-sm text-muted-foreground">
                  Loading projects...
                </p>
              </div>
            ) : allProjects.length === 0 ? (
              <div className="py-4 px-2 text-center">
                <p className="text-xs text-muted-foreground">No projects</p>
              </div>
            ) : (
              <div className="space-y-1 pb-1">
                {allProjects.map((project, index) => {
                  const isLastItem = index === allProjects.length - 1;

                  return (
                    <div
                      key={project.id}
                      ref={isLastItem ? lastProjectRef : null}
                      className="px-2"
                    >
                      <div
                        className="group flex items-center gap-2 py-1 hover:bg-accent cursor-pointer transition-all duration-200 rounded-sm"
                        onClick={() => navigateToProject(project.id)}
                      >
                        <FolderOpen className="h-4 w-4 flex-shrink-0 text-muted-foreground group-hover:text-primary transition-colors" />
                        <span className="truncate text-sm font-medium group-hover:text-accent-foreground">
                          {project.name}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {isLoadingMore && (
              <div className="flex justify-center py-3">
                <LoaderIcon className="h-4 w-4 animate-spin text-muted-foreground" />
              </div>
            )}
          </SidebarMenu>
        </div>
      </SidebarGroupContent>
    </SidebarGroup>
  );
}

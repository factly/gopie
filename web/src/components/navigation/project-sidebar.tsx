"use client";

import * as React from "react";
import {
  FolderIcon,
  LoaderIcon,
  DatabaseIcon,
  ChevronRightIcon,
  ChevronDownIcon,
} from "lucide-react";
import { useRouter, usePathname } from "next/navigation";
import { Project, Dataset } from "@/lib/api-client";
import { useProjects } from "@/lib/queries/project/list-projects";
import {
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
} from "@/components/ui/sidebar";
import { fetchDatasets } from "@/lib/queries/dataset/list-datasets";

export function ProjectsSidebar({ isSidebarOpen }: { isSidebarOpen: boolean }) {
  const router = useRouter();
  const pathname = usePathname();

  // Always declare hooks at the top level
  const [page, setPage] = React.useState(1);
  const [allProjects, setAllProjects] = React.useState<Project[]>([]);
  const [hasMore, setHasMore] = React.useState(true);
  const [isLoadingMore, setIsLoadingMore] = React.useState(false);
  const observerRef = React.useRef<IntersectionObserver | null>(null);
  const lastProjectRef = React.useRef<HTMLDivElement | null>(null);

  // Track expanded project states
  const [expandedProjects, setExpandedProjects] = React.useState<
    Record<string, boolean>
  >({});
  // Track datasets by project ID
  const [datasetsByProject, setDatasetsByProject] = React.useState<
    Record<string, Dataset[]>
  >({});
  // Track which projects are loading datasets
  const [loadingDatasets, setLoadingDatasets] = React.useState<
    Record<string, boolean>
  >({});

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

  // Function to toggle project expansion
  const toggleProjectExpansion = async (projectId: string) => {
    // Toggle the expanded state
    const newExpandedState = !expandedProjects[projectId];
    setExpandedProjects((prev) => ({
      ...prev,
      [projectId]: newExpandedState,
    }));

    // If expanding and we don't have datasets yet, fetch them
    if (newExpandedState && !datasetsByProject[projectId]) {
      try {
        setLoadingDatasets((prev) => ({ ...prev, [projectId]: true }));

        // Fetch datasets for this project
        const response = await fetchDatasets({
          projectId,
          limit: 50,
          page: 1,
        });

        setDatasetsByProject((prev) => ({
          ...prev,
          [projectId]: response.results || [],
        }));
      } catch (error) {
        console.error(
          `Failed to fetch datasets for project ${projectId}:`,
          error
        );
      } finally {
        setLoadingDatasets((prev) => ({ ...prev, [projectId]: false }));
      }
    }
  };

  // Function to navigate to a dataset
  const navigateToDataset = (
    projectId: string,
    datasetId: string,
    event: React.MouseEvent
  ) => {
    event.stopPropagation(); // Prevent toggling project expansion
    router.push(`/${projectId}/${datasetId}`);
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
                  className={`${
                    isSidebarOpen ? "h-6 w-6" : "h-6 w-6"
                  } animate-spin text-primary/70`}
                />
                {isSidebarOpen && (
                  <p className="text-sm text-muted-foreground">
                    Loading projects...
                  </p>
                )}
              </div>
            ) : allProjects.length === 0 ? (
              <div className="py-4 px-2 text-center">
                {isSidebarOpen ? (
                  <p className="text-sm font-medium">No projects found</p>
                ) : (
                  <p className="text-xs text-muted-foreground">No projects</p>
                )}
              </div>
            ) : (
              <div className="space-y-1 pb-1">
                {allProjects.map((project, index) => {
                  const isLastItem = index === allProjects.length - 1;
                  const isExpanded = expandedProjects[project.id] || false;
                  const datasets = datasetsByProject[project.id] || [];
                  const isLoadingDatasets =
                    loadingDatasets[project.id] || false;

                  return (
                    <div
                      key={project.id}
                      ref={isLastItem ? lastProjectRef : null}
                      className="px-1"
                    >
                      {isSidebarOpen ? (
                        <>
                          <div
                            className="group flex items-center gap-2 px-3 py-2 rounded-md hover:bg-accent cursor-pointer transition-all duration-200"
                            onClick={() => toggleProjectExpansion(project.id)}
                          >
                            <div className="flex-shrink-0 w-4">
                              {isExpanded ? (
                                <ChevronDownIcon className="h-4 w-4 text-muted-foreground" />
                              ) : (
                                <ChevronRightIcon className="h-4 w-4 text-muted-foreground" />
                              )}
                            </div>
                            <FolderIcon className="h-4 w-4 text-primary group-hover:text-primary transition-transform flex-shrink-0" />
                            <span
                              className="truncate text-sm font-medium group-hover:text-accent-foreground"
                              onClick={(e) => {
                                e.stopPropagation();
                                router.push(`/${project.id}`);
                              }}
                            >
                              {project.name}
                            </span>
                          </div>

                          {/* Datasets (when expanded) */}
                          {isExpanded && (
                            <div className="ml-9 mt-1 space-y-1">
                              {isLoadingDatasets ? (
                                <div className="flex items-center gap-2 px-3 py-1.5 text-sm text-muted-foreground">
                                  <LoaderIcon className="h-3 w-3 animate-spin" />
                                  <span>Loading datasets...</span>
                                </div>
                              ) : datasets.length === 0 ? (
                                <div className="px-3 py-1.5 text-xs text-muted-foreground">
                                  No datasets found
                                </div>
                              ) : (
                                datasets.map((dataset) => (
                                  <div
                                    key={dataset.id}
                                    className="flex items-center gap-2 px-3 py-1.5 rounded-md hover:bg-accent cursor-pointer group"
                                    onClick={(e) =>
                                      navigateToDataset(
                                        project.id,
                                        dataset.id,
                                        e
                                      )
                                    }
                                  >
                                    <DatabaseIcon className="h-4 w-4 flex-shrink-0 text-muted-foreground group-hover:text-primary transition-colors" />
                                    <span className="truncate text-sm text-muted-foreground group-hover:text-foreground">
                                      {dataset.alias || dataset.name}
                                    </span>
                                  </div>
                                ))
                              )}
                            </div>
                          )}
                        </>
                      ) : (
                        <div
                          className="flex justify-center cursor-pointer hover:bg-accent rounded-md transition-colors"
                          title={project.name}
                          onClick={() => router.push(`/${project.id}`)}
                        >
                          <FolderIcon className="h-4 w-4 my-2 text-primary transition-transform" />
                        </div>
                      )}
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

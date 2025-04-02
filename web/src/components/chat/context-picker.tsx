import { useState, useEffect } from "react";
import { Check, X, AtSign } from "lucide-react";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import { Badge } from "@/components/ui/badge";
import { useProjects } from "@/lib/queries/project/list-projects";
import { useDatasets } from "@/lib/queries/dataset/list-datasets";
import { Dataset } from "@/lib/api-client";
import { useQueryClient } from "@tanstack/react-query";

export interface ContextItem {
  id: string;
  type: "project" | "dataset";
  name: string;
  projectId?: string;
}

interface ContextPickerProps {
  selectedContexts: ContextItem[];
  onSelectContext: (context: ContextItem) => void;
  onRemoveContext: (contextId: string) => void;
  currentDatasetId?: string;
  currentProjectId?: string;
  triggerClassName?: string;
  lockableContextIds?: string[]; // Array of context IDs that cannot be removed
}

export function ContextPicker({
  selectedContexts,
  onSelectContext,
  onRemoveContext,
  triggerClassName,
  lockableContextIds = [], // Default to empty array
}: ContextPickerProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [allDatasets, setAllDatasets] = useState<
    (Dataset & { projectId: string })[]
  >([]);

  const queryClient = useQueryClient();

  // Get projects
  const { data: projectsData } = useProjects({
    variables: { limit: 100 },
  });

  useEffect(() => {
    async function getDatasets() {
      const projects = projectsData?.results || [];
      const datasets: (Dataset & { projectId: string })[] = [];

      // Collect all dataset queries and run them in parallel
      const datasetPromises = projects.map(async (project) => {
        try {
          const queryKey = ["datasets", { projectId: project.id, limit: 100 }];
          // Check cache first
          const cachedData = queryClient.getQueryData(queryKey);

          // Safely handle cached data with type assertion
          if (
            cachedData &&
            typeof cachedData === "object" &&
            "results" in cachedData
          ) {
            return { projectId: project.id, data: cachedData };
          }

          // If not in cache, fetch it
          const data = await queryClient.fetchQuery({
            queryKey,
            queryFn: async () => {
              const result = await useDatasets.fetcher({
                projectId: project.id,
                limit: 100,
              });
              return result;
            },
          });

          return { projectId: project.id, data };
        } catch (error) {
          console.error(
            `Failed to fetch datasets for project ${project.id}:`,
            error
          );
          return { projectId: project.id, data: { results: [] } };
        }
      });

      // Wait for all dataset queries to complete
      const datasetResults = await Promise.all(datasetPromises);

      // Process dataset results
      for (const result of datasetResults) {
        const projectId = result.projectId;
        const data = result.data;

        // Properly type guard for data.results
        if (
          !data ||
          typeof data !== "object" ||
          !("results" in data) ||
          !Array.isArray(data.results)
        ) {
          continue;
        }

        const datasetsWithProjectId = data.results.map((dataset) => ({
          ...dataset,
          projectId,
        }));
        datasets.push(...datasetsWithProjectId);
      }

      setAllDatasets(datasets);
    }

    getDatasets();
  }, [projectsData?.results, queryClient]);

  const filteredProjects = projectsData?.results
    ? projectsData.results.filter((project) =>
        project.name.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : [];

  const filteredDatasets = allDatasets.filter((dataset) =>
    dataset.alias.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          className={`relative ${triggerClassName || "h-10 w-10"}`}
        >
          <AtSign className="h-4 w-4" />
          {selectedContexts.length > 0 && (
            <div className="absolute top-0 right-0 h-2 w-2 bg-primary rounded-full" />
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent
        side="bottom"
        align="start"
        className="p-0 w-[300px] max-h-[400px] overflow-hidden"
      >
        <Command>
          <CommandInput
            placeholder="Search projects or datasets..."
            value={searchQuery}
            onValueChange={setSearchQuery}
          />
          <CommandList className="max-h-[320px]">
            <CommandEmpty>No results found.</CommandEmpty>

            {/* Selected contexts */}
            {selectedContexts.length > 0 && (
              <>
                <CommandGroup heading="Selected">
                  {selectedContexts.map((context) => (
                    <CommandItem
                      key={`selected-${context.id}`}
                      className="flex items-center justify-between"
                    >
                      <div className="flex items-center gap-2">
                        <Badge
                          variant={
                            context.type === "project" ? "outline" : "secondary"
                          }
                          className="h-5 px-1.5 text-xs"
                        >
                          {context.type === "project" ? "Project" : "Dataset"}
                        </Badge>
                        <span className="truncate">{context.name}</span>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        className={`h-6 w-6 p-0 ${
                          lockableContextIds.includes(context.id)
                            ? "opacity-40 pointer-events-none"
                            : ""
                        }`}
                        onClick={() => onRemoveContext(context.id)}
                      >
                        <X className="h-3 w-3" />
                      </Button>
                    </CommandItem>
                  ))}
                </CommandGroup>
                <CommandSeparator />
              </>
            )}

            {/* Projects */}
            <CommandGroup heading="Projects">
              {filteredProjects.length === 0 ? (
                <CommandItem disabled>No projects found</CommandItem>
              ) : (
                filteredProjects.map((project) => {
                  const isSelected = selectedContexts.some(
                    (c) => c.id === project.id && c.type === "project"
                  );

                  return (
                    <CommandItem
                      key={`project-${project.id}`}
                      onSelect={() => {
                        if (!isSelected) {
                          onSelectContext({
                            id: project.id,
                            type: "project",
                            name: project.name,
                          });
                        } else {
                          onRemoveContext(project.id);
                        }
                      }}
                    >
                      <div className="flex items-center justify-between w-full">
                        <span className="truncate">{project.name}</span>
                        {isSelected && <Check className="h-4 w-4" />}
                      </div>
                    </CommandItem>
                  );
                })
              )}
            </CommandGroup>

            {/* Datasets */}
            <CommandGroup heading="Datasets">
              {allDatasets.length === 0 ? (
                // TODO: handle proper loading
                <CommandItem disabled>No datasets found</CommandItem>
              ) : filteredDatasets.length === 0 ? (
                <CommandItem disabled>No datasets found</CommandItem>
              ) : (
                filteredDatasets.map((dataset) => {
                  const isSelected = selectedContexts.some(
                    (c) => c.id === dataset.id && c.type === "dataset"
                  );

                  // Find project for this dataset - using projectId property instead of checking if ID starts with project ID
                  const project = projectsData?.results.find(
                    (p) => p.id === dataset.projectId
                  );

                  return (
                    <CommandItem
                      key={`dataset-${dataset.id}`}
                      onSelect={() => {
                        if (!isSelected && project) {
                          onSelectContext({
                            id: dataset.id,
                            type: "dataset",
                            name: dataset.alias,
                            projectId: project.id,
                          });
                        } else if (isSelected) {
                          onRemoveContext(dataset.id);
                        }
                      }}
                    >
                      <div className="flex items-center justify-between w-full">
                        <div className="flex flex-col">
                          <span className="truncate">{dataset.alias}</span>
                          {project && (
                            <span className="text-xs text-muted-foreground truncate">
                              {project.name}
                            </span>
                          )}
                        </div>
                        {isSelected && <Check className="h-4 w-4" />}
                      </div>
                    </CommandItem>
                  );
                })
              )}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}

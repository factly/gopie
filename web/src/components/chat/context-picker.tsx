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
import { fetchDatasets } from "@/lib/queries/dataset/list-datasets";
import { Dataset } from "@/lib/api-client";

export interface ContextItem {
  id: string;
  type: "project" | "dataset";
  name: string;
  projectId?: string; // Only applicable for datasets
}

interface ContextPickerProps {
  selectedContexts: ContextItem[];
  onSelectContext: (context: ContextItem) => void;
  onRemoveContext: (contextId: string) => void;
  currentDatasetId?: string;
  currentProjectId?: string;
  triggerClassName?: string;
}

export function ContextPicker({
  selectedContexts,
  onSelectContext,
  onRemoveContext,
  currentDatasetId,
  currentProjectId,
  triggerClassName,
}: ContextPickerProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [allDatasets, setAllDatasets] = useState<
    (Dataset & { projectId: string })[]
  >([]);

  // Fetch all projects
  const { data: projectsData, isLoading: isLoadingProjects } = useProjects({
    variables: { limit: 1000 }, // Large limit to avoid pagination
  });

  const projects = projectsData?.results || [];

  // For each project, fetch all datasets
  const fetchAllDatasets = async () => {
    if (!projects.length) return;

    const allDatasetsArray: (Dataset & { projectId: string })[] = [];

    for (const project of projects) {
      try {
        const data = await fetchDatasets({
          projectId: project.id,
          limit: 1000,
        });

        if (data.results) {
          // Add projectId to each dataset
          const datasetsWithProject = data.results.map((dataset) => ({
            ...dataset,
            projectId: project.id,
          }));
          allDatasetsArray.push(...datasetsWithProject);
        }
      } catch (error) {
        console.error(
          `Failed to fetch datasets for project ${project.id}:`,
          error
        );
      }
    }

    setAllDatasets(allDatasetsArray);
  };

  useEffect(() => {
    if (projects.length > 0) {
      fetchAllDatasets();
    }
  }, [projects]);

  // Filter projects and datasets based on search query
  const filteredProjects = projects.filter((project) =>
    project.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const filteredDatasets = allDatasets.filter((dataset) =>
    dataset.alias.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Ensure current dataset is pre-selected
  useEffect(() => {
    if (currentDatasetId && currentProjectId) {
      const currentDataset = allDatasets.find((d) => d.id === currentDatasetId);

      if (
        currentDataset &&
        !selectedContexts.some((c) => c.id === currentDatasetId)
      ) {
        onSelectContext({
          id: currentDatasetId,
          type: "dataset",
          name: currentDataset.alias,
          projectId: currentProjectId,
        });
      }
    }
  }, [currentDatasetId, currentProjectId, allDatasets]);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className={`relative flex items-center justify-center bg-background/80 border border-input hover:bg-accent hover:text-accent-foreground ${
            triggerClassName || ""
          }`}
        >
          <AtSign className="h-4 w-4" />
          <span className="sr-only">Context</span>
          {selectedContexts.length > 0 && (
            <Badge
              variant="secondary"
              rounded="full"
              className="absolute -top-1 -right-1 h-5 w-5 p-0 flex items-center justify-center text-xs font-medium"
            >
              {selectedContexts.length}
            </Badge>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[350px] p-0" align="start">
        <Command>
          <CommandInput
            placeholder="Search projects and datasets..."
            value={searchQuery}
            onValueChange={setSearchQuery}
          />
          <CommandList>
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
                        className="h-6 w-6 p-0"
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
              {isLoadingProjects ? (
                <CommandItem disabled>Loading projects...</CommandItem>
              ) : filteredProjects.length === 0 ? (
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
                <CommandItem disabled>Loading datasets...</CommandItem>
              ) : filteredDatasets.length === 0 ? (
                <CommandItem disabled>No datasets found</CommandItem>
              ) : (
                filteredDatasets.map((dataset) => {
                  const isSelected = selectedContexts.some(
                    (c) => c.id === dataset.id && c.type === "dataset"
                  );

                  // Find project for this dataset - using projectId property instead of checking if ID starts with project ID
                  const project = projects.find(
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

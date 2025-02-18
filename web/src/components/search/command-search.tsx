"use client";

import * as React from "react";
import { useHotkeys } from "react-hotkeys-hook";
import { Search, Folder, Database } from "lucide-react";

import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { useProjects } from "@/lib/queries/project/list-projects";
import { useDatasets } from "@/lib/queries/dataset/list-datasets";
import { DialogTitle } from "@/components/ui/dialog";
import { VisuallyHidden } from "@/components/ui/visually-hidden";
import { useDebounce } from "@/hooks/use-debounce";

interface CommandSearchProps {
  projectId?: string;
  onNavigate: (path: string) => void;
}

export function CommandSearch({ projectId, onNavigate }: CommandSearchProps) {
  const [open, setOpen] = React.useState(false);
  const [inputValue, setInputValue] = React.useState("");
  const search = useDebounce(inputValue, 300); // 300ms debounce

  // Query projects
  const { data: projects } = useProjects({
    variables: {
      query: search,
    },
  });

  // Query datasets (across all projects when searching)
  const { data: datasets } = useDatasets({
    variables: {
      projectId: projectId || "", // Use provided project ID if available
      query: search,
    },
  });

  React.useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((open) => !open);
      }
    };

    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  // Also bind to forward slash for quick search
  useHotkeys("/", (e) => {
    e.preventDefault();
    setOpen(true);
  });

  const handleSelect = (path: string) => {
    onNavigate(path);
    setOpen(false);
  };

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="inline-flex items-center gap-2 rounded-md border bg-background px-3 py-2 text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
      >
        <Search className="size-4" />
        <span className="hidden md:inline-flex">Search...</span>
        <kbd className="pointer-events-none hidden h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium opacity-100 md:inline-flex">
          <span className="text-xs">⌘</span>K
        </kbd>
      </button>
      <CommandDialog open={open} onOpenChange={setOpen}>
        <VisuallyHidden asChild>
          <DialogTitle>Search projects and datasets</DialogTitle>
        </VisuallyHidden>
        <CommandInput
          placeholder="Search projects and datasets..."
          value={inputValue}
          onValueChange={setInputValue}
        />
        <CommandList>
          <CommandEmpty>No results found.</CommandEmpty>
          {projects?.results && projects.results.length > 0 && (
            <CommandGroup heading="Projects">
              {projects.results.map((project) => (
                <CommandItem
                  key={project.id}
                  value={`${project.name} ${project.description || ""}`}
                  onSelect={() => handleSelect(`/${project.id}`)}
                >
                  <Folder className="mr-2 size-4" />
                  <div className="flex flex-col gap-1">
                    <div>{project.name}</div>
                    {project.description && (
                      <div className="text-xs text-muted-foreground line-clamp-1">
                        {project.description}
                      </div>
                    )}
                  </div>
                </CommandItem>
              ))}
            </CommandGroup>
          )}
          {datasets?.results && datasets.results.length > 0 && (
            <CommandGroup heading="Datasets">
              {datasets.results.map((dataset) => (
                <CommandItem
                  key={dataset.id}
                  value={`${dataset.name} ${dataset.description || ""}`}
                  onSelect={() => handleSelect(`/${projectId}/${dataset.id}`)}
                >
                  <Database className="mr-2 size-4" />
                  <div className="flex flex-col gap-1">
                    <div>{dataset.name}</div>
                    {dataset.description && (
                      <div className="text-xs text-muted-foreground line-clamp-1">
                        {dataset.description}
                      </div>
                    )}
                  </div>
                </CommandItem>
              ))}
            </CommandGroup>
          )}
        </CommandList>
      </CommandDialog>
    </>
  );
}

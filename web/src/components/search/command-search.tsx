"use client";

import * as React from "react";
import { useHotkeys } from "react-hotkeys-hook";
import { Search, Folder, Database, Loader2 } from "lucide-react";

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
import { useSidebar } from "../ui/sidebar";

interface CommandSearchProps {
  projectId?: string;
  onNavigate: (path: string) => void;
}

export function CommandSearch({ projectId, onNavigate }: CommandSearchProps) {
  const [open, setOpen] = React.useState(false);
  const [inputValue, setInputValue] = React.useState("");
  const search = useDebounce(inputValue, 300);
  const [isLoading, setIsLoading] = React.useState(false);

  // Query projects
  const { data: projects, isLoading: projectsLoading } = useProjects({
    variables: {
      query: search,
    },
  });

  // Query datasets (across all projects when searching)
  const { data: datasets, isLoading: datasetsLoading } = useDatasets({
    variables: {
      projectId: projectId || "",
      query: search,
    },
  });

  React.useEffect(() => {
    setIsLoading(projectsLoading || datasetsLoading);
  }, [projectsLoading, datasetsLoading]);

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

  const { open: isSidebarOpen } = useSidebar();

  const highlightMatch = (text: string) => {
    if (!search) return text;
    const parts = text.split(new RegExp(`(${search})`, "gi"));
    return parts.map((part, i) =>
      part.toLowerCase() === search.toLowerCase() ? (
        <span key={i} className="bg-yellow-200 dark:bg-yellow-900">
          {part}
        </span>
      ) : (
        part
      )
    );
  };

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className={`inline-flex items-center gap-2 rounded-md border bg-background shadow-sm ${
          isSidebarOpen ? "px-3 py-2" : "p-2"
        } text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground hover:border-accent-foreground/20 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-ring`}
      >
        <Search className="h-4 w-4" />
        {isSidebarOpen && (
          <>
            <span className="hidden md:inline-flex">Quick search...</span>
            <kbd className="pointer-events-none hidden h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium opacity-100 md:inline-flex">
              <span className="text-xs">⌘</span>K
            </kbd>
          </>
        )}
      </button>
      <CommandDialog open={open} onOpenChange={setOpen}>
        <VisuallyHidden asChild>
          <DialogTitle>Search projects and datasets</DialogTitle>
        </VisuallyHidden>
        <div className="relative">
          <CommandInput
            placeholder="Search projects and datasets..."
            value={inputValue}
            onValueChange={setInputValue}
          />
          {isLoading && (
            <div className="absolute right-3 top-3">
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            </div>
          )}
        </div>
        <CommandList>
          <CommandEmpty className="py-6 text-center text-sm">
            <div className="space-y-1">
              <p className="text-muted-foreground">No results found.</p>
              <p className="text-xs text-muted-foreground">
                Try searching for project or dataset names
              </p>
            </div>
          </CommandEmpty>
          {projects?.results && projects.results.length > 0 && (
            <CommandGroup heading="Projects">
              {projects.results.map((project) => (
                <CommandItem
                  key={project.id}
                  value={`${project.name} ${project.description || ""}`}
                  onSelect={() => handleSelect(`/${project.id}`)}
                  className="group"
                >
                  <Folder className="mr-2 h-4 w-4 text-muted-foreground group-hover:text-foreground transition-colors" />
                  <div className="flex flex-col gap-1">
                    <div>{highlightMatch(project.name)}</div>
                    {project.description && (
                      <div className="text-xs text-muted-foreground line-clamp-1">
                        {highlightMatch(project.description)}
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
                  className="group"
                >
                  <Database className="mr-2 h-4 w-4 text-muted-foreground group-hover:text-foreground transition-colors" />
                  <div className="flex flex-col gap-1">
                    <div>{highlightMatch(dataset.name)}</div>
                    {dataset.description && (
                      <div className="text-xs text-muted-foreground line-clamp-1">
                        {highlightMatch(dataset.description)}
                      </div>
                    )}
                  </div>
                </CommandItem>
              ))}
            </CommandGroup>
          )}
          <div className="py-2 px-2 text-xs text-muted-foreground border-t">
            <div className="flex items-center justify-between">
              <div>
                <span className="opacity-50">↑↓</span> to navigate
              </div>
              <div>
                <span className="opacity-50">enter</span> to select
              </div>
              <div>
                <span className="opacity-50">esc</span> to close
              </div>
            </div>
          </div>
        </CommandList>
      </CommandDialog>
    </>
  );
}

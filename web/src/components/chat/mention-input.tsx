import { useState, useRef, useEffect, KeyboardEvent, ReactNode } from "react";
import { X, Sparkles, Send } from "lucide-react";
import { Input } from "@/components/ui/input";
import {
  Command,
  CommandGroup,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverAnchor,
} from "@/components/ui/popover";
import { Badge } from "@/components/ui/badge";
import { ContextItem } from "./context-picker";
import { useProjects } from "@/lib/queries/project/list-projects";
import { fetchDatasets } from "@/lib/queries/dataset/list-datasets";
import { Dataset } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

interface MentionInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  disabled?: boolean;
  placeholder?: string;
  selectedContexts: ContextItem[];
  onSelectContext: (context: ContextItem) => void;
  onRemoveContext: (contextId: string) => void;
  className?: string;
  actionButtons?: ReactNode;
  showSendButton?: boolean;
  isSending?: boolean;
}

export function MentionInput({
  value,
  onChange,
  onSubmit,
  disabled = false,
  placeholder = "Type your message...",
  selectedContexts,
  onSelectContext,
  onRemoveContext,
  className = "",
  actionButtons,
  showSendButton = false,
  isSending = false,
}: MentionInputProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);
  const [cursorPosition, setCursorPosition] = useState<number | null>(null);
  const [showMentionPopover, setShowMentionPopover] = useState(false);
  const [mentionResults, setMentionResults] = useState<{
    projects: { id: string; name: string }[];
    datasets: { id: string; name: string; projectId: string; alias: string }[];
  }>({
    projects: [],
    datasets: [],
  });

  // Get projects
  const { data: projectsData } = useProjects({
    variables: { limit: 1000 },
  });

  // Handle input changes and detect @ mentions
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    const currentPosition = e.target.selectionStart || 0;

    // Store cursor position before React re-renders
    const newCursorPosition = currentPosition;

    // Update input value
    onChange(newValue);

    // Save cursor position for later use
    setCursorPosition(newCursorPosition);

    // Check if the user is trying to mention something
    const textBeforeCursor = newValue.substring(0, currentPosition);
    const mentionMatch = textBeforeCursor.match(/@([^@\s]*)$/);

    if (mentionMatch) {
      setShowMentionPopover(true);
      searchMentions(mentionMatch[1]);
    } else {
      setShowMentionPopover(false);
    }

    // Set cursor position after React updates the DOM
    setTimeout(() => {
      if (inputRef.current) {
        inputRef.current.setSelectionRange(
          newCursorPosition,
          newCursorPosition
        );
      }
    }, 0);
  };

  // Handle @ key press to explicitly open the menu
  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "@") {
      setShowMentionPopover(true);
      searchMentions("");
    } else if (e.key === "Escape") {
      setShowMentionPopover(false);
    }
  };

  // Focus input on mount
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }, []);

  // Maintain cursor position when input value changes
  useEffect(() => {
    if (inputRef.current && cursorPosition !== null) {
      inputRef.current.setSelectionRange(cursorPosition, cursorPosition);
    }
  }, [value, cursorPosition]);

  // Close mention popover when clicking outside, but not when clicking inside the popover or input
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        inputRef.current &&
        !inputRef.current.contains(event.target as Node) &&
        popoverRef.current &&
        !popoverRef.current.contains(event.target as Node)
      ) {
        setShowMentionPopover(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  // Search for projects and datasets that match the mention query
  const searchMentions = async (query: string) => {
    const projects = projectsData?.results || [];
    const filteredProjects = projects.filter((project) =>
      project.name.toLowerCase().includes(query.toLowerCase())
    );

    const allDatasets: Dataset[] = [];
    for (const project of projects) {
      try {
        const data = await fetchDatasets({
          projectId: project.id,
          limit: 100,
          query,
        });

        if (data.results) {
          allDatasets.push(...data.results);
        }
      } catch (error) {
        console.error(
          `Failed to fetch datasets for project ${project.id}:`,
          error
        );
      }
    }

    setMentionResults({
      projects: filteredProjects.map((p) => ({ id: p.id, name: p.name })),
      datasets: allDatasets.map((d) => ({
        id: d.id,
        name: d.alias,
        projectId: d.id.split("/")[0], // Assuming projectId is first part of dataset ID
        alias: d.alias,
      })),
    });
  };

  // Handle selection of a mention
  const handleSelectMention = (item: {
    id: string;
    name: string;
    type: "project" | "dataset";
    projectId?: string;
  }) => {
    // Add to selected contexts if not already selected
    if (!selectedContexts.some((c) => c.id === item.id)) {
      onSelectContext({
        id: item.id,
        type: item.type,
        name: item.name,
        projectId: item.projectId,
      });
    }

    // Add the mention to the input
    // let newText = value;
    // if (cursorPosition !== null && inputRef.current) {
    //   const beforeMention = value
    //     .substring(0, cursorPosition)
    //     .replace(/@[^@\s]*$/, "");
    //   const afterMention = value.substring(cursorPosition);
    //   newText = `${beforeMention}@${item.name} ${afterMention}`;
    // } else {
    //   // If we don't have cursor position, just append
    //   newText = `${value}@${item.name} `;
    // }
    // onChange(newText);

    // Close the popover
    setShowMentionPopover(false);

    // Focus the input and set cursor after the mention
    setTimeout(() => {
      if (inputRef.current) {
        inputRef.current.focus();

        if (cursorPosition !== null) {
          // Set cursor position after the mention
          const beforeMention = value
            .substring(0, cursorPosition)
            .replace(/@[^@\s]*$/, "");
          const newPosition = beforeMention.length + item.name.length + 2; // +2 for @ and space
          inputRef.current.setSelectionRange(newPosition, newPosition);
        }
      }
    }, 10); // Slightly longer timeout to ensure UI updates first
  };

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit(e);
      }}
      className="relative w-full"
    >
      <div className="relative">
        <div
          className={cn(
            "flex flex-col justify-center rounded-lg border bg-background px-4 pr-10 shadow-sm transition-all duration-200",
            "hover:shadow-md focus-within:shadow-md",
            selectedContexts.length > 0
              ? "min-h-[4rem] py-2.5"
              : "min-h-[3.25rem]",
            "w-full",
            className,
            disabled ? "opacity-50" : ""
          )}
        >
          {/* <div className="absolute left-3 top-1/2 transform -translate-y-1/2 flex items-center justify-center h-5 w-5">
            <AtSign className="h-4 w-4 text-muted-foreground opacity-70" />
          </div> */}

          {/* Display selected contexts as badges above the input */}
          {selectedContexts.length > 0 && (
            <div className="flex flex-wrap gap-1.5 items-center w-full mb-2.5 max-h-[80px] overflow-y-auto scrollbar-thin pr-1">
              {selectedContexts.map((context) => (
                <Badge
                  key={`badge-${context.id}`}
                  variant={context.type === "project" ? "outline" : "secondary"}
                  className={cn(
                    "h-6 py-0.5 px-2 flex items-center gap-1.5 text-xs flex-shrink-0",
                    "transition-all duration-200 hover:opacity-90"
                  )}
                >
                  {context.type === "project" ? (
                    <Sparkles className="h-3 w-3 opacity-70" />
                  ) : (
                    <div className="h-2 w-2 bg-current opacity-70" />
                  )}
                  <span className="truncate max-w-32">{context.name}</span>
                  <X
                    className="h-3 w-3 cursor-pointer hover:text-red-500 transition-colors"
                    onClick={(e) => {
                      e.stopPropagation();
                      onRemoveContext(context.id);
                    }}
                  />
                </Badge>
              ))}
            </div>
          )}

          <Input
            ref={inputRef}
            className={cn(
              "flex-1 border-0 bg-transparent p-0 pr-[10.5rem]",
              "shadow-none focus-visible:ring-0 focus-visible:ring-offset-0 text-sm",
              !selectedContexts.length ? "py-4" : "py-1.5"
            )}
            placeholder={placeholder}
            value={value}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            disabled={disabled}
          />

          {/* Action buttons container */}
          <div className="absolute right-4 top-1/2 transform -translate-y-1/2 flex items-center gap-1.5">
            {actionButtons}
            {showSendButton && (
              <Button
                type="submit"
                size="icon"
                variant="default"
                className="h-9 w-9 rounded-full shadow-sm ml-0.5"
                disabled={disabled || !value.trim() || isSending}
              >
                {isSending ? (
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            )}
          </div>
        </div>

        <Popover
          open={showMentionPopover}
          onOpenChange={(open) => {
            setShowMentionPopover(open);
            // Re-focus the input when popover closes
            if (!open && inputRef.current) {
              setTimeout(() => {
                inputRef.current?.focus();
              }, 0);
            }
          }}
        >
          <PopoverAnchor asChild>
            <div className="absolute inset-0 pointer-events-none" />
          </PopoverAnchor>
          <PopoverContent
            ref={popoverRef}
            className="w-[300px] p-0 border shadow-lg"
            align="start"
            side="top"
            sideOffset={5}
            onClick={(e) => e.stopPropagation()}
          >
            <Command shouldFilter={false} className="overflow-hidden">
              <CommandList>
                {mentionResults.projects.length === 0 &&
                mentionResults.datasets.length === 0 ? (
                  <div className="py-6 text-center text-sm text-muted-foreground">
                    No results found
                  </div>
                ) : (
                  <>
                    {mentionResults.projects.length > 0 && (
                      <CommandGroup
                        heading="Projects"
                        className="px-1 text-xs font-medium"
                      >
                        {mentionResults.projects.map((project) => (
                          <CommandItem
                            key={`mention-project-${project.id}`}
                            onSelect={() => {
                              handleSelectMention({
                                ...project,
                                type: "project",
                              });
                            }}
                            className="cursor-pointer hover:bg-muted transition-colors my-0.5 text-sm"
                            onClick={() => {
                              handleSelectMention({
                                ...project,
                                type: "project",
                              });
                            }}
                          >
                            <div className="flex items-center gap-2">
                              <Badge
                                variant="outline"
                                className="h-5 px-1.5 text-xs flex items-center gap-1"
                              >
                                <Sparkles className="h-3 w-3 opacity-70" />
                                <span>Project</span>
                              </Badge>
                              <span className="text-sm">{project.name}</span>
                            </div>
                          </CommandItem>
                        ))}
                      </CommandGroup>
                    )}

                    {mentionResults.datasets.length > 0 && (
                      <CommandGroup
                        heading="Datasets"
                        className="px-1 text-xs font-medium"
                      >
                        {mentionResults.datasets.map((dataset) => (
                          <CommandItem
                            key={`mention-dataset-${dataset.id}`}
                            onSelect={() => {
                              handleSelectMention({
                                ...dataset,
                                type: "dataset",
                              });
                            }}
                            className="cursor-pointer hover:bg-muted transition-colors my-0.5 text-sm"
                            onClick={() => {
                              handleSelectMention({
                                ...dataset,
                                type: "dataset",
                              });
                            }}
                          >
                            <div className="flex items-center gap-2">
                              <Badge
                                variant="secondary"
                                className="h-5 px-1.5 text-xs flex items-center gap-1"
                              >
                                <div className="h-2 w-2 bg-current opacity-70" />
                                <span>Dataset</span>
                              </Badge>
                              <span className="text-sm">{dataset.alias}</span>
                            </div>
                          </CommandItem>
                        ))}
                      </CommandGroup>
                    )}
                  </>
                )}
              </CommandList>
            </Command>
          </PopoverContent>
        </Popover>
      </div>
    </form>
  );
}

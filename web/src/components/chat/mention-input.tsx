import {
  useCallback,
  useState,
  useRef,
  useEffect,
  ReactNode,
  KeyboardEvent,
} from "react";
import { X, Sparkles, Send, Square } from "lucide-react";
import { Textarea } from "@/components/ui/textarea";
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
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Badge } from "@/components/ui/badge";
import { ContextItem } from "./context-picker";
import { useProjects } from "@/lib/queries/project/list-projects";
import { useDatasets } from "@/lib/queries/dataset/list-datasets";
import { Dataset } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { useQueryClient } from "@tanstack/react-query";
import { debounce } from "@/lib/utils";

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
  isStreaming?: boolean;
  stopMessageStream?: () => void;
  lockableContextIds?: string[]; // Array of context IDs that cannot be removed
  hasContext?: boolean; // Whether any context is selected
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
  isStreaming = false,
  stopMessageStream = () => {},
  lockableContextIds,
  hasContext,
}: MentionInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);
  const [cursorPosition, setCursorPosition] = useState<number | null>(null);
  const [showMentionPopover, setShowMentionPopover] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [mentionResults, setMentionResults] = useState<{
    projects: { id: string; name: string }[];
    datasets: { id: string; name: string; projectId: string; alias: string }[];
  }>({
    projects: [],
    datasets: [],
  });

  const queryClient = useQueryClient();

  // Get projects
  const { data: projectsData } = useProjects({
    variables: { limit: 1000 },
  });

  // Define a debounced search function
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const debouncedSearch = useCallback(
    debounce((query: string) => {
      setSearchQuery(query);
    }, 300),
    []
  );

  // Auto-resize textarea
  const autoResizeTextarea = useCallback(() => {
    if (textareaRef.current) {
      const textarea = textareaRef.current;
      // Reset height to auto to get the correct scrollHeight
      textarea.style.height = "auto";

      const scrollHeight = textarea.scrollHeight;
      const maxHeight = 160; // Increased max height for better multi-line support (about 7 lines)
      const minHeight = 24; // Minimum height for single line

      if (scrollHeight <= maxHeight) {
        // If content fits within max height, set height to scrollHeight but not less than minHeight
        textarea.style.height = `${Math.max(scrollHeight, minHeight)}px`;
        textarea.style.overflowY = "hidden";
      } else {
        // If content exceeds max height, set to max height and enable scrolling
        textarea.style.height = `${maxHeight}px`;
        textarea.style.overflowY = "auto";
      }
    }
  }, []);

  // Handle input changes and detect @ mentions
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
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
      debouncedSearch(mentionMatch[1]);
    } else {
      setShowMentionPopover(false);
    }

    // Set cursor position after React updates the DOM
    setTimeout(() => {
      if (textareaRef.current) {
        textareaRef.current.setSelectionRange(
          newCursorPosition,
          newCursorPosition
        );
        // Auto-resize after cursor position is set
        autoResizeTextarea();
      }
    }, 0);
  };

  // Handle @ key press to explicitly open the menu
  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "@") {
      setShowMentionPopover(true);
      debouncedSearch("");
    } else if (e.key === "Escape") {
      setShowMentionPopover(false);
    } else if (e.key === "Enter") {
      if (e.shiftKey) {
        // Allow Shift+Enter for new lines (default textarea behavior)
        return;
      } else if (e.ctrlKey || e.metaKey) {
        // Allow Ctrl+Enter or Cmd+Enter to also submit
        e.preventDefault();
        if (value.trim() && !disabled) {
          onSubmit(e);
        }
      } else {
        // Regular Enter submits the form
        e.preventDefault();
        if (value.trim() && !disabled) {
          onSubmit(e);
        }
      }
    }
  };

  // Focus input on mount and setup auto-resize
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.focus();
      // Use setTimeout to ensure the textarea is properly rendered before auto-resizing
      setTimeout(() => {
        autoResizeTextarea();
      }, 0);
    }
  }, [autoResizeTextarea]);

  // Auto-resize when value changes
  useEffect(() => {
    setTimeout(() => {
      autoResizeTextarea();
    }, 0);
  }, [value, autoResizeTextarea]);

  // Maintain cursor position when input value changes
  useEffect(() => {
    if (textareaRef.current && cursorPosition !== null) {
      textareaRef.current.setSelectionRange(cursorPosition, cursorPosition);
    }
  }, [value, cursorPosition]);

  // Close mention popover when clicking outside, but not when clicking inside the popover or input
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        textareaRef.current &&
        !textareaRef.current.contains(event.target as Node) &&
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

  // Effect to search projects and datasets when searchQuery changes
  useEffect(() => {
    const loadMentionResults = async () => {
      const projects = projectsData?.results || [];
      const filteredProjects = projects.filter((project) =>
        project.name.toLowerCase().includes(searchQuery.toLowerCase())
      );

      // Start building results with filtered projects
      const results = {
        projects: filteredProjects.map((p) => ({ id: p.id, name: p.name })),
        datasets: [] as {
          id: string;
          name: string;
          projectId: string;
          alias: string;
        }[],
      };

      // Only search datasets if we have projects
      if (projects.length > 0) {
        // We'll collect all dataset queries and run them in parallel
        const datasetPromises = projects.map(async (project) => {
          try {
            const queryKey = [
              "datasets",
              { projectId: project.id, limit: 100, query: searchQuery },
            ];
            const cachedData = queryClient.getQueryData(queryKey);

            // If we have cached data, use it
            if (cachedData) {
              return { projectId: project.id, data: cachedData };
            }

            // Otherwise fetch it using the hook's fetcher
            const data = await queryClient.fetchQuery({
              queryKey,
              queryFn: async () => {
                const result = await useDatasets.fetcher({
                  projectId: project.id,
                  limit: 100,
                  query: searchQuery,
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
        datasetResults.forEach(({ data }) => {
          // Type guard to ensure data has results property and it's an array
          const hasResults =
            data &&
            typeof data === "object" &&
            "results" in data &&
            Array.isArray(data.results);

          if (hasResults) {
            results.datasets.push(
              ...data.results.map((d: Dataset) => ({
                id: d.id,
                name: d.alias,
                projectId: d.id.split("/")[0],
                alias: d.alias,
              }))
            );
          }
        });
      }

      setMentionResults(results);
    };

    if (showMentionPopover) {
      loadMentionResults();
    }
  }, [searchQuery, projectsData, showMentionPopover, queryClient]);

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

    // Close the popover
    setShowMentionPopover(false);

    // Focus the input and set cursor after the mention
    setTimeout(() => {
      if (textareaRef.current) {
        textareaRef.current.focus();

        if (cursorPosition !== null) {
          // Set cursor position after the mention
          const beforeMention = value
            .substring(0, cursorPosition)
            .replace(/@[^@\s]*$/, "");
          const newPosition = beforeMention.length + item.name.length + 2; // +2 for @ and space
          textareaRef.current.setSelectionRange(newPosition, newPosition);
        }
      }
    }, 10); // Slightly longer timeout to ensure UI updates first
  };

  const handleStopMessageStream = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();
      stopMessageStream();
    },
    [stopMessageStream]
  );

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
            "flex flex-col justify-start rounded-lg border bg-background px-4 shadow-sm transition-all duration-200",
            "hover:shadow-md focus-within:shadow-md",
            selectedContexts.length > 0
              ? "min-h-[4rem] py-3"
              : "min-h-[3.5rem] py-3",
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
                    className={cn(
                      "h-3 w-3 cursor-pointer hover:text-red-500 transition-colors",
                      lockableContextIds?.includes(context.id) &&
                        "pointer-events-none opacity-40"
                    )}
                    onClick={(e) => {
                      e.stopPropagation();
                      if (!lockableContextIds?.includes(context.id)) {
                        onRemoveContext(context.id);
                      }
                    }}
                  />
                </Badge>
              ))}
            </div>
          )}

          <div className="relative flex-1 flex items-start">
            <Textarea
              ref={textareaRef}
              className={cn(
                "w-full border-0 bg-transparent p-0 pr-16 resize-none",
                "shadow-none focus-visible:ring-0 focus-visible:ring-offset-0 text-sm",
                "min-h-[1.5rem] max-h-[160px] leading-6",
                "placeholder:text-muted-foreground",
                "transition-all duration-200"
              )}
              placeholder={placeholder}
              value={value}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              onFocus={() => setTimeout(() => autoResizeTextarea(), 0)}
              disabled={disabled}
              rows={1}
              style={{
                paddingTop: "0.25rem",
                paddingBottom: "0.25rem",
                lineHeight: "1.5",
              }}
            />
          </div>

          {/* Action buttons container - vertically centered for better alignment */}
          <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1.5">
            {actionButtons}
            {showSendButton && (
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      type={isStreaming ? "button" : "submit"}
                      size="icon"
                      variant={isStreaming ? "destructive" : "default"}
                      className="h-8 w-8 rounded-full shadow-sm"
                      disabled={
                        isStreaming
                          ? false
                          : disabled ||
                            !value.trim() ||
                            isSending ||
                            !hasContext
                      }
                      onClick={
                        isStreaming ? handleStopMessageStream : undefined
                      }
                    >
                      {isSending && !isStreaming ? (
                        <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
                      ) : isStreaming ? (
                        <Square className="h-3.5 w-3.5" />
                      ) : (
                        <Send className="h-3.5 w-3.5" />
                      )}
                    </Button>
                  </TooltipTrigger>
                  {!hasContext && !isStreaming && (
                    <TooltipContent>
                      <p>Select some context before sending</p>
                    </TooltipContent>
                  )}
                </Tooltip>
              </TooltipProvider>
            )}
          </div>
        </div>

        <Popover
          open={showMentionPopover}
          onOpenChange={(open) => {
            setShowMentionPopover(open);
            // Re-focus the input when popover closes
            if (!open && textareaRef.current) {
              setTimeout(() => {
                textareaRef.current?.focus();
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

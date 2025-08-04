import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  MoreVertical,
  Trash2,
  Play,
  ChevronDown,
  ChevronRight,
  Loader2,
  Database,
  ExternalLink,
  BarChart3,
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import ReactMarkdown from "react-markdown";
import { SqlPreview } from "@/components/dataset/sql/sql-preview";
import { SqlEditor } from "@/components/dataset/sql/sql-editor";
import { useDatasetSql } from "@/lib/mutations/dataset/sql";
import { useSqlStore } from "@/lib/stores/sql-store";
import { useVisualizationStore } from "@/lib/stores/visualization-store";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useEffect, useState, useCallback } from "react";
import { TextShimmerWave } from "@/components/ui/text-shimmer-wave";
// import { TTSButton } from "./tts-button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { useDatasetById } from "@/lib/queries/dataset/get-dataset-by-id";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { UIMessage } from "ai";

interface MessageContent {
  type: "text" | "sql";
  content: string;
}

// Define StreamEvent interface
interface StreamEvent {
  role: "intermediate" | "ai";
  content: string;
  datasets_used?: string[];
  generated_sql_query?: string;
}

function parseMessageContent(content: string): MessageContent {
  if (content.startsWith("---SQL---") && content.endsWith("---SQL---")) {
    return {
      type: "sql",
      content: content
        .replace(/^---SQL---/, "")
        .replace(/---SQL---$/, "")
        .trim(),
    };
  }
  if (content.startsWith("---TEXT---") && content.endsWith("---TEXT---")) {
    return {
      type: "text",
      content: content
        .replace(/^---TEXT---/, "")
        .replace(/---TEXT---$/, "")
        .trim(),
    };
  }
  return { type: "text", content };
}

interface ChatMessageProps {
  id: string;
  content: string | MessageContent[] | StreamEvent[];
  message?: UIMessage;
  role: "user" | "assistant" | "intermediate" | "ai";
  createdAt: string;
  isLoading?: boolean;
  streamAborted?: boolean;
  onDelete?: (messageId: string) => void;
  chatId?: string;
  isLatest?: boolean;
  finalizedDatasets?: string[];
  finalizedSqlQuery?: string;
}

// New component for dataset details
interface DatasetItemProps {
  datasetId: string;
  projectId?: string;
}

function DatasetItem({ datasetId, projectId }: DatasetItemProps) {
  const {
    data: dataset,
    isLoading,
    isError,
  } = useDatasetById({
    variables: { datasetId },
  });

  if (isLoading) {
    return (
      <span className="text-xs bg-primary/5 text-primary dark:bg-primary/10 dark:text-primary-foreground/70 px-2 py-0.5 font-mono flex items-center gap-1">
        <Loader2 className="h-3 w-3 animate-spin" />
        {datasetId.substring(0, 8)}...
      </span>
    );
  }

  if (isError || !dataset) {
    return (
      <span className="text-xs bg-destructive/10 text-destructive px-2 py-0.5 font-mono">
        {datasetId.substring(0, 8)}...
      </span>
    );
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Badge
          variant="outline"
          className="text-xs bg-primary/10 text-primary font-normal"
        >
          {projectId ? (
            <Link
              href={`/projects/${projectId}/datasets/${datasetId}`}
              className="flex items-center gap-1 hover:underline"
            >
              {dataset.alias}
              <ExternalLink className="h-3 w-3 ml-0.5" />
            </Link>
          ) : (
            dataset.alias
          )}
        </Badge>
      </TooltipTrigger>
      <TooltipContent className="w-60">
        <div className="space-y-1.5">
          <p className="font-medium">{dataset.name}</p>
          {dataset.description && (
            <p className="text-xs text-muted-foreground">
              {dataset.description}
            </p>
          )}
          <div className="text-xs">
            <span className="text-muted-foreground">Rows:</span>{" "}
            <span className="font-medium">
              {dataset.row_count.toLocaleString()}
            </span>
          </div>
        </div>
      </TooltipContent>
    </Tooltip>
  );
}

export function ChatMessage({
  id,
  content,
  message,
  role,
  createdAt,
  isLoading,
  streamAborted,
  onDelete,
  chatId,
  isLatest,
  finalizedDatasets,
  finalizedSqlQuery,
}: ChatMessageProps) {
  const executeSql = useDatasetSql();
  const {
    setResults,
    setIsOpen: setSqlPanelOpen,
    markQueryAsExecuted,
  } = useSqlStore();
  const { setPaths: setVisualizationPaths, setIsOpen: setVisualizationOpen } =
    useVisualizationStore();
  const [isExecuting, setIsExecuting] = useState(false);
  const [isCollapsibleOpen, setIsCollapsibleOpen] = useState(
    role === "intermediate" && typeof content === "string" ? true : false
  );
  const [isThoughtProcessOpen, setIsThoughtProcessOpen] = useState(false);
  const [displayDatasets, setDisplayDatasets] = useState<string[]>([]);
  const [displaySqlQueries, setDisplaySqlQueries] = useState<string[]>([]);
  const [displayIntermediateMessages, setDisplayIntermediateMessages] =
    useState<string[]>([]);
  const [displayVisualizationPaths, setDisplayVisualizationPaths] = useState<
    string[]
  >([]);
  const [displayVisualizationResults, setDisplayVisualizationResults] =
    useState<string[]>([]);
  const [expandedQueries, setExpandedQueries] = useState<Set<number>>(
    new Set()
  );
  const [editedQueries, setEditedQueries] = useState<Map<number, string>>(
    new Map()
  );

  const toggleQueryExpansion = (index: number) => {
    setExpandedQueries((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(index)) {
        newSet.delete(index);
      } else {
        newSet.add(index);
      }
      return newSet;
    });
  };

  const getQueryPreview = (query: string) => {
    const words = query.trim().split(/\s+/);
    const preview = words.slice(0, 4).join(" ");
    return preview.length < query.length ? `${preview}...` : preview;
  };

  // Process message parts from AI SDK
  useEffect(() => {
    if (message?.parts) {
      // Extract datasets from datasets_used tool calls
      const newDatasets: string[] = [];
      // Extract SQL from sql_queries tool calls
      const newSqlQueries: string[] = [];
      // Extract thought process messages from tool_messages tool calls
      const newIntermediateMessages: string[] = [];
      // Extract visualization paths from visualization_paths tool calls
      const newVisualizationPaths: string[] = [];
      // Extract visualization results from visualization_result tool calls
      const newVisualizationResults: string[] = [];

      message.parts.forEach((part) => {
        if (part.type === "tool-invocation") {
          const { toolName, args } = part.toolInvocation;

          if (toolName === "datasets_used" && args.datasets) {
            // Handle datasets_used tool
            args.datasets.forEach((dataset: string) => {
              if (!newDatasets.includes(dataset)) {
                newDatasets.push(dataset);
              }
            });
          }

          if (toolName === "sql_queries" && args.queries) {
            // Handle sql_queries tool (now expects an array of queries)
            if (Array.isArray(args.queries)) {
              newSqlQueries.push(...args.queries);
            } else if (typeof args.queries === "string") {
              newSqlQueries.push(args.queries);
            }
          }

          if (toolName === "tool_messages" && args.role && args.content) {
            // Handle tool_messages tool (thought process) - now expects role and content directly
            if (
              args.role === "intermediate" &&
              typeof args.content === "string"
            ) {
              newIntermediateMessages.push(args.content);
            }
          }

          if (toolName === "visualization_paths" && args.paths) {
            // Handle visualization_paths tool
            if (Array.isArray(args.paths)) {
              args.paths.forEach((path: string) => {
                if (!newVisualizationPaths.includes(path)) {
                  newVisualizationPaths.push(path);
                }
              });
            }
          }

          if (toolName === "visualization_result" && args.s3_paths) {
            // Handle visualization_result tool
            if (Array.isArray(args.s3_paths)) {
              args.s3_paths.forEach((path: string) => {
                if (!newVisualizationResults.includes(path)) {
                  newVisualizationResults.push(path);
                }
              });
            }
          }
        }
      });

      // Update state with extracted data
      if (newDatasets.length > 0) {
        setDisplayDatasets(newDatasets);
      } else if (finalizedDatasets && finalizedDatasets.length > 0) {
        setDisplayDatasets(finalizedDatasets);
      }

      if (newSqlQueries.length > 0) {
        setDisplaySqlQueries(newSqlQueries);
      } else if (finalizedSqlQuery) {
        setDisplaySqlQueries([finalizedSqlQuery]);
      }

      if (newIntermediateMessages.length > 0) {
        setDisplayIntermediateMessages(newIntermediateMessages);
        setIsThoughtProcessOpen(true);
      }

      if (newVisualizationPaths.length > 0) {
        setDisplayVisualizationPaths(newVisualizationPaths);
      }

      if (newVisualizationResults.length > 0) {
        setDisplayVisualizationResults(newVisualizationResults);
        setVisualizationPaths(newVisualizationResults, chatId);
      }
    } else if (Array.isArray(content)) {
      // Legacy handling for StreamEvent[]
      const allStreamDatasets = new Set<string>();
      const streamSqlQueries: string[] = [];
      const intermediateMessages: string[] = [];

      // Type guard to check if it's StreamEvent[]
      const isStreamEventArray = (
        arr: MessageContent[] | StreamEvent[]
      ): arr is StreamEvent[] => {
        return arr.length > 0 && "role" in arr[0];
      };

      if (isStreamEventArray(content)) {
        const streamContent = content as StreamEvent[];
        streamContent.forEach((event) => {
          if (event.datasets_used) {
            event.datasets_used.forEach((dataset) =>
              allStreamDatasets.add(dataset)
            );
          }
          if (event.generated_sql_query) {
            streamSqlQueries.push(event.generated_sql_query);
          }
          if (event.role === "intermediate") {
            intermediateMessages.push(event.content);
          }
        });
      }

      setDisplayDatasets(Array.from(allStreamDatasets));
      setDisplaySqlQueries(streamSqlQueries);
      setDisplayIntermediateMessages(intermediateMessages);
    } else {
      setDisplayDatasets(finalizedDatasets || []);
      setDisplaySqlQueries(finalizedSqlQuery ? [finalizedSqlQuery] : []);
    }
  }, [
    message,
    content,
    finalizedDatasets,
    finalizedSqlQuery,
    chatId,
    setVisualizationPaths,
  ]);

  const handleRunQuery = useCallback(
    async (query: string) => {
      setIsExecuting(true);
      try {
        const result = await executeSql.mutateAsync(query);
        setResults({
          data: result.data ?? [],
          total: result.data?.length ?? 0,
          query,
          chatId,
        });
        setSqlPanelOpen(true);
      } catch (error) {
        setResults({
          data: [],
          total: 0,
          error:
            error instanceof Error ? error.message : "Failed to execute query",
          query,
          chatId,
        });
        setSqlPanelOpen(true);
      } finally {
        setIsExecuting(false);
      }
    },
    [executeSql, setResults, setSqlPanelOpen, chatId]
  );

  useEffect(() => {
    if (!isLoading && (role === "assistant" || role === "ai") && isLatest) {
      let sqlToExecute: string | null = null;

      if (displaySqlQueries.length > 0) {
        // Execute the last query by default
        sqlToExecute = displaySqlQueries[displaySqlQueries.length - 1];
      } else if (typeof content === "string") {
        const parsed = parseMessageContent(content);
        if (parsed.type === "sql") {
          sqlToExecute = parsed.content;
        }
      } else if (message?.content) {
        const parsed = parseMessageContent(message.content);
        if (parsed.type === "sql") {
          sqlToExecute = parsed.content;
        }
      }

      if (sqlToExecute) {
        const shouldExecute = markQueryAsExecuted(id, sqlToExecute);
        if (shouldExecute) {
          handleRunQuery(sqlToExecute);
        }
      }
    }
  }, [
    content,
    message,
    isLoading,
    role,
    isLatest,
    handleRunQuery,
    id,
    markQueryAsExecuted,
    displaySqlQueries,
  ]);

  const styleRole =
    role === "ai" || role === "intermediate" ? "assistant" : role;

  // Extract text content from message or fallback to content
  const textContent =
    message?.content || (typeof content === "string" ? content : "");
  const parsedTextContent = parseMessageContent(textContent);

  if (
    isLoading &&
    !message?.parts?.length &&
    !(Array.isArray(content) && content.length > 0) &&
    styleRole === "assistant"
  ) {
    return (
      <div className={cn("group flex w-full justify-start")}>
        <div
          className={cn(
            "flex items-start gap-3 px-4 py-3",
            "w-fit max-w-[90%] min-w-0",
            "bg-muted shadow-sm border border-border/10"
          )}
        >
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <TextShimmerWave
                className="text-sm [--base-color:#71717a] [--base-gradient-color:#a1a1aa] dark:[--base-color:#a1a1aa] dark:[--base-gradient-color:#e4e4e7]"
                duration={1}
                spread={1}
              >
                Processing your request...
              </TextShimmerWave>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Special handling for intermediate role with string content
  if (role === "intermediate" && typeof content === "string" && !message) {
    return (
      <div className={cn("group flex w-full justify-start")}>
        <div
          className={cn(
            "flex items-start gap-3 px-4 py-3",
            "w-fit max-w-[90%] min-w-0",
            "bg-muted shadow-sm border border-border/10 border-dashed opacity-90"
          )}
          id={`message-${id}`}
          data-message-role={role}
          data-message-id={id}
        >
          <div className="flex-1 min-w-0">
            <Collapsible
              open={isCollapsibleOpen}
              onOpenChange={setIsCollapsibleOpen}
              className="w-full"
            >
              <div className="flex items-center justify-between">
                <CollapsibleTrigger className="flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                  {isCollapsibleOpen ? (
                    <ChevronDown className="h-4 w-4" />
                  ) : (
                    <ChevronRight className="h-4 w-4" />
                  )}
                  Agent is thinking...
                </CollapsibleTrigger>
                <span className="text-[11px] text-muted-foreground">
                  {new Date(createdAt).toLocaleTimeString()}
                </span>
              </div>
              <CollapsibleContent className="pt-2">
                <div
                  className={cn(
                    "prose prose-sm max-w-none break-words [&>:first-child]:mt-0 [&>:last-child]:mb-0 leading-relaxed",
                    "[&_code]:whitespace-pre-wrap [&_code]:break-words [&_pre]:border",
                    "[&_pre]:overflow-x-auto [&_pre]:whitespace-pre [&_pre]:shadow-sm",
                    "dark:prose-invert [&_*]:!my-0.5 prose-p:leading-relaxed prose-li:leading-relaxed prose-ul:!pl-4 prose-ol:!pl-4 [&_blockquote]:!pl-4 [&_pre]:!p-3 [&_blockquote]:border-l-2 [&_blockquote]:border-border"
                  )}
                >
                  <ReactMarkdown>{content}</ReactMarkdown>
                </div>
              </CollapsibleContent>
            </Collapsible>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "group flex w-full",
        styleRole === "user" ? "justify-end" : "justify-start"
      )}
    >
      <div
        className={cn(
          "flex flex-col items-start gap-2 px-4 py-3 min-w-0",
          styleRole === "user"
            ? "w-fit max-w-[90%] bg-primary text-primary-foreground shadow-sm"
            : "w-full bg-muted shadow-sm border border-border/10"
        )}
        id={`message-${id}`}
        data-message-role={role}
        data-message-id={id}
      >
        {/* Thought process section */}
        {displayIntermediateMessages.length > 0 && (
          <Collapsible
            open={isThoughtProcessOpen}
            onOpenChange={setIsThoughtProcessOpen}
            className="w-full"
          >
            <div className="flex items-center justify-between">
              <CollapsibleTrigger className="flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                {isThoughtProcessOpen ? (
                  <ChevronDown className="h-4 w-4" />
                ) : (
                  <ChevronRight className="h-4 w-4" />
                )}
                Agent thought process
              </CollapsibleTrigger>
            </div>
            <CollapsibleContent className="pt-2">
              <div
                className={cn(
                  "prose prose-sm max-w-none break-words [&>:first-child]:mt-0 [&>:last-child]:mb-0 leading-relaxed",
                  "[&_code]:whitespace-pre-wrap [&_code]:break-words [&_pre]:border",
                  "[&_pre]:overflow-x-auto [&_pre]:whitespace-pre [&_pre]:shadow-sm",
                  "dark:prose-invert [&_*]:!my-0.5 prose-p:leading-relaxed prose-li:leading-relaxed prose-ul:!pl-4 prose-ol:!pl-4 [&_blockquote]:!pl-4 [&_pre]:!p-3 [&_blockquote]:border-l-2 [&_blockquote]:border-border"
                )}
              >
                <ReactMarkdown>
                  {displayIntermediateMessages.join("\n\n")}
                </ReactMarkdown>
              </div>
            </CollapsibleContent>
          </Collapsible>
        )}

        <div className="flex-1 min-w-0 w-full pt-1 overflow-hidden">
          <div className="text-sm break-words space-y-3 min-w-0">
            {/* AI SDK parts-based rendering for text content */}
            {message?.parts ? (
              <>
                {message.parts.map((part, index) => {
                  if (part.type === "text") {
                    return (
                      <div
                        key={`${id}-part-${index}`}
                        className={cn(
                          "prose prose-sm max-w-none break-words [&>:first-child]:mt-0 [&>:last-child]:mb-0 leading-relaxed",
                          "[&_code]:whitespace-pre-wrap [&_code]:break-words [&_pre]:border",
                          "[&_pre]:overflow-x-auto [&_pre]:whitespace-pre [&_pre]:shadow-sm",
                          styleRole === "user"
                            ? "dark:prose-invert prose-p:text-primary-foreground prose-headings:text-primary-foreground prose-ul:text-primary-foreground prose-ol:text-primary-foreground prose-strong:text-primary-foreground [&_*]:text-primary-foreground"
                            : "dark:prose-invert [&_*]:!my-0.5 prose-p:leading-relaxed prose-li:leading-relaxed prose-ul:!pl-4 prose-ol:!pl-4 [&_blockquote]:!pl-4 [&_pre]:!p-3 [&_blockquote]:border-l-2 [&_blockquote]:border-border"
                        )}
                      >
                        <ReactMarkdown>{part.text}</ReactMarkdown>
                      </div>
                    );
                  }
                  return null;
                })}
              </>
            ) : (
              // Legacy text content rendering
              parsedTextContent.type === "text" &&
              parsedTextContent.content && (
                <div
                  className={cn(
                    "prose prose-sm max-w-none break-words [&>:first-child]:mt-0 [&>:last-child]:mb-0 leading-relaxed",
                    "[&_code]:whitespace-pre-wrap [&_code]:break-words [&_pre]:border",
                    "[&_pre]:overflow-x-auto [&_pre]:whitespace-pre [&_pre]:shadow-sm",
                    styleRole === "user"
                      ? "dark:prose-invert prose-p:text-primary-foreground prose-headings:text-primary-foreground prose-ul:text-primary-foreground prose-ol:text-primary-foreground prose-strong:text-primary-foreground [&_*]:text-primary-foreground"
                      : "dark:prose-invert [&_*]:!my-0.5 prose-p:leading-relaxed prose-li:leading-relaxed prose-ul:!pl-4 prose-ol:!pl-4 [&_blockquote]:!pl-4 [&_pre]:!p-3 [&_blockquote]:border-l-2 [&_blockquote]:border-border"
                  )}
                >
                  <ReactMarkdown>{parsedTextContent.content}</ReactMarkdown>
                </div>
              )
            )}

            {/* SQL Queries display */}
            {displaySqlQueries.length > 0 && (
              <div className="w-full max-w-full lg:max-w-[800px] text-base pt-2 space-y-3">
                <p className="text-xs text-muted-foreground font-medium mb-2">
                  Suggested SQL{" "}
                  {displaySqlQueries.length > 1 ? "Queries" : "Query"}:
                </p>
                {displaySqlQueries.map((query, index) => (
                  <Collapsible
                    key={index}
                    open={expandedQueries.has(index)}
                    onOpenChange={() => toggleQueryExpansion(index)}
                    className="border border-border bg-card shadow-sm min-w-0"
                  >
                    <CollapsibleTrigger className="flex items-center justify-between w-full p-3 text-sm font-medium text-left hover:bg-accent hover:text-accent-foreground transition-colors data-[state=open]:border-b-0">
                      <div className="flex items-center gap-3 min-w-0 flex-1">
                        {expandedQueries.has(index) ? (
                          <ChevronDown className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                        ) : (
                          <ChevronRight className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                        )}
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2 min-w-0">
                            <Database className="h-3.5 w-3.5 text-primary flex-shrink-0" />
                            <span className="text-foreground font-mono text-xs break-words overflow-hidden">
                              {getQueryPreview(query)}
                            </span>
                          </div>
                          {displaySqlQueries.length > 1 && (
                            <div className="text-[10px] text-muted-foreground mt-0.5">
                              Query {index + 1} of {displaySqlQueries.length}
                            </div>
                          )}
                        </div>
                      </div>
                      {!isLoading && (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={(e) => {
                            e.stopPropagation();
                            const queryToRun =
                              editedQueries.get(index) ?? query;
                            handleRunQuery(queryToRun);
                          }}
                          disabled={isExecuting}
                          className="h-7 px-2 text-xs ml-2 flex-shrink-0 hover:bg-primary hover:text-primary-foreground"
                        >
                          {isExecuting ? (
                            <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                          ) : (
                            <Play className="mr-1 h-3 w-3" />
                          )}
                          Run
                        </Button>
                      )}
                    </CollapsibleTrigger>
                    <CollapsibleContent className="border-t border-border">
                      <div className="p-3 pt-2">
                        <SqlEditor
                          value={editedQueries.get(index) ?? query}
                          onChange={(newValue) => {
                            setEditedQueries((prev) => {
                              const newMap = new Map(prev);
                              newMap.set(index, newValue);
                              return newMap;
                            });
                          }}
                          datasetId={""}
                        />
                      </div>
                    </CollapsibleContent>
                  </Collapsible>
                ))}
              </div>
            )}

            {/* SQL content fallback when no specific SQL query is identified */}
            {displaySqlQueries.length === 0 &&
              parsedTextContent.type === "sql" && (
                <div className="w-full max-w-full lg:max-w-[800px] text-base">
                  <div className="relative">
                    <SqlPreview value={parsedTextContent.content} />
                    {!isLoading && (
                      <div className="absolute top-2 right-2 flex items-center gap-2">
                        {isExecuting && (
                          <div className="flex items-center gap-1.5 text-xs text-muted-foreground bg-background/80 px-2.5 py-1 backdrop-blur-sm shadow-sm">
                            <span className="h-2 w-2 bg-primary/50 animate-pulse" />
                            Running...
                          </div>
                        )}
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Button
                              size="icon"
                              variant="ghost"
                              className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity"
                              onClick={() =>
                                handleRunQuery(parsedTextContent.content)
                              }
                              disabled={isExecuting}
                            >
                              <Play className="h-3 w-3" />
                            </Button>
                          </TooltipTrigger>
                          <TooltipContent>Run query</TooltipContent>
                        </Tooltip>
                      </div>
                    )}
                  </div>
                </div>
              )}

            {/* Loading indicator */}
            {isLoading && !textContent && displaySqlQueries.length === 0 && (
              <div className="flex items-center gap-1 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                AI response is generating...
              </div>
            )}

            {/* Stream aborted message */}
            {!isLoading &&
              streamAborted &&
              !textContent &&
              displaySqlQueries.length === 0 && (
                <div className="text-sm text-muted-foreground italic">
                  Stream stopped by user. No content was generated.
                </div>
              )}
          </div>

          {/* Visualization results section */}
          {displayVisualizationResults.length > 0 && (
            <div className="mt-3 pt-3 border-t border-border/50">
              <p className="text-xs text-muted-foreground font-medium mb-2 flex items-center">
                <BarChart3 className="h-3.5 w-3.5 mr-1.5 text-muted-foreground/80" />
                Generated {displayVisualizationResults.length} visualization
                {displayVisualizationResults.length !== 1 ? "s" : ""}
              </p>
              <div className="grid gap-2">
                {displayVisualizationResults.map((path, index) => (
                  <div
                    key={index}
                    className="group relative flex items-center justify-between p-3 bg-gradient-to-r from-emerald-50 to-teal-50 dark:from-emerald-950/30 dark:to-teal-950/30 border border-emerald-200/50 dark:border-emerald-800/30"
                  >
                    <div className="flex items-center gap-2 min-w-0 flex-1">
                      <BarChart3 className="h-4 w-4 text-emerald-600 dark:text-emerald-400 flex-shrink-0" />
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-emerald-900 dark:text-emerald-100">
                          Visualization {index + 1}
                        </p>
                        <p className="text-xs text-emerald-700 dark:text-emerald-300 truncate font-mono">
                          {path.split("/").pop() || path}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 px-2 text-xs text-emerald-700 dark:text-emerald-300 hover:bg-emerald-100 dark:hover:bg-emerald-900/50"
                        onClick={() => {
                          setVisualizationPaths(
                            displayVisualizationResults,
                            chatId
                          );
                          setVisualizationOpen(true);
                        }}
                      >
                        <BarChart3 className="h-3 w-3 mr-1" />
                        View
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 px-2 text-xs text-emerald-700 dark:text-emerald-300 hover:bg-emerald-100 dark:hover:bg-emerald-900/50"
                        onClick={() => window.open(path, "_blank")}
                      >
                        <ExternalLink className="h-3 w-3 mr-1" />
                        Code
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Datasets used section */}
          {displayDatasets.length > 0 && (
            <div className="mt-3 pt-3 border-t border-border/50">
              <p className="text-xs text-muted-foreground font-medium mb-1.5 flex items-center">
                <Database className="h-3.5 w-3.5 mr-1.5 text-muted-foreground/80" />
                Agent utilized the following dataset(s):
              </p>
              <div className="flex flex-wrap gap-1.5">
                {displayDatasets.map((datasetId) => (
                  <DatasetItem
                    key={datasetId}
                    datasetId={datasetId}
                    projectId={
                      datasetId && datasetId.includes("/")
                        ? datasetId.split("/")[0]
                        : undefined
                    }
                  />
                ))}
              </div>
            </div>
          )}

          {/* Visualization paths section */}
          {displayVisualizationPaths.length > 0 && (
            <div className="mt-3 pt-3 border-t border-border/50">
              <p className="text-xs text-muted-foreground font-medium mb-1.5">
                Visualization paths:
              </p>
              <div className="space-y-1">
                {displayVisualizationPaths.map((path, index) => (
                  <div
                    key={index}
                    className="text-xs bg-secondary/50 text-secondary-foreground px-2 py-1 font-mono"
                  >
                    {path}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Message footer: timestamp, TTS button, and delete option */}
          {!isLoading && (styleRole === "user" || textContent) && (
            <div className="flex items-center gap-2 mt-2">
              <span
                className={cn(
                  "text-[11px]",
                  styleRole === "user"
                    ? "text-primary-foreground/70"
                    : "text-muted-foreground"
                )}
              >
                {new Date(createdAt).toLocaleTimeString()}
              </span>

              {/* <div id={`tts-button-container-${id}`} data-tts-message-id={id}>
                <TTSButton
                  text={textContent}
                  role={styleRole}
                  datasetId={datasetId}
                />
              </div> */}

              {onDelete && chatId && (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className={cn(
                        "h-6 w-6 opacity-0 transition-opacity group-hover:opacity-100",
                        styleRole === "user"
                          ? "hover:bg-primary-foreground/10 text-primary-foreground"
                          : "hover:bg-muted"
                      )}
                    >
                      <MoreVertical className="h-3 w-3" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem
                      className="text-destructive"
                      onClick={() => onDelete(id)}
                    >
                      <Trash2 className="mr-2 h-4 w-4" />
                      Delete
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

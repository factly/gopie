"use client";

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
  FolderOpen,
  Lightbulb,
} from "lucide-react";
import { format } from "sql-formatter";
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
import { useResultsPanelStore } from "@/lib/stores/results-panel-store";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useEffect, useState, useCallback, memo, useMemo } from "react";
import { TextShimmerWave } from "@/components/ui/text-shimmer-wave";
// import { TTSButton } from "./tts-button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { useDatasetById } from "@/lib/queries/dataset/get-dataset-by-id";
import { useProject } from "@/lib/queries/project/get-project";
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

// Helper function to format SQL queries safely
function formatSqlQuery(sql: string): string {
  try {
    return format(sql, {
      language: "sql",
      tabWidth: 2,
      useTabs: false,
      keywordCase: "lower",
      linesBetweenQueries: 2,
    });
  } catch (error) {
    console.warn("Failed to format SQL:", error);
    // Return original query if formatting fails
    return sql;
  }
}

// Memoized component for rendering text parts to reduce re-renders during streaming
const MessageTextPart = memo(
  ({ text, styleRole }: { text: string; styleRole: string }) => {
    const className = useMemo(
      () =>
        cn(
          "prose prose-sm max-w-none break-words [&>:first-child]:mt-0 [&>:last-child]:mb-0 leading-relaxed",
          "[&_code]:whitespace-pre-wrap [&_code]:break-words [&_pre]:border",
          "[&_pre]:overflow-x-auto [&_pre]:whitespace-pre [&_pre]:shadow-sm",
          styleRole === "user"
            ? "dark:prose-invert prose-p:text-primary-foreground prose-headings:text-primary-foreground prose-ul:text-primary-foreground prose-ol:text-primary-foreground prose-strong:text-primary-foreground [&_*]:text-primary-foreground"
            : "dark:prose-invert [&_*]:!my-0.5 prose-p:leading-relaxed prose-li:leading-relaxed prose-ul:!pl-4 prose-ol:!pl-4 [&_blockquote]:!pl-4 [&_pre]:!p-3 [&_blockquote]:border-l-2 [&_blockquote]:border-border"
        ),
      [styleRole]
    );

    return (
      <div className={className}>
        <ReactMarkdown>{text}</ReactMarkdown>
      </div>
    );
  }
);
MessageTextPart.displayName = "MessageTextPart";

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
        .replace(/---SQL---$/, "")
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

// Component for displaying context information (projects and datasets)
interface ContextDisplayProps {
  projectIds: string[];
  datasetIds: string[];
}

function ContextDisplay({ projectIds, datasetIds }: ContextDisplayProps) {
  return (
    <div className="flex flex-wrap gap-1.5 mt-2">
      {projectIds.map((projectId) => (
        <ProjectItem key={projectId} projectId={projectId} />
      ))}
      {datasetIds.map((datasetId) => (
        <DatasetItem
          key={datasetId}
          datasetId={datasetId}
          projectId={
            datasetIds.length === 1 && projectIds.length === 1
              ? projectIds[0]
              : undefined
          }
        />
      ))}
    </div>
  );
}

// Component for displaying project information
interface ProjectItemProps {
  projectId: string;
}

function ProjectItem({ projectId }: ProjectItemProps) {
  const {
    data: project,
    isLoading,
    isError,
  } = useProject({
    variables: { projectId },
  });

  if (isLoading) {
    return (
      <Badge variant="secondary" className="text-xs">
        <Loader2 className="h-3 w-3 animate-spin mr-1" />
        Loading...
      </Badge>
    );
  }

  if (isError || !project) {
    return (
      <Badge variant="destructive" className="text-xs">
        Project not found
      </Badge>
    );
  }

  return (
    <Badge variant="secondary" className="text-xs font-normal">
      <Link
        href={`/projects/${projectId}`}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-1 hover:underline"
      >
        <FolderOpen className="h-3 w-3" />
        {project.name}
        <ExternalLink className="h-3 w-3 ml-0.5" />
      </Link>
    </Badge>
  );
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
      <Badge variant="secondary" className="text-xs">
        <Loader2 className="h-3 w-3 animate-spin mr-1" />
        {datasetId.substring(0, 8)}...
      </Badge>
    );
  }

  if (isError || !dataset) {
    return (
      <Badge variant="destructive" className="text-xs">
        {datasetId.substring(0, 8)}...
      </Badge>
    );
  }

  return (
    <Badge variant="secondary" className="text-xs font-normal">
      <Link
        href={`/projects/${projectId}/datasets/${datasetId}`}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-1 hover:underline"
      >
        <Database className="h-3 w-3" />
        {dataset.alias}
        <ExternalLink className="h-3 w-3 ml-0.5" />
      </Link>
    </Badge>
  );
}

export function ChatMessage({
  id,
  content,
  message,
  role,
  createdAt: _createdAt,
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
    setOnPageChange,
    setIsLoading,
    resetPagination,
    rowsPerPage,
  } = useSqlStore();
  const { setPaths: setVisualizationPaths, setIsOpen: setVisualizationOpen } =
    useVisualizationStore();
  const { setActiveTab } = useResultsPanelStore();
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
  const [expandedQueries, setExpandedQueries] = useState<number[]>([]);
  const [editedQueries, setEditedQueries] = useState<Record<number, string>>(
    {}
  );
  const [contextProjectIds, setContextProjectIds] = useState<string[]>([]);
  const [contextDatasetIds, setContextDatasetIds] = useState<string[]>([]);

  // Memoize these values at the component level to avoid conditional hook calls
  const latestThoughtProcessMessage = useMemo(
    () =>
      displayIntermediateMessages[displayIntermediateMessages.length - 1]
        ?.split("\n")
        .pop() || "Processing...",
    [displayIntermediateMessages]
  );

  const joinedIntermediateMessages = useMemo(
    () => displayIntermediateMessages.join("\n\n"),
    [displayIntermediateMessages]
  );

  const toggleQueryExpansion = (index: number) => {
    setExpandedQueries((prev) => {
      if (prev.includes(index)) {
        return prev.filter((i) => i !== index);
      } else {
        return [...prev, index];
      }
    });
  };

  const getQueryPreview = (query: string) => {
    // Format the query first for a better preview
    const formattedQuery = formatSqlQuery(query.trim());
    const words = formattedQuery.split(/\s+/);
    const preview = words.slice(0, 4).join(" ");
    return preview.length < formattedQuery.length ? `${preview}...` : preview;
  };

  // Process message parts from AI SDK with memoization to reduce re-renders
  useEffect(() => {
    if (message?.parts) {
      // Use requestAnimationFrame to defer state updates and batch them
      requestAnimationFrame(() => {
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
        // Extract context from set_context tool calls (for user messages)
        const newProjectIds: string[] = [];
        const newDatasetIds: string[] = [];

        message.parts.forEach((part) => {
          if (part.type === "tool-invocation") {
            const { toolName, args } = part.toolInvocation;

            // Handle set_context tool call (from user messages)
            if (toolName === "set_context") {
              if (args.project_ids && Array.isArray(args.project_ids)) {
                newProjectIds.push(...args.project_ids);
              }
              if (args.dataset_ids && Array.isArray(args.dataset_ids)) {
                newDatasetIds.push(...args.dataset_ids);
              }
            }

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

        // Batch state updates to reduce re-renders
        if (newProjectIds.length > 0) {
          setContextProjectIds(newProjectIds);
        }

        if (newDatasetIds.length > 0) {
          setContextDatasetIds(newDatasetIds);
        }

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
          // Keep thought process collapsed by default - user can manually expand if needed
        }

        if (newVisualizationPaths.length > 0) {
          setDisplayVisualizationPaths(newVisualizationPaths);
        }

        if (newVisualizationResults.length > 0) {
          setDisplayVisualizationResults(newVisualizationResults);
          setVisualizationPaths(newVisualizationResults, chatId);
          setActiveTab("visualizations"); // Auto-switch to visualizations tab when new visualizations are received
        }
      });
    } else if (Array.isArray(content)) {
      // Legacy handling for StreamEvent[]
      const allStreamDatasets: string[] = [];
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
            event.datasets_used.forEach((dataset) => {
              if (!allStreamDatasets.includes(dataset)) {
                allStreamDatasets.push(dataset);
              }
            });
          }
          if (event.generated_sql_query) {
            streamSqlQueries.push(event.generated_sql_query);
          }
          if (event.role === "intermediate") {
            intermediateMessages.push(event.content);
          }
        });
      }

      setDisplayDatasets(allStreamDatasets);
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
    setActiveTab,
    // Remove isLoading dependency to prevent re-renders during loading
  ]);

  // Extract text content from message or fallback to content (needed early for useEffect)
  const textContent =
    message?.content || (typeof content === "string" ? content : "");

  const handleRunQuery = useCallback(
    async (query: string, page: number = 1, limit: number = 20) => {
      setIsExecuting(true);
      setIsLoading(true);
      const offset = (page - 1) * limit;
      
      try {
        const result = await executeSql.mutateAsync({
          query,
          limit,
          offset,
        });
        setResults({
          data: result.data ?? [],
          total: result.count ?? result.data?.length ?? 0,
          columns: result.columns,
          query,
          chatId,
        });
        setSqlPanelOpen(true);
        setActiveTab("sql"); // Switch to SQL tab when running a query
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
        setActiveTab("sql"); // Switch to SQL tab even on error
      } finally {
        setIsExecuting(false);
        setIsLoading(false);
      }
    },
    [executeSql, setResults, setSqlPanelOpen, chatId, setActiveTab, setIsLoading]
  );

  // Execute SQL queries as soon as they appear (even while streaming)
  useEffect(() => {
    if (
      (role === "assistant" || role === "ai") &&
      isLatest &&
      displaySqlQueries.length > 0
    ) {
      // Execute the last query by default
      const sqlToExecute = displaySqlQueries[displaySqlQueries.length - 1];

      if (sqlToExecute) {
        const shouldExecute = markQueryAsExecuted(id, sqlToExecute);
        if (shouldExecute) {
          // Reset pagination for new query
          resetPagination();
          
          // Set up the page change callback for this query
          setOnPageChange((page: number, limit: number) => {
            handleRunQuery(sqlToExecute, page, limit);
          });
          
          // Use queueMicrotask to ensure non-blocking execution
          // This allows the SQL to run in parallel with streaming without blocking the UI
          queueMicrotask(() => {
            handleRunQuery(sqlToExecute, 1, rowsPerPage);
          });
        }
      }
    }
  }, [
    role,
    isLatest,
    handleRunQuery,
    id,
    markQueryAsExecuted,
    displaySqlQueries,
    resetPagination,
    setOnPageChange,
    rowsPerPage,
  ]);

  // Fallback for legacy SQL content (when not using displaySqlQueries)
  useEffect(() => {
    if (
      !isLoading &&
      (role === "assistant" || role === "ai") &&
      isLatest &&
      displaySqlQueries.length === 0
    ) {
      let sqlToExecute: string | null = null;

      if (typeof content === "string") {
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
          // Use queueMicrotask for non-blocking execution
          // Reset pagination for new query
          resetPagination();
          
          // Set up the page change callback for this query
          setOnPageChange((page: number, limit: number) => {
            handleRunQuery(sqlToExecute, page, limit);
          });
          
          queueMicrotask(() => {
            handleRunQuery(sqlToExecute, 1, rowsPerPage);
          });
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
    resetPagination,
    setOnPageChange,
    rowsPerPage,
  ]);

  const styleRole =
    role === "ai" || role === "intermediate" ? "assistant" : role;

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
              </div>
              <CollapsibleContent className="pt-2 pl-4">
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
              <CollapsibleTrigger className="flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors cursor-pointer p-1 -m-1 rounded hover:bg-accent">
                {isThoughtProcessOpen ? (
                  <ChevronDown className="h-4 w-4" />
                ) : (
                  <ChevronRight className="h-4 w-4" />
                )}
                {/* Always show lightbulb icon, animate it while loading */}
                <Lightbulb
                  className={cn(
                    "h-4 w-4",
                    isLoading
                      ? "animate-pulse text-yellow-500 dark:text-yellow-400"
                      : "text-muted-foreground"
                  )}
                />
                {/* Show title when expanded or not loading, show latest message when collapsed and loading */}
                {isThoughtProcessOpen || !isLoading ? (
                  "Agent thought process"
                ) : (
                  <span className="text-xs italic text-muted-foreground truncate max-w-[400px]">
                    {latestThoughtProcessMessage}
                  </span>
                )}
              </CollapsibleTrigger>
            </div>
            <CollapsibleContent className="pt-2 pl-5">
              <div
                className={cn(
                  "prose prose-sm max-w-none break-words [&>:first-child]:mt-0 [&>:last-child]:mb-0 leading-relaxed",
                  "[&_code]:whitespace-pre-wrap [&_code]:break-words [&_pre]:border",
                  "[&_pre]:overflow-x-auto [&_pre]:whitespace-pre [&_pre]:shadow-sm",
                  "dark:prose-invert [&_*]:!my-0.5 prose-p:leading-relaxed prose-li:leading-relaxed prose-ul:!pl-4 prose-ol:!pl-4 [&_blockquote]:!pl-4 [&_pre]:!p-3 [&_blockquote]:border-l-2 [&_blockquote]:border-border"
                )}
              >
                <ReactMarkdown>{joinedIntermediateMessages}</ReactMarkdown>
              </div>
            </CollapsibleContent>
          </Collapsible>
        )}

        <div className="flex-1 min-w-0 w-full pt-1 overflow-hidden">
          <div className="text-sm break-words space-y-3 min-w-0">
            {/* SQL Queries display - moved before text content for better UX flow */}
            {displaySqlQueries.length > 0 && (
              <div className="w-full max-w-full lg:max-w-[800px] text-base pt-2 space-y-3">
                {displaySqlQueries.map((query, index) => (
                  <Collapsible
                    key={index}
                    open={expandedQueries.includes(index)}
                    onOpenChange={() => toggleQueryExpansion(index)}
                    className="border border-border bg-card shadow-sm min-w-0"
                  >
                    <div className="flex items-center justify-between w-full p-3 text-sm font-medium text-left hover:bg-accent hover:text-accent-foreground transition-colors data-[state=open]:border-b-0">
                      <CollapsibleTrigger className="flex items-center gap-3 min-w-0 flex-1">
                        {expandedQueries.includes(index) ? (
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
                      </CollapsibleTrigger>
                      {!isLoading && (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={(e) => {
                            e.stopPropagation();
                            const queryToRun =
                              editedQueries[index] ?? formatSqlQuery(query);
                            resetPagination();
                            setOnPageChange((page: number, limit: number) => {
                              handleRunQuery(queryToRun, page, limit);
                            });
                            handleRunQuery(queryToRun, 1, rowsPerPage);
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
                    </div>
                    <CollapsibleContent className="border-t border-border">
                      <div className="p-3 pt-2">
                        <SqlEditor
                          value={editedQueries[index] ?? formatSqlQuery(query)}
                          onChange={(newValue) => {
                            setEditedQueries((prev) => ({
                              ...prev,
                              [index]: newValue,
                            }));
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
                    <SqlPreview
                      value={formatSqlQuery(parsedTextContent.content)}
                    />
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
                              onClick={() => {
                                const queryToRun = formatSqlQuery(parsedTextContent.content);
                                resetPagination();
                                setOnPageChange((page: number, limit: number) => {
                                  handleRunQuery(queryToRun, page, limit);
                                });
                                handleRunQuery(queryToRun, 1, rowsPerPage);
                              }}
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

            {/* AI SDK parts-based rendering for text content with memoization - moved after SQL for better flow */}
            {message?.parts ? (
              <>
                {message.parts.map((part, index) => {
                  if (part.type === "text") {
                    return (
                      <MessageTextPart
                        key={`${id}-part-${index}`}
                        text={part.text}
                        styleRole={styleRole}
                      />
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

            {/* Loading indicator */}
            {isLoading && !textContent && displaySqlQueries.length === 0 && (
              <div className="flex items-center gap-1 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Generating response...
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
                          setActiveTab("visualizations"); // Switch to visualizations tab
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
                        : contextProjectIds.length > 0
                        ? contextProjectIds[0]
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

          {/* Context display for user messages */}
          {styleRole === "user" &&
            (contextProjectIds.length > 0 || contextDatasetIds.length > 0) && (
              <ContextDisplay
                projectIds={contextProjectIds}
                datasetIds={contextDatasetIds}
              />
            )}

          {/* Message footer: delete option */}
          {!isLoading &&
            (styleRole === "user" || textContent) &&
            onDelete &&
            chatId && (
              <div className="flex items-center gap-2 mt-2">
                {/* <div id={`tts-button-container-${id}`} data-tts-message-id={id}>
                <TTSButton
                  text={textContent}
                  role={styleRole}
                  datasetId={datasetId}
                />
              </div> */}

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
              </div>
            )}
        </div>
      </div>
    </div>
  );
}

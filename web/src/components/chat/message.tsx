import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  MoreVertical,
  Trash2,
  Play,
  ChevronDown,
  ChevronRight,
  Loader2,
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import ReactMarkdown from "react-markdown";
import { SqlPreview } from "@/components/dataset/sql/sql-preview";
import { useDatasetSql } from "@/lib/mutations/dataset/sql";
import { useSqlStore } from "@/lib/stores/sql-store";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useEffect, useState, useCallback } from "react";
import { TextShimmerWave } from "@/components/ui/text-shimmer-wave";
import { TTSButton } from "./tts-button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

interface MessageContent {
  type: "text" | "sql";
  content: string;
}

// Define StreamEvent interface
interface StreamEvent {
  role: "intermediate" | "ai";
  content: string;
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
  content: string | StreamEvent[]; // Updated content type
  role: "user" | "assistant" | "intermediate" | "ai";
  createdAt: string;
  isLoading?: boolean;
  onDelete?: (messageId: string) => void;
  chatId?: string;
  isLatest?: boolean;
  datasetId?: string;
}

export function ChatMessage({
  id,
  content,
  role,
  createdAt,
  isLoading,
  onDelete,
  chatId,
  isLatest,
  datasetId,
}: ChatMessageProps) {
  const executeSql = useDatasetSql();
  const {
    setResults,
    setIsOpen: setSqlPanelOpen,
    markQueryAsExecuted,
  } = useSqlStore();
  const [isExecuting, setIsExecuting] = useState(false);
  const [isCollapsibleOpen, setIsCollapsibleOpen] = useState(
    role === "intermediate" && typeof content === "string" ? true : false
  ); // Default open for string intermediate messages
  const [isThoughtProcessOpen, setIsThoughtProcessOpen] = useState(
    Array.isArray(content) &&
      content.some((event) => event.role === "intermediate")
  );

  // Effect to update isThoughtProcessOpen when content changes (relevant if content can change type after mount)
  useEffect(() => {
    if (Array.isArray(content)) {
      setIsThoughtProcessOpen(
        content.some((event) => event.role === "intermediate")
      );
    } else {
      // If content is not an array, this collapsible isn't relevant, ensure it's closed or in a defined state
      setIsThoughtProcessOpen(false);
    }
  }, [content]);

  // Effect to update isCollapsibleOpen for string intermediate messages when props change
  useEffect(() => {
    setIsCollapsibleOpen(
      role === "intermediate" && typeof content === "string" ? true : false
    );
  }, [role, content]);

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
      if (typeof content === "string") {
        const parsed = parseMessageContent(content);
        if (parsed.type === "sql") {
          sqlToExecute = parsed.content;
        }
      } else if (Array.isArray(content)) {
        const aiEvents = content.filter((event) => event.role === "ai");
        const finalAiContentString = aiEvents
          .map((event) => event.content)
          .join("");
        if (finalAiContentString) {
          const parsed = parseMessageContent(finalAiContentString);
          if (parsed.type === "sql") {
            sqlToExecute = parsed.content;
          }
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
    isLoading,
    role,
    isLatest,
    handleRunQuery,
    id,
    markQueryAsExecuted,
  ]);

  const styleRole =
    role === "ai" || role === "intermediate" ? "assistant" : role;

  if (
    isLoading &&
    (!Array.isArray(content) || content.length === 0) &&
    styleRole === "assistant"
  ) {
    return (
      <div className={cn("group flex w-full justify-start")}>
        <div
          className={cn(
            "flex items-start gap-3 rounded-2xl px-4 py-3",
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
                AI is thinking...
              </TextShimmerWave>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (typeof content === "string" && !isLoading) {
    const isIntermediateStringMessage = role === "intermediate";
    const parsed = parseMessageContent(content);

    return (
      <div
        className={cn(
          "group flex w-full",
          styleRole === "user" ? "justify-end" : "justify-start"
        )}
      >
        <div
          className={cn(
            "flex items-start gap-3 rounded-2xl px-4 py-3",
            "w-fit max-w-[90%] min-w-0",
            styleRole === "user"
              ? "bg-primary text-primary-foreground shadow-sm"
              : "bg-muted shadow-sm border border-border/10",
            isIntermediateStringMessage && "border-dashed opacity-90"
          )}
          id={`message-${id}`}
          data-message-role={role}
          data-message-id={id}
        >
          <div className="flex-1 min-w-0">
            {isIntermediateStringMessage ? (
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
                      "[&_code]:whitespace-pre-wrap [&_code]:break-words [&_pre]:rounded-lg",
                      "[&_pre]:overflow-x-auto [&_pre]:whitespace-pre [&_pre]:shadow-sm",
                      "dark:prose-invert [&_*]:!my-0.5 prose-p:leading-relaxed prose-li:leading-relaxed prose-ul:!pl-4 prose-ol:!pl-4 [&_blockquote]:!pl-4 [&_pre]:!p-3 [&_blockquote]:border-l-2 [&_blockquote]:border-border"
                    )}
                  >
                    <ReactMarkdown>{parsed.content}</ReactMarkdown>
                  </div>
                </CollapsibleContent>
              </Collapsible>
            ) : (
              <>
                <div className="text-sm break-words">
                  {parsed.type === "sql" ? (
                    <div className="min-w-[400px] w-full max-w-[800px] text-base">
                      <div className="relative">
                        <SqlPreview value={parsed.content} />
                        <div className="absolute top-2 right-2 flex items-center gap-2">
                          {isExecuting && (
                            <div className="flex items-center gap-1.5 text-xs text-muted-foreground bg-background/80 px-2.5 py-1 rounded-full backdrop-blur-sm shadow-sm">
                              <span className="h-2 w-2 rounded-full bg-primary/50 animate-pulse" />
                              Running...
                            </div>
                          )}
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Button
                                size="icon"
                                variant="ghost"
                                className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity"
                                onClick={() => handleRunQuery(parsed.content)}
                                disabled={isExecuting}
                              >
                                <Play className="h-3 w-3" />
                              </Button>
                            </TooltipTrigger>
                            <TooltipContent>Run query</TooltipContent>
                          </Tooltip>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div
                      className={cn(
                        "prose prose-sm max-w-none break-words [&>:first-child]:mt-0 [&>:last-child]:mb-0 leading-relaxed",
                        "[&_code]:whitespace-pre-wrap [&_code]:break-words [&_pre]:rounded-lg",
                        "[&_pre]:overflow-x-auto [&_pre]:whitespace-pre [&_pre]:shadow-sm",
                        styleRole === "user"
                          ? "dark:prose-invert prose-p:text-primary-foreground prose-headings:text-primary-foreground prose-ul:text-primary-foreground prose-ol:text-primary-foreground prose-strong:text-primary-foreground [&_*]:text-primary-foreground"
                          : "dark:prose-invert [&_*]:!my-0.5 prose-p:leading-relaxed prose-li:leading-relaxed prose-ul:!pl-4 prose-ol:!pl-4 [&_blockquote]:!pl-4 [&_pre]:!p-3 [&_blockquote]:border-l-2 [&_blockquote]:border-border"
                      )}
                    >
                      <ReactMarkdown>{parsed.content}</ReactMarkdown>
                    </div>
                  )}
                </div>
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
                  {!isLoading && (
                    <div
                      id={`tts-button-container-${id}`}
                      data-tts-message-id={id}
                    >
                      <TTSButton
                        text={parsed.content}
                        role={styleRole}
                        datasetId={datasetId}
                      />
                    </div>
                  )}
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
              </>
            )}
          </div>
        </div>
      </div>
    );
  } else if (Array.isArray(content)) {
    // content is StreamEvent[]
    const intermediateEvents = content.filter(
      (event: StreamEvent) => event.role === "intermediate"
    );
    const aiEvents = content.filter(
      (event: StreamEvent) => event.role === "ai"
    );

    const intermediateContent = intermediateEvents
      .map((event: StreamEvent) => event.content)
      .join("\n\n");
    const finalAiContentString = aiEvents
      .map((event: StreamEvent) => event.content)
      .join("");
    const parsedFinalAiContent = parseMessageContent(finalAiContentString);

    return (
      <div
        className={cn(
          "group flex w-full",
          styleRole === "user" ? "justify-end" : "justify-start"
        )}
      >
        <div
          className={cn(
            "flex flex-col items-start gap-2 rounded-2xl px-4 py-3",
            "w-fit max-w-[90%] min-w-0",
            styleRole === "user" // Should not happen for StreamEvent content, but good practice
              ? "bg-primary text-primary-foreground shadow-sm"
              : "bg-muted shadow-sm border border-border/10"
          )}
          id={`message-${id}`}
          data-message-role={role}
          data-message-id={id}
        >
          {intermediateEvents.length > 0 && (
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
                    "[&_code]:whitespace-pre-wrap [&_code]:break-words [&_pre]:rounded-lg",
                    "[&_pre]:overflow-x-auto [&_pre]:whitespace-pre [&_pre]:shadow-sm",
                    "dark:prose-invert [&_*]:!my-0.5 prose-p:leading-relaxed prose-li:leading-relaxed prose-ul:!pl-4 prose-ol:!pl-4 [&_blockquote]:!pl-4 [&_pre]:!p-3 [&_blockquote]:border-l-2 [&_blockquote]:border-border"
                  )}
                >
                  <ReactMarkdown>{intermediateContent}</ReactMarkdown>
                </div>
              </CollapsibleContent>
            </Collapsible>
          )}

          {(finalAiContentString ||
            (isLoading && styleRole === "assistant")) && (
            <div className="flex-1 min-w-0 w-full pt-1">
              <div className="text-sm break-words">
                {parsedFinalAiContent.type === "sql" && finalAiContentString ? (
                  <div className="min-w-[400px] w-full max-w-[800px] text-base">
                    <div className="relative">
                      <SqlPreview value={parsedFinalAiContent.content} />
                      {!isLoading && (
                        <div className="absolute top-2 right-2 flex items-center gap-2">
                          {isExecuting && (
                            <div className="flex items-center gap-1.5 text-xs text-muted-foreground bg-background/80 px-2.5 py-1 rounded-full backdrop-blur-sm shadow-sm">
                              <span className="h-2 w-2 rounded-full bg-primary/50 animate-pulse" />
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
                                  handleRunQuery(parsedFinalAiContent.content)
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
                ) : finalAiContentString ? (
                  <div
                    className={cn(
                      "prose prose-sm max-w-none break-words [&>:first-child]:mt-0 [&>:last-child]:mb-0 leading-relaxed",
                      "[&_code]:whitespace-pre-wrap [&_code]:break-words [&_pre]:rounded-lg",
                      "[&_pre]:overflow-x-auto [&_pre]:whitespace-pre [&_pre]:shadow-sm",
                      "dark:prose-invert [&_*]:!my-0.5 prose-p:leading-relaxed prose-li:leading-relaxed prose-ul:!pl-4 prose-ol:!pl-4 [&_blockquote]:!pl-4 [&_pre]:!p-3 [&_blockquote]:border-l-2 [&_blockquote]:border-border"
                    )}
                  >
                    <ReactMarkdown>
                      {parsedFinalAiContent.content}
                    </ReactMarkdown>
                    {isLoading && styleRole === "assistant" && (
                      <span className="ml-1 text-xs text-muted-foreground animate-pulse">
                        (streaming...)
                      </span>
                    )}
                  </div>
                ) : isLoading && styleRole === "assistant" ? (
                  <div className="flex items-center gap-1 text-sm text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    AI response is generating...
                  </div>
                ) : null}
              </div>
              {!isLoading && (
                <div className="flex items-center gap-2 mt-2">
                  <span className={cn("text-[11px]", "text-muted-foreground")}>
                    {new Date(createdAt).toLocaleTimeString()}
                  </span>
                  <TTSButton
                    text={finalAiContentString}
                    role={styleRole}
                    datasetId={datasetId}
                  />
                  {onDelete && chatId && (
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          variant="ghost"
                          size="icon"
                          className={cn(
                            "h-6 w-6 opacity-0 transition-opacity group-hover:opacity-100",
                            "hover:bg-muted"
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
          )}
        </div>
      </div>
    );
  }
}

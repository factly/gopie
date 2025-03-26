import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { MoreVertical, Trash2, Play } from "lucide-react";
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
import { useEffect, useRef, useState } from "react";
import { TextShimmerWave } from "@/components/ui/text-shimmer-wave";
import { TTSButton } from "./tts-button";

interface MessageContent {
  type: "text" | "sql";
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
  content: string;
  role: "user" | "assistant";
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
  const { setResults, setIsOpen } = useSqlStore();
  const hasAutoExecuted = useRef(false);
  const [isExecuting, setIsExecuting] = useState(false);

  const handleRunQuery = async (query: string) => {
    setIsExecuting(true);
    try {
      const result = await executeSql.mutateAsync(query);
      setResults({
        data: result.data ?? [],
        total: result.data?.length ?? 0,
        query,
        chatId,
      });
      setIsOpen(true);
    } catch (error) {
      setResults({
        data: [],
        total: 0,
        error:
          error instanceof Error ? error.message : "Failed to execute query",
        query,
        chatId,
      });
      setIsOpen(true);
    } finally {
      setIsExecuting(false);
    }
  };

  // Auto-execute SQL queries from assistant only if it's the latest message
  useEffect(() => {
    if (
      !isLoading &&
      role === "assistant" &&
      isLatest &&
      !hasAutoExecuted.current
    ) {
      const parsed = parseMessageContent(content);
      if (parsed.type === "sql") {
        hasAutoExecuted.current = true;
        handleRunQuery(parsed.content);
      }
    }
  }, [content, isLoading, role, isLatest]);

  return (
    <div
      className={cn(
        "group flex w-full",
        role === "user" ? "justify-end" : "justify-start"
      )}
    >
      <div
        className={cn(
          "flex items-start gap-3 rounded-2xl px-4 py-3",
          "w-fit max-w-[90%] min-w-0",
          role === "user"
            ? "bg-primary text-primary-foreground shadow-sm"
            : "bg-muted shadow-sm border border-border/10"
        )}
        id={`message-${id}`}
        data-message-role={role}
        data-message-id={id}
      >
        <div className="flex-1 min-w-0">
          {isLoading ? (
            <div className="flex items-center gap-2">
              <TextShimmerWave
                className="text-sm [--base-color:#71717a] [--base-gradient-color:#a1a1aa] dark:[--base-color:#a1a1aa] dark:[--base-gradient-color:#e4e4e7]"
                duration={1}
                spread={1}
                zDistance={1}
                scaleDistance={1.1}
                rotateYDistance={20}
              >
                AI is thinking...
              </TextShimmerWave>
            </div>
          ) : (
            <>
              <div className="text-sm break-words">
                {(() => {
                  const parsed = parseMessageContent(content);
                  if (parsed.type === "sql") {
                    return (
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
                    );
                  }
                  return (
                    <div
                      className={cn(
                        "prose prose-sm max-w-none break-words [&>:first-child]:mt-0 [&>:last-child]:mb-0 leading-relaxed",
                        "[&_code]:whitespace-pre-wrap [&_code]:break-words [&_pre]:rounded-lg",
                        "[&_pre]:overflow-x-auto [&_pre]:whitespace-pre [&_pre]:shadow-sm",
                        role === "user"
                          ? "dark:prose-invert prose-p:text-primary-foreground prose-headings:text-primary-foreground prose-ul:text-primary-foreground prose-ol:text-primary-foreground prose-strong:text-primary-foreground [&_*]:text-primary-foreground"
                          : "dark:prose-invert [&_*]:!my-0.5 prose-p:leading-relaxed prose-li:leading-relaxed prose-ul:!pl-4 prose-ol:!pl-4 [&_blockquote]:!pl-4 [&_pre]:!p-3 [&_blockquote]:border-l-2 [&_blockquote]:border-border"
                      )}
                    >
                      <ReactMarkdown>{parsed.content}</ReactMarkdown>
                    </div>
                  );
                })()}
              </div>
              <div className="flex items-center gap-2 mt-2">
                <span
                  className={cn(
                    "text-[11px]",
                    role === "user"
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
                      text={content}
                      role={role}
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
                          role === "user"
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
}

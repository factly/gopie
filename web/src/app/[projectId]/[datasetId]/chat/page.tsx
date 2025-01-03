"use client";

import { use, useState, useEffect, useRef } from "react";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Send, User, Bot, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { SqlPreview } from "@/components/dataset/sql/sql-preview";
import { useDatasetSql } from "@/lib/mutations/dataset/sql";
import { ResultsTable } from "@/components/dataset/sql/results-table";
import { PlayIcon } from "lucide-react";
import { toast } from "sonner";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

interface BaseMessage {
  role: "user" | "assistant";
}

interface TextMessage extends BaseMessage {
  type: "text";
  content: string;
}

interface SqlMessage extends BaseMessage {
  type: "sql";
  query: string;
  results?: Record<string, unknown>[];
}

interface UserMessage {
  role: "user";
  content: string;
}

interface AssistantMessage {
  role: "assistant";
  responses: (TextMessage | SqlMessage)[];
}

type Message = UserMessage | AssistantMessage;

interface StreamingState {
  isStreaming: boolean;
  streamedContent: string;
}

const MessageCard = ({
  message,
  onRunQuery,
  isLatest,
}: {
  message: Message;
  onRunQuery: (query: string) => Promise<void>;
  isLatest: boolean;
}) => {
  const isUser = message.role === "user";
  const [runningQueries, setRunningQueries] = useState<{
    [key: string]: boolean;
  }>({});
  const [streamingStates, setStreamingStates] = useState<{
    [key: number]: StreamingState;
  }>({});

  useEffect(() => {
    if (!isLatest || isUser) return;
    const assistantMessage = message as AssistantMessage;

    assistantMessage.responses.forEach((response, idx) => {
      if (response.type === "text") {
        setStreamingStates((prev) => ({
          ...prev,
          [idx]: { isStreaming: true, streamedContent: "" },
        }));

        let currentContent = "";
        const words = response.content.split(" ");

        words.forEach((word, wordIdx) => {
          setTimeout(() => {
            currentContent += (wordIdx === 0 ? "" : " ") + word;
            setStreamingStates((prev) => ({
              ...prev,
              [idx]: {
                isStreaming: wordIdx < words.length - 1,
                streamedContent: currentContent,
              },
            }));
          }, wordIdx * 100);
        });
      }
    });
  }, [isLatest, isUser, message, message.responses, message.role]);

  const handleRunQuery = async (query: string) => {
    setRunningQueries((prev) => ({ ...prev, [query]: true }));
    try {
      await onRunQuery(query);
      toast.success("Query executed successfully");
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "Failed to execute query";
      toast.error(errorMessage);
    } finally {
      setRunningQueries((prev) => ({ ...prev, [query]: false }));
    }
  };

  return (
    <div
      className={cn(
        "flex gap-3 mb-4 transition-opacity duration-300",
        isUser && "flex-row-reverse",
        isLatest ? "opacity-100" : "opacity-90"
      )}
    >
      <Avatar
        className={cn(
          "h-8 w-8 ring-2",
          isUser ? "ring-primary/20" : "ring-muted"
        )}
      >
        <AvatarFallback className={isUser ? "bg-primary/10" : "bg-muted"}>
          {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
        </AvatarFallback>
      </Avatar>
      <div
        className={cn(
          "flex flex-col gap-2 max-w-[80%] w-full",
          isUser && "items-end"
        )}
      >
        {isUser ? (
          <Card className="p-3 shadow-sm bg-primary/10 hover:bg-primary/15 transition-colors">
            <p>{message.content}</p>
          </Card>
        ) : (
          (message as AssistantMessage).responses.map((response, idx) => (
            <div key={idx} className="w-full space-y-2">
              {response.type === "text" ? (
                <Card className="p-3 shadow-sm bg-muted hover:bg-muted/90 transition-colors">
                  <p>
                    {streamingStates[idx]?.streamedContent || response.content}
                    {streamingStates[idx]?.isStreaming && (
                      <span className="inline-block w-1.5 h-4 ml-1 bg-primary/50 animate-pulse" />
                    )}
                  </p>
                </Card>
              ) : (
                <div className="space-y-4">
                  <Accordion type="single" collapsible className="w-full">
                    <AccordionItem value="query" className="border rounded-lg">
                      <div className="flex items-center justify-between p-2">
                        <AccordionTrigger className="hover:no-underline flex-1 py-0">
                          <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <div className="h-2 w-2 rounded-full bg-primary/50" />
                            SQL Query
                          </div>
                        </AccordionTrigger>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleRunQuery(response.query)}
                          disabled={runningQueries[response.query]}
                          className={cn(
                            "gap-2 transition-all",
                            runningQueries[response.query]
                              ? "opacity-70"
                              : "hover:scale-105 hover:shadow-md"
                          )}
                        >
                          {runningQueries[response.query] ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <PlayIcon className="h-4 w-4" />
                          )}
                          {runningQueries[response.query]
                            ? "Running..."
                            : "Run Query"}
                        </Button>
                      </div>
                      <AccordionContent>
                        <div className="p-2">
                          <SqlPreview value={response.query} height="100px" />
                        </div>
                      </AccordionContent>
                    </AccordionItem>
                  </Accordion>
                  {response.results && (
                    <Card className="border shadow-sm">
                      <div className="p-3 border-b bg-muted/50">
                        <div className="text-sm font-medium">Query Results</div>
                      </div>
                      <div className="p-4">
                        <ResultsTable results={response.results} />
                      </div>
                    </Card>
                  )}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};

const getMockResponses = (datasetId: string): Message[] => [
  {
    role: "assistant",
    responses: [
      {
        type: "text",
        role: "assistant",
        content:
          "Let me analyze the distribution of Iris species measurements:",
      },
      {
        type: "sql",
        role: "assistant",
        query: `SELECT
  "Species",
  ROUND(AVG("SepalLengthCm"), 2) as "Avg Sepal Length",
  ROUND(AVG("PetalLengthCm"), 2) as "Avg Petal Length",
  COUNT(*) as "Count"
FROM "${datasetId}"
GROUP BY "Species"
ORDER BY "Count" DESC;`,
      },
    ],
  },
  {
    role: "assistant",
    responses: [
      {
        type: "text",
        role: "assistant",
        content:
          "Here's a comparison of petal sizes across different Iris species:",
      },
      {
        type: "sql",
        role: "assistant",
        query: `select "Species", avg("PetalLengthCm") as "average_petal_length", avg("PetalWidthCm") as "average_petal_width" from "gp_6nitjnH9KTGZ" group by "Species"`,
      },
    ],
  },
  {
    role: "assistant",
    responses: [
      {
        type: "text",
        role: "assistant",
        content:
          "Let's look at the relationship between sepal and petal measurements:",
      },
      {
        type: "sql",
        role: "assistant",
        query: `select "SepalLengthCm", "SepalWidthCm", "PetalLengthCm", "PetalWidthCm", "Species" from "gp_6nitjnH9KTGZ"`,
      },
    ],
  },
  {
    role: "assistant",
    responses: [
      {
        type: "text",
        role: "assistant",
        content:
          "Here are the Iris specimens with the largest overall dimensions:",
      },
      {
        type: "sql",
        role: "assistant",
        query: `select "Id", "SepalLengthCm", "SepalWidthCm", "PetalLengthCm", "PetalWidthCm", "Species" from "gp_6nitjnH9KTGZ" order by ("SepalLengthCm" + "SepalWidthCm" + "PetalLengthCm" + "PetalWidthCm") desc limit 10`,
      },
    ],
  },
];

export default function ChatPage({
  params,
}: {
  params: Promise<{ projectId: string; datasetId: string }>;
}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const { datasetId } = use(params);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const { mutateAsync: executeSql } = useDatasetSql();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const mockStreamingResponse = async (question: string) => {
    setIsLoading(true);
    await new Promise((resolve) => setTimeout(resolve, 500));

    const mockResponses = getMockResponses(datasetId);
    const randomResponse =
      mockResponses[Math.floor(Math.random() * mockResponses.length)];

    setMessages((prev) => [
      ...prev,
      { role: "user", content: question },
      randomResponse,
    ]);
    setIsLoading(false);
  };

  const handleRunQuery = async (query: string) => {
    try {
      const results = await executeSql(query);

      setMessages((prev) =>
        prev.map((msg) => {
          if (msg.role === "assistant") {
            return {
              ...msg,
              responses: msg.responses.map((response) => {
                if (response.type === "sql" && response.query === query) {
                  return { ...response, results };
                }
                return response;
              }),
            };
          }
          return msg;
        })
      );
    } catch (error) {
      throw error;
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const question = input.trim();
    setInput("");
    await mockStreamingResponse(question);
  };

  return (
    <div className="container mx-auto p-4 max-w-4xl h-[calc(100vh-4rem)]">
      <div className="flex flex-col h-full bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 rounded-lg border shadow-sm">
        <ScrollArea className="flex-1 p-4">
          <div className="space-y-4 mb-4">
            {messages.map((message, index) => (
              <MessageCard
                key={index}
                message={message}
                onRunQuery={handleRunQuery}
                isLatest={index === messages.length - 1}
              />
            ))}
            {isLoading && (
              <div className="flex gap-3">
                <Avatar className="h-8 w-8 ring-2 ring-muted">
                  <AvatarFallback className="bg-muted">
                    <Bot className="h-4 w-4" />
                  </AvatarFallback>
                </Avatar>
                <Card className="p-3 bg-muted w-fit">
                  <div className="flex gap-1">
                    <div
                      className="w-2 h-2 rounded-full bg-muted-foreground/30 animate-bounce"
                      style={{ animationDelay: "0ms" }}
                    />
                    <div
                      className="w-2 h-2 rounded-full bg-muted-foreground/30 animate-bounce"
                      style={{ animationDelay: "150ms" }}
                    />
                    <div
                      className="w-2 h-2 rounded-full bg-muted-foreground/30 animate-bounce"
                      style={{ animationDelay: "300ms" }}
                    />
                  </div>
                </Card>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </ScrollArea>

        <form onSubmit={handleSubmit} className="p-4 border-t bg-background/95">
          <div className="flex gap-2 items-center">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about your data..."
              disabled={isLoading}
              className="flex-1 bg-background"
            />
            <Button
              type="submit"
              disabled={isLoading}
              className="transition-transform hover:scale-105"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

"use client";

import { use, useState } from "react";
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

type Message =
  | {
      role: "user";
      content: string;
    }
  | {
      role: "assistant";
      responses: (TextMessage | SqlMessage)[];
    };

const MessageCard = ({
  message,
  onRunQuery,
}: {
  message: Message;
  onRunQuery: (query: string) => Promise<void>;
}) => {
  const isUser = message.role === "user";
  const [runningQueries, setRunningQueries] = useState<{
    [key: string]: boolean;
  }>({});

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
    <div className={cn("flex gap-3 mb-4", isUser && "flex-row-reverse")}>
      <Avatar className="h-8 w-8">
        <AvatarFallback className={isUser ? "bg-primary/10" : "bg-muted"}>
          {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
        </AvatarFallback>
      </Avatar>
      <div
        className={cn(
          "flex flex-col gap-2 max-w-[80%] w-full",
          isUser && "items-end",
        )}
      >
        {isUser ? (
          <Card className="p-3 shadow-sm bg-primary/10">
            <p>{message.content}</p>
          </Card>
        ) : (
          message.responses.map((response, idx) => (
            <div key={idx} className="w-full space-y-2">
              {response.type === "text" ? (
                <Card className="p-3 shadow-sm bg-muted">
                  <p>{response.content}</p>
                </Card>
              ) : (
                <Accordion type="single" collapsible className="w-full">
                  <AccordionItem value="query">
                    <div className="flex items-center justify-between">
                      <AccordionTrigger className="hover:no-underline flex-1">
                        <div className="text-sm text-muted-foreground">
                          SQL Query
                        </div>
                      </AccordionTrigger>
                      <Button
                        size="sm"
                        onClick={() => handleRunQuery(response.query)}
                        disabled={runningQueries[response.query]}
                        className={cn(
                          "gap-2 transition-all",
                          runningQueries[response.query]
                            ? "opacity-70"
                            : "hover:scale-105",
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
                      <div className="space-y-2">
                        <SqlPreview value={response.query} height="100px" />
                        {response.results && (
                          <Card className="p-4">
                            <ResultsTable results={response.results} />
                          </Card>
                        )}
                      </div>
                    </AccordionContent>
                  </AccordionItem>
                </Accordion>
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

  const { mutateAsync: executeSql } = useDatasetSql();

  const mockStreamingResponse = async (question: string) => {
    setIsLoading(true);
    await new Promise((resolve) => setTimeout(resolve, 1000));

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
        }),
      );
    } catch (error) {
      // Let the error bubble up to MessageCard's error handler
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
    <div className="container mx-auto p-4 max-w-4xl">
      <div className="flex flex-col h-full">
        <ScrollArea className="flex-1 pr-4">
          <div className="space-y-4 mb-4">
            {messages.map((message, index) => (
              <MessageCard
                key={index}
                message={message}
                onRunQuery={handleRunQuery}
              />
            ))}
            {isLoading && (
              <Card className="p-3 bg-muted w-fit">
                <p className="animate-pulse">Thinking...</p>
              </Card>
            )}
          </div>
        </ScrollArea>

        <form onSubmit={handleSubmit} className="flex gap-2 pt-4 border-t">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about your data..."
            disabled={isLoading}
            className="flex-1"
          />
          <Button type="submit" disabled={isLoading}>
            <Send className="h-4 w-4" />
          </Button>
        </form>
      </div>
    </div>
  );
}

"use client";

import React from "react";
import {
  useEffect,
  useRef,
  useState,
  useLayoutEffect,
  useCallback,
  useMemo,
} from "react";
import { useChatMessages } from "@/lib/queries/chat";
import { useDeleteChat, useChatWithAgent } from "@/lib/mutations/chat";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import { Table2, MessageSquarePlus, Trash2 } from "lucide-react";
import { ChatMessage } from "@/components/chat/message";
import { SqlResults } from "@/components/chat/sql-results";
import {
  ResizablePanel,
  ResizablePanelGroup,
  ResizableHandle,
} from "@/components/ui/resizable";
import { useSqlStore } from "@/lib/stores/sql-store";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useChatStore } from "@/lib/stores/chat-store";
import { VoiceMode } from "@/components/chat/voice-mode";
import { VoiceModeToggle } from "@/components/chat/voice-mode-toggle";
import { MentionInput } from "@/components/chat/mention-input";
import { ContextPicker, ContextItem } from "@/components/chat/context-picker";
import { useSearchParams, useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { useProjects } from "@/lib/queries/project/list-projects";
import { useDatasets } from "@/lib/queries/dataset/list-datasets";
import { fetchChats } from "@/lib/queries/chat/list-chats";
import { useQueryClient } from "@tanstack/react-query";
import { Chat, Project, Dataset } from "@/lib/api-client";
import { useSidebar } from "@/components/ui/sidebar";

interface StreamEvent {
  role: "intermediate" | "ai";
  content: string;
  datasets_used?: string[];
  generated_sql_query?: string;
}

interface CachedDatasetsData {
  results: Dataset[];
  total_count?: number;
}

interface DatasetsFetcherResponse {
  results: Dataset[];
  total_count?: number;
}

// Helper function to derive datasets and SQL from stream events
function deriveEnhancementsFromStream(streamEvents: StreamEvent[]): {
  datasets: string[];
  sql: string | null;
} {
  const allDatasets = new Set<string>();
  let latestSql: string | null = null;
  streamEvents.forEach((event) => {
    if (event.datasets_used) {
      event.datasets_used.forEach((dataset) => allDatasets.add(dataset));
    }
    if (event.generated_sql_query) {
      latestSql = event.generated_sql_query;
    }
  });
  return { datasets: Array.from(allDatasets), sql: latestSql };
}

const ChatHistoryList = React.memo(function ChatHistoryList({
  setActiveTab,
  setSelectedContexts,
  setLinkedDatasetId,
}: {
  setActiveTab: (tab: string) => void;
  setSelectedContexts: (contexts: ContextItem[]) => void;
  setLinkedDatasetId: (datasetId: string | null) => void;
}) {
  const { selectChatForDataset, selectedChatId } = useChatStore();
  const queryClient = useQueryClient();
  const [isLoading, setIsLoading] = useState(true);
  const [allChats, setAllChats] = useState<
    (Chat & {
      datasetId: string;
      datasetName: string;
      projectId: string;
      projectName: string;
    })[]
  >([]);

  const { data: projectsData } = useProjects({
    variables: { limit: 100 },
  });

  const deleteChat = useDeleteChat();

  useEffect(() => {
    async function fetchAllChats() {
      if (!projectsData?.results?.length) return;

      setIsLoading(true);
      const projects = projectsData.results;
      const allChatsArray: (Chat & {
        datasetId: string;
        datasetName: string;
        projectId: string;
        projectName: string;
      })[] = [];

      try {
        const datasetPromises = projects.map(async (project) => {
          try {
            const queryKey = [
              "datasets",
              { projectId: project.id, limit: 100 },
            ];
            const cachedData =
              queryClient.getQueryData<CachedDatasetsData>(queryKey);

            if (cachedData && cachedData.results) {
              return { projectId: project.id, data: cachedData };
            }

            const data = await queryClient.fetchQuery<DatasetsFetcherResponse>({
              queryKey,
              queryFn: async () => {
                const result = await useDatasets.fetcher({
                  projectId: project.id,
                  limit: 100,
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

        const datasetResults = await Promise.all(datasetPromises);

        for (const result of datasetResults) {
          const projectId = result.projectId;
          const data = result.data;
          const project = projects.find((p) => p.id === projectId);

          if (!project || !data || !Array.isArray(data.results)) {
            continue;
          }

          for (const dataset of data.results) {
            try {
              const chatsResponse = await fetchChats(
                { datasetId: dataset.id, limit: 50 },
                { pageParam: 1 }
              );

              if (chatsResponse.data.results) {
                const chatsWithContext = chatsResponse.data.results.map(
                  (chat: Chat) => ({
                    ...chat,
                    datasetId: dataset.id,
                    datasetName: dataset.alias,
                    projectId: project.id,
                    projectName: project.name,
                  })
                );
                allChatsArray.push(...chatsWithContext);
              }
            } catch (error) {
              console.error(
                `Failed to fetch chats for dataset ${dataset.id}:`,
                error
              );
            }
          }
        }

        allChatsArray.sort((a, b) => {
          return (
            new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
          );
        });

        setAllChats(allChatsArray);

        if (selectedChatId) {
          const selectedChat = allChatsArray.find(
            (chat) => chat.id === selectedChatId
          );
          if (selectedChat) {
            setSelectedContexts([
              {
                id: selectedChat.datasetId,
                type: "dataset",
                name: selectedChat.datasetName,
                projectId: selectedChat.projectId,
              },
            ]);
            setLinkedDatasetId(selectedChat.datasetId);
          }
        }
      } catch (error) {
        console.error("Error fetching all chats:", error);
        toast.error("Failed to load chat history");
      } finally {
        setIsLoading(false);
      }
    }

    fetchAllChats();
  }, [
    projectsData?.results,
    selectedChatId,
    setSelectedContexts,
    setLinkedDatasetId,
    queryClient,
  ]);

  const handleStartNewChat = () => {
    selectChatForDataset(null, null, null);
    setActiveTab("chat");
    setSelectedContexts([]);
    setLinkedDatasetId(null);
  };

  const handleDeleteChat = async (chatId: string) => {
    try {
      await deleteChat.mutateAsync(chatId);
      setAllChats((prev) => {
        const chatToDelete = prev.find((chat) => chat.id === chatId);
        if (chatToDelete && chatToDelete.datasetId === selectedChatId) {
          selectChatForDataset(null, null, null);
        }
        return prev.filter((chat) => chat.id !== chatId);
      });
      await queryClient.invalidateQueries({ queryKey: ["chats"] });
      if (selectedChatId === chatId) {
        selectChatForDataset(null, null, null);
        setSelectedContexts([]);
        setLinkedDatasetId(null);
        await queryClient.invalidateQueries({
          queryKey: ["chat-messages", { chatId }],
        });
      }
      toast.success("Chat deleted successfully");
    } catch {
      toast.error("Failed to delete chat");
    }
  };

  const handleSelectChat = (
    chatId: string,
    chatName: string,
    datasetId?: string,
    datasetName?: string,
    projectId?: string
  ) => {
    if (datasetId && datasetName && projectId) {
      setSelectedContexts([
        {
          id: datasetId,
          type: "dataset",
          name: datasetName,
          projectId: projectId,
        },
      ]);
      selectChatForDataset(datasetId, chatId, chatName || "New Chat");
      setLinkedDatasetId(datasetId);
    } else {
      setSelectedContexts([]);
      selectChatForDataset(null, chatId, chatName || "New Chat");
      setLinkedDatasetId(null);
    }
    setActiveTab("chat");
  };

  useEffect(() => {
    if (!selectedChatId) {
      setLinkedDatasetId(null);
    }
  }, [selectedChatId, setLinkedDatasetId]);

  if (isLoading) {
    return (
      <div className="p-4 space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-8 w-full" />
        ))}
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between p-2 mb-4">
        <Button
          variant="ghost"
          size="sm"
          onClick={handleStartNewChat}
          className="h-8 px-2 text-xs w-full justify-start"
        >
          <MessageSquarePlus className="h-4 w-4 mr-2" />
          New Chat
        </Button>
      </div>

      {allChats.length > 0 ? (
        <ScrollArea className="flex-1 pr-2">
          <div className="space-y-2">
            {allChats.map((chat) => {
              const date = new Date(chat.updated_at);
              const today = new Date();
              const yesterday = new Date(today);
              yesterday.setDate(yesterday.getDate() - 1);

              let dateString;
              if (date.toDateString() === today.toDateString()) {
                dateString = date.toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                });
              } else if (date.toDateString() === yesterday.toDateString()) {
                dateString = "Yesterday";
              } else if (date.getFullYear() === today.getFullYear()) {
                dateString = date.toLocaleDateString([], {
                  month: "short",
                  day: "numeric",
                });
              } else {
                dateString = date.toLocaleDateString([], {
                  year: "2-digit",
                  month: "short",
                  day: "numeric",
                });
              }

              return (
                <div
                  key={chat.id}
                  className={cn(
                    "group relative flex flex-col rounded-lg px-4 py-3 hover:bg-muted cursor-pointer transition-colors",
                    selectedChatId === chat.id &&
                      "bg-muted/80 border border-border/10"
                  )}
                  onClick={() =>
                    handleSelectChat(
                      chat.id,
                      chat.name || "New Chat",
                      chat.datasetId,
                      chat.datasetName,
                      chat.projectId
                    )
                  }
                >
                  <div className="flex items-center justify-between mb-1">
                    <div className="font-medium text-foreground/90 text-sm truncate max-w-[calc(100%-60px)]">
                      {chat.name || "New Chat"}
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs text-muted-foreground whitespace-nowrap flex items-center gap-1">
                        {dateString}
                      </span>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity ml-1"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteChat(chat.id);
                        }}
                      >
                        <Trash2 className="h-3.5 w-3.5 text-muted-foreground hover:text-destructive" />
                      </Button>
                    </div>
                  </div>
                  <div className="text-xs text-muted-foreground line-clamp-1">
                    {chat.projectName} / {chat.datasetName}
                  </div>
                </div>
              );
            })}
          </div>
        </ScrollArea>
      ) : (
        <div className="py-8 text-center text-sm text-muted-foreground">
          No chat history yet
        </div>
      )}
    </div>
  );
});
ChatHistoryList.displayName = "ChatHistoryList";

interface OptimisticMessage {
  id: string;
  content: string | StreamEvent[];
  role: "user" | "assistant" | "intermediate" | "ai";
  created_at: string;
  isLoading?: boolean;
  streamAborted?: boolean;
}

interface ChatInputProps {
  sendMessage: (message: string) => Promise<void>;
  isSending: boolean;
  isStreaming: boolean;
  stopMessageStream: () => void;
  selectedContexts: ContextItem[];
  onSelectContext: (context: ContextItem) => void;
  onRemoveContext: (contextId: string) => void;
  isVoiceModeActive: boolean;
  setIsVoiceModeActive: (active: boolean) => void;
  initialValue?: string;
  lockableContextIds?: string[];
  hasContext: boolean;
}

const ChatInput = React.memo(
  ({
    sendMessage,
    isSending,
    isStreaming,
    stopMessageStream,
    selectedContexts,
    onSelectContext,
    onRemoveContext,
    isVoiceModeActive,
    setIsVoiceModeActive,
    initialValue = "",
    lockableContextIds = [],
    hasContext,
  }: ChatInputProps) => {
    const [inputValue, setInputValue] = useState(initialValue);

    const handleSendMessage = useCallback(
      (e: React.FormEvent) => {
        e.preventDefault();
        if (!inputValue.trim() || isSending) return;
        sendMessage(inputValue);
        setInputValue("");
      },
      [inputValue, isSending, sendMessage]
    );

    const handleInputChange = useCallback((value: string) => {
      setInputValue(value);
    }, []);

    return (
      <div className="border-t bg-background/80 backdrop-blur-md p-2">
        <div className="flex items-start gap-2 max-w-5xl mx-auto">
          <ContextPicker
            selectedContexts={selectedContexts}
            onSelectContext={onSelectContext}
            onRemoveContext={onRemoveContext}
            triggerClassName="h-10 w-10 rounded-full bg-transparent text-foreground hover:bg-black/5 dark:hover:bg-white/5"
            lockableContextIds={lockableContextIds}
          />
          <MentionInput
            value={inputValue}
            onChange={handleInputChange}
            onSubmit={handleSendMessage}
            disabled={isSending}
            placeholder="Ask a question..."
            selectedContexts={selectedContexts}
            onSelectContext={onSelectContext}
            onRemoveContext={onRemoveContext}
            className="flex-1"
            showSendButton={true}
            isSending={isSending}
            isStreaming={isStreaming}
            stopMessageStream={stopMessageStream}
            lockableContextIds={lockableContextIds}
            hasContext={hasContext}
            actionButtons={
              <VoiceModeToggle
                isActive={isVoiceModeActive}
                onToggle={() => setIsVoiceModeActive(!isVoiceModeActive)}
              />
            }
          />
        </div>
      </div>
    );
  }
);
ChatInput.displayName = "ChatInput";

interface ChatViewProps {
  scrollRef: React.RefObject<HTMLDivElement | null>;
  handleScroll: (event: React.UIEvent<HTMLDivElement>) => void;
  isLoadingMessages: boolean;
  optimisticMessages: OptimisticMessage[];
  selectedChatId: string | null;
  allMessages: Array<{
    id: string;
    content: string;
    role: "user" | "assistant" | "intermediate" | "ai";
    created_at: string;
    chat_id?: string;
  }>;
  selectedContexts: ContextItem[];
  enhancementsForFinalizedMessages: Map<
    string,
    { datasets: string[]; sql: string | null }
  >;
}

const ChatView = React.memo(
  ({
    scrollRef,
    handleScroll,
    isLoadingMessages,
    optimisticMessages,
    selectedChatId,
    allMessages,
    selectedContexts,
    enhancementsForFinalizedMessages,
  }: ChatViewProps) => (
    <div className="flex-1 overflow-hidden relative">
      <div
        className={`z-10 absolute inset-x-0 top-0 h-8 bg-gradient-to-b from-background via-background to-transparent pointer-events-none ${
          allMessages.length > 0 || optimisticMessages.length > 0
            ? "opacity-100"
            : "opacity-0"
        } transition-opacity duration-300`}
      />
      <ScrollArea
        ref={scrollRef}
        className="h-full px-4"
        onScroll={handleScroll}
      >
        <div className="pb-32 pt-8">
          {isLoadingMessages &&
          !optimisticMessages.length &&
          allMessages.length === 0 ? (
            <div className="space-y-4">
              <Skeleton className="h-16 w-3/4" />
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-16 w-2/3" />
            </div>
          ) : !selectedChatId &&
            !optimisticMessages.length &&
            allMessages.length === 0 ? (
            <div className="flex flex-col items-center justify-center pt-12 text-center max-w-lg mx-auto space-y-6">
              <div className="text-lg font-medium">
                Start a new conversation
              </div>
              <p className="text-sm text-muted-foreground">
                Select contexts and ask questions about your data.
              </p>
            </div>
          ) : (
            <div className="space-y-6">
              {allMessages.map((message) => (
                <ChatMessage
                  key={message.id}
                  id={message.id}
                  content={message.content}
                  role={
                    message.role as "user" | "assistant" | "intermediate" | "ai"
                  }
                  createdAt={message.created_at}
                  chatId={selectedChatId || undefined}
                  isLatest={false}
                  datasetId={
                    selectedContexts.find((ctx) => ctx.type === "dataset")?.id
                  }
                  finalizedDatasets={
                    enhancementsForFinalizedMessages.get(message.id)?.datasets
                  }
                  finalizedSqlQuery={
                    enhancementsForFinalizedMessages.get(message.id)?.sql
                  }
                />
              ))}
              {optimisticMessages.map((message, index) => (
                <ChatMessage
                  key={message.id}
                  id={message.id}
                  content={message.content}
                  role={message.role}
                  createdAt={message.created_at}
                  isLoading={message.isLoading}
                  streamAborted={message.streamAborted}
                  chatId={selectedChatId || undefined}
                  isLatest={
                    index === optimisticMessages.length - 1 &&
                    message.role !== "user"
                  }
                  datasetId={
                    selectedContexts.find((ctx) => ctx.type === "dataset")?.id
                  }
                />
              ))}
            </div>
          )}
        </div>
      </ScrollArea>
      <div
        className={`z-10 absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-background to-transparent pointer-events-none`}
      />
    </div>
  )
);
ChatView.displayName = "ChatView";

function ChatPageClient() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const initialMessage = searchParams.get("initialMessage");
  const contextData = searchParams.get("contextData");
  const [activeTab, setActiveTab] = useState("chat");
  const queryClient = useQueryClient();

  const { setOpen, open: isSidebarOpen, isMobile } = useSidebar();
  const scrollRef = useRef<HTMLDivElement>(null);
  const { selectedChatId, selectedChatTitle, selectChatForDataset } =
    useChatStore();
  const [isSending, setIsSending] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);
  const [optimisticMessages, setOptimisticMessages] = useState<
    OptimisticMessage[]
  >([]);
  const { isOpen, setIsOpen, resetExecutedQueries } = useSqlStore();
  const [isVoiceModeActive, setIsVoiceModeActive] = useState(false);
  const [latestAssistantMessage, setLatestAssistantMessage] = useState<
    string | null
  >(null);

  const [selectedContexts, setSelectedContexts] = useState<ContextItem[]>([]);
  const [initialMessageSent, setInitialMessageSent] = useState(false);
  const [linkedDatasetId, setLinkedDatasetId] = useState<string | null>(null);

  // State to hold details from the most recently completed AI stream
  const [lastCompletedStreamDetails, setLastCompletedStreamDetails] = useState<{
    optimisticId: string;
    chatId: string;
    derivedDatasets: string[];
    derivedSql: string | null;
    // traceId?: string | null; // Future: if trace_id can be used for matching
  } | null>(null);

  // State to store enhancements for finalized messages, keyed by backend message ID
  const [
    enhancementsForFinalizedMessages,
    setEnhancementsForFinalizedMessages,
  ] = useState<Map<string, { datasets: string[]; sql: string | null }>>(
    new Map()
  );

  const chatWithAgent = useChatWithAgent();

  useEffect(() => {
    if (contextData) {
      try {
        const parsedContexts = JSON.parse(
          decodeURIComponent(contextData)
        ) as ContextItem[];
        if (Array.isArray(parsedContexts) && parsedContexts.length > 0) {
          setSelectedContexts(parsedContexts);
        }
      } catch (error) {
        console.error("Failed to parse context data:", error);
      }
    }
  }, [contextData]);

  const { data: projectsData } = useProjects({
    variables: { limit: 100 },
  });

  useEffect(() => {
    if (selectedChatId && projectsData?.results?.length) {
      const findChatDataset = async () => {
        try {
          const datasetPromises = projectsData.results.map(
            async (project: Project) => {
              try {
                const queryKey = [
                  "datasets",
                  { projectId: project.id, limit: 100 },
                ];
                const cachedData =
                  queryClient.getQueryData<CachedDatasetsData>(queryKey);
                if (cachedData && cachedData.results) {
                  return { project, data: cachedData };
                }
                const data =
                  await queryClient.fetchQuery<DatasetsFetcherResponse>({
                    queryKey,
                    queryFn: async () => {
                      const result = await useDatasets.fetcher({
                        projectId: project.id,
                        limit: 100,
                      });
                      return result;
                    },
                  });
                return { project, data };
              } catch (error) {
                console.error(
                  `Failed to fetch datasets for project ${project.id}:`,
                  error
                );
                return { project, data: { results: [] } };
              }
            }
          );

          const datasetResults = await Promise.all(datasetPromises);

          for (const result of datasetResults) {
            const project = result.project;
            const data = result.data;

            if (!data || !Array.isArray(data.results)) {
              continue;
            }

            for (const dataset of data.results) {
              try {
                const chatsResponse = await fetchChats(
                  { datasetId: dataset.id, limit: 50 },
                  { pageParam: 1 }
                );

                if (!chatsResponse?.data?.results?.length) continue;

                const chatFound = chatsResponse.data.results.find(
                  (chat: Chat) => chat.id === selectedChatId
                );

                if (chatFound) {
                  const datasetContext: ContextItem = {
                    id: dataset.id,
                    type: "dataset",
                    name: dataset.alias,
                    projectId: project.id,
                  };
                  setSelectedContexts([datasetContext]);
                  setLinkedDatasetId(dataset.id);
                  return;
                }
              } catch (error) {
                console.error(
                  `Failed to fetch chats for dataset ${dataset.id}:`,
                  error
                );
              }
            }
          }
        } catch (error) {
          console.error("Error finding dataset for chat:", error);
        }
      };
      findChatDataset();
    }
  }, [selectedChatId, projectsData, queryClient]);

  useEffect(() => {
    resetExecutedQueries();
  }, [selectedChatId, resetExecutedQueries]);

  useEffect(() => {
    setOpen(false);
  }, [setOpen]);

  const sendMessage = useCallback(
    async (message: string) => {
      if (!message.trim()) return;
      setIsSending(true);
      setIsStreaming(true);
      const optimisticId = Date.now().toString();
      const currentChatId = selectedChatId;

      // Create a new AbortController for this request
      abortControllerRef.current = new AbortController();
      const signal = abortControllerRef.current.signal;

      setOptimisticMessages((prev) => [
        ...prev,
        {
          id: `user-${optimisticId}`,
          content: message,
          role: "user",
          created_at: new Date().toISOString(),
        },
      ]);

      setOptimisticMessages((prev) => [
        ...prev,
        {
          id: `assistant-${optimisticId}`,
          content: [],
          role: "assistant",
          created_at: new Date().toISOString(),
          isLoading: true,
        },
      ]);

      try {
        const datasetIds = selectedContexts
          .filter((ctx) => ctx.type === "dataset")
          .map((ctx) => ctx.id);
        const projectIds = selectedContexts
          .filter((ctx) => ctx.type === "project")
          .map((ctx) => ctx.id);

        const response = await chatWithAgent.mutateAsync({
          chatId: currentChatId || undefined,
          datasetIds,
          projectIds,
          prompt: message,
          signal, // Pass the abort signal to the request
        });

        const reader = response.body?.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let newChatIdFromStream: string | null = null;
        let newChatNameFromStream: string | null = null;

        if (reader) {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop() || "";

            for (const line of lines) {
              if (line.startsWith("data: ")) {
                const jsonStr = line.substring(5).trim();
                if (jsonStr === "[DONE]") continue;
                if (!jsonStr) continue;

                try {
                  const data = JSON.parse(jsonStr);
                  let newContent = "";
                  let responseRole = data.role || "assistant";

                  if (
                    responseRole === "intermediate" ||
                    responseRole === "ai"
                  ) {
                    // Keep role
                  } else if (responseRole !== "user") {
                    responseRole = "assistant";
                  }

                  if (data.choices && data.choices[0]?.delta?.content) {
                    newContent = data.choices[0].delta.content;
                    if (data.choices[0].delta.role) {
                      responseRole = data.choices[0].delta.role;
                    }
                  } else if (data.content) {
                    newContent = data.content;
                  } else if (data.message?.content) {
                    newContent = data.message.content;
                    if (data.message.role) responseRole = data.message.role;
                  } else if (data.text) {
                    newContent = data.text;
                  } else if (typeof data === "string") {
                    newContent = data;
                  }

                  let eventRoleForStream: "intermediate" | "ai" | null = null;
                  if (responseRole === "intermediate") {
                    eventRoleForStream = "intermediate";
                  } else if (
                    responseRole === "ai" ||
                    responseRole === "assistant"
                  ) {
                    eventRoleForStream = "ai";
                  }

                  if (eventRoleForStream && newContent) {
                    const currentEvent: StreamEvent = {
                      role: eventRoleForStream,
                      content: newContent,
                      datasets_used: data.datasets_used,
                      generated_sql_query: data.generated_sql_query,
                    };
                    setOptimisticMessages((prev) =>
                      prev.map((msg) =>
                        msg.id === `assistant-${optimisticId}`
                          ? {
                              ...msg,
                              content: Array.isArray(msg.content)
                                ? [...msg.content, currentEvent]
                                : [currentEvent],
                            }
                          : msg
                      )
                    );
                  }

                  if (!currentChatId && data.chat_id && !newChatIdFromStream) {
                    newChatIdFromStream = data.chat_id;
                    newChatNameFromStream =
                      data.name || message.substring(0, 30) + "...";
                  }
                } catch (e) {
                  console.error(
                    "Error parsing SSE JSON:",
                    e,
                    "Raw line:",
                    jsonStr
                  );
                }
              } else if (line.trim()) {
                console.log("Received non-SSE line:", line);
              }
            }
          }
        }

        if (buffer.startsWith("data: ")) {
          const jsonStr = buffer.substring(5).trim();
          if (jsonStr && jsonStr !== "[DONE]") {
            try {
              const data = JSON.parse(jsonStr);
              let newContent = "";
              let responseRole = data.role || "assistant";
              if (data.choices && data.choices[0]?.delta?.content) {
                newContent = data.choices[0].delta.content;
                if (data.choices[0].delta.role)
                  responseRole = data.choices[0].delta.role;
              } else if (data.content) newContent = data.content;
              else if (data.message?.content) {
                newContent = data.message.content;
                if (data.message.role) responseRole = data.message.role;
              } else if (data.text) newContent = data.text;
              else if (typeof data === "string") newContent = data;

              let eventRoleForStream: "intermediate" | "ai" | null = null;
              if (responseRole === "intermediate")
                eventRoleForStream = "intermediate";
              else if (responseRole === "ai" || responseRole === "assistant")
                eventRoleForStream = "ai";

              if (eventRoleForStream && newContent) {
                const currentEvent: StreamEvent = {
                  role: eventRoleForStream,
                  content: newContent,
                  datasets_used: data.datasets_used,
                  generated_sql_query: data.generated_sql_query,
                };
                setOptimisticMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === `assistant-${optimisticId}`
                      ? {
                          ...msg,
                          content: Array.isArray(msg.content)
                            ? [...msg.content, currentEvent]
                            : [currentEvent],
                        }
                      : msg
                  )
                );
              }
            } catch (e) {
              console.error(
                "Error parsing remaining SSE JSON:",
                e,
                "Raw buffer:",
                jsonStr
              );
            }
          }
        }

        // Stream finished, capture derived datasets/SQL for the optimistic message
        setOptimisticMessages((prev) => {
          const currentOptMsg = prev.find(
            (msg) => msg.id === `assistant-${optimisticId}`
          );
          if (
            currentOptMsg &&
            Array.isArray(currentOptMsg.content) &&
            currentOptMsg.content.length > 0
          ) {
            const { datasets, sql } = deriveEnhancementsFromStream(
              currentOptMsg.content as StreamEvent[]
            );
            setLastCompletedStreamDetails({
              optimisticId: `assistant-${optimisticId}`,
              chatId: currentChatId || newChatIdFromStream || "", // Ensure chatId is string
              derivedDatasets: datasets,
              derivedSql: sql,
            });
          }
          return prev.map((msg) =>
            msg.id === `assistant-${optimisticId}`
              ? { ...msg, isLoading: false }
              : msg
          );
        });

        if (newChatIdFromStream && newChatNameFromStream) {
          const datasetIdForNewChat =
            selectedContexts.find((ctx) => ctx.type === "dataset")?.id || null;
          selectChatForDataset(
            datasetIdForNewChat,
            newChatIdFromStream,
            newChatNameFromStream
          );
        }

        await queryClient.invalidateQueries({
          queryKey: [
            "chat-messages",
            { chatId: currentChatId || newChatIdFromStream },
          ],
        });
        await queryClient.invalidateQueries({ queryKey: ["chats"] });

        setActiveTab("chat");
      } catch (error) {
        if (!(error instanceof Error && error.name === "AbortError")) {
          console.error("Error sending message:", error);
          toast.error("Failed to send message");
          setOptimisticMessages((prev) =>
            prev.filter((msg) => !msg.id.endsWith(optimisticId))
          );
        }
      } finally {
        setIsSending(false);
        setIsStreaming(false);
        abortControllerRef.current = null;
      }
    },
    [
      selectedChatId,
      selectedContexts,
      chatWithAgent,
      queryClient,
      selectChatForDataset,
      setActiveTab,
    ]
  );

  const stopMessageStream = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();

      setOptimisticMessages((prevMessages) =>
        prevMessages.map((msg) => {
          if (
            msg.isLoading &&
            (msg.role === "assistant" || msg.role === "ai") &&
            Array.isArray(msg.content)
          ) {
            return {
              ...msg,
              streamAborted: true,
            };
          }
          return msg;
        })
      );
      abortControllerRef.current = null;
      setIsStreaming(false);
    }
  }, []);

  useEffect(() => {
    if (initialMessage && !initialMessageSent && selectedContexts.length > 0) {
      // Send the message if any context is selected (not just datasets)
      sendMessage(initialMessage);
      setInitialMessageSent(true);
      const params = new URLSearchParams(searchParams.toString());
      params.delete("initialMessage");
      params.delete("contextData");
      router.replace(`/chat?${params.toString()}`);
    }
  }, [
    initialMessage,
    initialMessageSent,
    selectedContexts,
    sendMessage,
    router,
    searchParams,
  ]);

  const {
    data: messagesData,
    isLoading: isLoadingMessages,
    hasNextPage,
    fetchNextPage,
    isFetchingNextPage,
  } = useChatMessages({
    variables: {
      chatId: selectedChatId || "",
      limit: 20,
    },
    enabled: !!selectedChatId,
  });

  const allMessages = useMemo(() => {
    const messages =
      messagesData?.pages.flatMap((page) => page.data.results) ?? [];
    const processedMessages = messages.map((message) => ({
      ...message,
      role: ["user", "assistant", "intermediate", "ai"].includes(message.role)
        ? (message.role as "user" | "assistant" | "intermediate" | "ai")
        : "assistant",
    }));
    return processedMessages.sort((a, b) => {
      const timeA = new Date(a.created_at).getTime();
      const timeB = new Date(b.created_at).getTime();
      if (timeA === timeB) return a.role === "user" ? -1 : 1;
      return timeA - timeB;
    });
  }, [messagesData?.pages]);

  // Effect to associate completed stream data with a finalized message
  useEffect(() => {
    if (lastCompletedStreamDetails && allMessages.length > 0) {
      const { chatId, derivedDatasets, derivedSql } =
        lastCompletedStreamDetails;

      // Attempt to find the corresponding message in allMessages
      // Match if the stream's chatID is the currently selectedChatId
      if (selectedChatId === chatId) {
        const potentialMatches = allMessages.filter(
          (msg) =>
            (msg.role === "assistant" || msg.role === "ai") &&
            // msg.chat_id === chatId && // No longer needed, selectedChatId is the context
            !enhancementsForFinalizedMessages.has(msg.id)
        );

        if (potentialMatches.length > 0) {
          const matchedMessage = potentialMatches[potentialMatches.length - 1]; // Take the most recent
          setEnhancementsForFinalizedMessages((prev) =>
            new Map(prev).set(matchedMessage.id, {
              datasets: derivedDatasets,
              sql: derivedSql,
            })
          );
          setLastCompletedStreamDetails(null); // Consume the details
        }
      }
    }
  }, [
    allMessages,
    lastCompletedStreamDetails,
    enhancementsForFinalizedMessages,
    selectedChatId, // Added selectedChatId dependency
  ]);

  const showSqlButton = useMemo(() => {
    const checkContentForSql = (content: string | StreamEvent[]): boolean => {
      if (typeof content === "string") {
        return content.toLowerCase().includes("sql");
      } else if (Array.isArray(content)) {
        return content.some(
          (event) =>
            event.role === "ai" && event.content.toLowerCase().includes("sql")
        );
      }
      return false;
    };
    return (
      selectedChatId &&
      (allMessages.some((msg) => checkContentForSql(msg.content)) ||
        optimisticMessages.some(
          (msg) => msg.role !== "user" && checkContentForSql(msg.content)
        ))
    );
  }, [selectedChatId, allMessages, optimisticMessages]);

  useEffect(() => {
    let lastAssistantText: string | null = null;
    const assistantMessagesFromApi = allMessages.filter(
      (msg) => msg.role === "assistant" || msg.role === "ai"
    );
    if (assistantMessagesFromApi.length > 0) {
      const lastApiMsgContent =
        assistantMessagesFromApi[assistantMessagesFromApi.length - 1].content;
      if (typeof lastApiMsgContent === "string") {
        lastAssistantText = lastApiMsgContent;
      }
    }

    const optimisticAssistantMsg = optimisticMessages.find(
      (msg) => (msg.role === "assistant" || msg.role === "ai") && !msg.isLoading
    );
    if (
      optimisticAssistantMsg &&
      Array.isArray(optimisticAssistantMsg.content)
    ) {
      lastAssistantText = optimisticAssistantMsg.content
        .filter((e) => e.role === "ai")
        .map((e) => e.content)
        .join("");
    } else if (
      optimisticAssistantMsg &&
      typeof optimisticAssistantMsg.content === "string"
    ) {
      lastAssistantText = optimisticAssistantMsg.content;
    }

    setLatestAssistantMessage(lastAssistantText);
  }, [allMessages, optimisticMessages]);

  useEffect(() => {
    if (isSending) {
      setLatestAssistantMessage(null);
    }
  }, [isSending]);

  useEffect(() => {
    setOptimisticMessages([]);
  }, [selectedChatId]);

  useEffect(() => {
    if (!isSending && messagesData && optimisticMessages.length > 0) {
      setOptimisticMessages([]);
    }
  }, [messagesData, isSending, optimisticMessages.length]);

  useEffect(() => {
    if (selectedChatId) {
      setActiveTab("chat");
    }
  }, [selectedChatId, setActiveTab]);

  const handleScroll = useCallback(
    (event: React.UIEvent<HTMLDivElement>) => {
      const viewport = event.currentTarget;
      if (viewport.scrollTop < 100 && hasNextPage && !isFetchingNextPage) {
        fetchNextPage();
      }
    },
    [hasNextPage, isFetchingNextPage, fetchNextPage]
  );

  useLayoutEffect(() => {
    if (scrollRef.current) {
      const viewport = scrollRef.current.querySelector(
        "[data-radix-scroll-area-viewport]"
      );
      if (viewport) {
        const isNearBottom =
          viewport.scrollHeight - viewport.scrollTop - viewport.clientHeight <
          100;
        if (isNearBottom || !isFetchingNextPage) {
          requestAnimationFrame(() => {
            viewport.scrollTop = viewport.scrollHeight;
          });
        }
      }
    }
  }, [allMessages, optimisticMessages, isFetchingNextPage]);

  const handleSelectContext = useCallback((context: ContextItem) => {
    setSelectedContexts((prev) => [...prev, context]);
  }, []);

  const handleRemoveContext = useCallback((contextId: string) => {
    setSelectedContexts((prev) => prev.filter((c) => c.id !== contextId));
  }, []);

  const handleSendVoiceMessage = useCallback(
    async (message: string) => {
      await sendMessage(message);
    },
    [sendMessage]
  );

  const sqlPanelRef = useRef<HTMLDivElement>(null);
  const [sqlPanelWidth, setSqlPanelWidth] = useState(0);

  useEffect(() => {
    if (!isOpen) {
      setSqlPanelWidth(0);
      return;
    }
    const updateWidth = () => {
      if (sqlPanelRef.current) {
        setSqlPanelWidth(sqlPanelRef.current.clientWidth);
      }
    };
    updateWidth();
    const resizeObserver = new ResizeObserver(updateWidth);
    if (sqlPanelRef.current) {
      resizeObserver.observe(sqlPanelRef.current);
    }
    window.addEventListener("resize", updateWidth);
    return () => {
      resizeObserver.disconnect();
      window.removeEventListener("resize", updateWidth);
    };
  }, [isOpen, sqlPanelRef]);

  return (
    <main className="flex flex-col h-screen w-full pt-0 pb-0">
      <div className="flex w-full relative overflow-hidden max-h-screen">
        <ResizablePanelGroup direction="horizontal">
          <ResizablePanel minSize={30}>
            <Tabs
              value={activeTab}
              onValueChange={setActiveTab}
              className="w-full h-full flex flex-col"
            >
              <div className="flex w-full items-center border-b">
                <TabsList className="flex-1 h-10 grid grid-cols-2 rounded-none bg-background">
                  <TabsTrigger
                    value="chat"
                    className="data-[state=active]:border-b-2 data-[state=active]:border-primary data-[state=active]:bg-background data-[state=active]:shadow-none data-[state=active]:font-medium rounded-none px-4 py-2 text-sm transition-all"
                  >
                    {selectedChatTitle ? selectedChatTitle : "Chat"}
                  </TabsTrigger>
                  <TabsTrigger
                    value="history"
                    className="data-[state=active]:border-b-2 data-[state=active]:border-primary data-[state=active]:bg-background data-[state=active]:shadow-none data-[state=active]:font-medium rounded-none px-4 py-2 text-sm transition-all"
                  >
                    History
                  </TabsTrigger>
                </TabsList>
                <Button
                  variant="ghost"
                  size="sm"
                  className="mr-2"
                  onClick={() => {
                    selectChatForDataset(null, null, null);
                    setLinkedDatasetId(null);
                    setActiveTab("chat");
                  }}
                >
                  <MessageSquarePlus className="h-4 w-4 mr-1" />
                  New Chat
                </Button>
                {showSqlButton && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="mr-2"
                    onClick={() => setIsOpen(!isOpen)}
                  >
                    <Table2 className="h-4 w-4 mr-1" />
                    SQL Results
                  </Button>
                )}
              </div>

              <TabsContent
                value="chat"
                className="flex-1 overflow-hidden flex flex-col data-[state=inactive]:hidden p-0 border-none"
              >
                <div className="flex flex-col h-full">
                  <ChatView
                    scrollRef={scrollRef}
                    handleScroll={handleScroll}
                    isLoadingMessages={isLoadingMessages}
                    optimisticMessages={optimisticMessages}
                    selectedChatId={selectedChatId}
                    allMessages={allMessages}
                    selectedContexts={selectedContexts}
                    enhancementsForFinalizedMessages={
                      enhancementsForFinalizedMessages
                    }
                  />
                </div>
              </TabsContent>

              <TabsContent
                value="history"
                className="flex-1 overflow-hidden p-4 flex flex-col data-[state=inactive]:hidden border-none"
              >
                <ChatHistoryList
                  setActiveTab={setActiveTab}
                  setSelectedContexts={setSelectedContexts}
                  setLinkedDatasetId={setLinkedDatasetId}
                />
              </TabsContent>
            </Tabs>
          </ResizablePanel>
          {isOpen && (
            <>
              <ResizableHandle />
              <ResizablePanel defaultSize={70} minSize={30}>
                <div ref={sqlPanelRef} className="h-screen overflow-hidden">
                  <SqlResults />
                </div>
              </ResizablePanel>
            </>
          )}
        </ResizablePanelGroup>
      </div>
      {activeTab === "chat" && (
        <div
          className="fixed bottom-0 right-0 z-10"
          style={{
            left: isMobile ? 0 : isSidebarOpen ? "16rem" : "3rem",
            width: isOpen
              ? `calc(100% - ${
                  isMobile ? 0 : isSidebarOpen ? "16rem" : "3rem"
                } - ${sqlPanelWidth}px)`
              : `calc(100% - ${
                  isMobile ? 0 : isSidebarOpen ? "16rem" : "3rem"
                })`,
            transition: "left 0.2s ease-in-out, width 0.2s ease-in-out",
          }}
        >
          <ChatInput
            sendMessage={sendMessage}
            isSending={isSending}
            isStreaming={isStreaming}
            stopMessageStream={stopMessageStream}
            selectedContexts={selectedContexts}
            onSelectContext={handleSelectContext}
            onRemoveContext={handleRemoveContext}
            isVoiceModeActive={isVoiceModeActive}
            setIsVoiceModeActive={setIsVoiceModeActive}
            initialValue={initialMessage || ""}
            lockableContextIds={
              selectedChatId && linkedDatasetId ? [linkedDatasetId] : []
            }
            hasContext={selectedContexts.length > 0}
          />
        </div>
      )}
      {isVoiceModeActive && latestAssistantMessage && (
        <VoiceMode
          isActive={isVoiceModeActive}
          onToggle={() => setIsVoiceModeActive(!isVoiceModeActive)}
          onSendMessage={handleSendVoiceMessage}
          latestAssistantMessage={latestAssistantMessage}
          datasetId={
            selectedContexts.find((ctx) => ctx.type === "dataset")?.id || ""
          }
          isWaitingForResponse={isSending}
        />
      )}
    </main>
  );
}

export default ChatPageClient;

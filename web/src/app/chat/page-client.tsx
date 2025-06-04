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
import { useChat } from "@ai-sdk/react";
import { useDeleteChat } from "@/lib/mutations/chat";
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
import { UIMessage } from "ai";

interface CachedDatasetsData {
  results: Dataset[];
  total_count?: number;
}

interface DatasetsFetcherResponse {
  results: Dataset[];
  total_count?: number;
}

// Type for the messages from AI SDK
interface ChatMessage {
  id: string;
  role: string;
  content: string;
  createdAt?: string | Date;
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

interface ChatInputProps {
  onStop: () => void;
  isStreaming: boolean;
  selectedContexts: ContextItem[];
  onSelectContext: (context: ContextItem) => void;
  onRemoveContext: (contextId: string) => void;
  isVoiceModeActive: boolean;
  setIsVoiceModeActive: (active: boolean) => void;
  lockableContextIds?: string[];
  hasContext: boolean;
  input: string;
  handleInputChange: (value: string) => void;
  handleSubmit: (e: React.FormEvent) => void;
  isLoading: boolean;
}

const ChatInput = React.memo(
  ({
    onStop,
    isStreaming,
    selectedContexts,
    onSelectContext,
    onRemoveContext,
    isVoiceModeActive,
    setIsVoiceModeActive,
    lockableContextIds = [],
    hasContext,
    input,
    handleInputChange,
    handleSubmit,
    isLoading,
  }: ChatInputProps) => {
    // Handle input change from MentionInput
    const handleMentionInputChange = useCallback(
      (value: string) => {
        handleInputChange(value);
      },
      [handleInputChange]
    );

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
            value={input}
            onChange={handleMentionInputChange}
            onSubmit={handleSubmit}
            disabled={isLoading}
            placeholder="Ask a question..."
            selectedContexts={selectedContexts}
            onSelectContext={onSelectContext}
            onRemoveContext={onRemoveContext}
            className="flex-1"
            showSendButton={true}
            isSending={isLoading}
            isStreaming={isStreaming}
            stopMessageStream={onStop}
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
  isLoading: boolean;
  messages: UIMessage[];
  selectedContexts: ContextItem[];
  selectedChatId: string | null;
}

const ChatView = React.memo(
  ({
    scrollRef,
    handleScroll,
    isLoading,
    messages,
    selectedContexts,
    selectedChatId,
  }: ChatViewProps) => (
    <div className="flex-1 overflow-hidden relative">
      <div
        className={`z-10 absolute inset-x-0 top-0 h-8 bg-gradient-to-b from-background via-background to-transparent pointer-events-none ${
          messages.length > 0 ? "opacity-100" : "opacity-0"
        } transition-opacity duration-300`}
      />
      <ScrollArea
        ref={scrollRef}
        className="h-full px-4"
        onScroll={handleScroll}
      >
        <div className="pb-32 pt-8">
          {isLoading && messages.length === 0 ? (
            <div className="space-y-4">
              <Skeleton className="h-16 w-3/4" />
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-16 w-2/3" />
            </div>
          ) : !selectedChatId && messages.length === 0 ? (
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
              {messages.map((message) => (
                <ChatMessage
                  key={message.id}
                  id={message.id}
                  content={message.content}
                  message={message}
                  role={
                    message.role === "system"
                      ? "assistant"
                      : (message.role as
                          | "user"
                          | "assistant"
                          | "intermediate"
                          | "ai")
                  }
                  createdAt={
                    typeof message.createdAt === "string"
                      ? message.createdAt
                      : message.createdAt instanceof Date
                      ? message.createdAt.toISOString()
                      : new Date().toISOString()
                  }
                  chatId={selectedChatId || undefined}
                  isLatest={
                    message === messages[messages.length - 1] &&
                    message.role !== "user"
                  }
                  datasetId={
                    selectedContexts.find((ctx) => ctx.type === "dataset")?.id
                  }
                  isLoading={
                    message.role === "assistant" && message.content === ""
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

  const { open: isSidebarOpen, isMobile } = useSidebar();
  const scrollRef = useRef<HTMLDivElement>(null);
  const { selectedChatId, selectedChatTitle, selectChatForDataset } =
    useChatStore();
  const [isStreaming, setIsStreaming] = useState(false);
  const { isOpen, setIsOpen, resetExecutedQueries } = useSqlStore();
  const [isVoiceModeActive, setIsVoiceModeActive] = useState(false);
  const [latestAssistantMessage, setLatestAssistantMessage] = useState<
    string | null
  >(null);

  const [selectedContexts, setSelectedContexts] = useState<ContextItem[]>([]);
  const [initialMessageSent, setInitialMessageSent] = useState(false);
  const [linkedDatasetId, setLinkedDatasetId] = useState<string | null>(null);

  const sqlPanelRef = useRef<HTMLDivElement>(null);
  const [sqlPanelWidth, setSqlPanelWidth] = useState(0);

  // AI SDK Chat Implementation
  const {
    messages,
    input,
    handleInputChange: sdkHandleInputChange,
    handleSubmit: sdkHandleSubmit,
    isLoading,
    stop,
    error,
  } = useChat({
    api: "/api/chat",
    id: selectedChatId || undefined,
    body: {
      // Pass project_ids and dataset_ids from the selected contexts
      project_ids: selectedContexts
        .filter((ctx) => ctx.type === "project")
        .map((ctx) => ctx.id),
      dataset_ids: selectedContexts
        .filter((ctx) => ctx.type === "dataset")
        .map((ctx) => ctx.id),
    },
    onResponse: async (response) => {
      console.log(
        "Chat response received:",
        response.status,
        response.statusText
      );
    },
    onFinish: (message) => {
      console.log("Chat message finished:", message);
      // Update latest assistant message for voice mode
      if (message.role === "assistant") {
        setLatestAssistantMessage(message.content);
        setIsStreaming(false);
      }
    },
    onError: (err) => {
      console.error("Chat error:", err);
      toast.error("Error processing chat: " + (err.message || "Unknown error"));
    },
  });

  // Log messages for debugging
  useEffect(() => {
    console.log("Messages updated:", messages);
  }, [messages]);

  // Display any errors in the UI
  useEffect(() => {
    if (error) {
      console.error("Chat error state:", error);
      toast.error(`Error: ${error.message || "Unknown error"}`);
    }
  }, [error]);

  // Custom input handler that works with our MentionInput component
  const handleInputChange = useCallback(
    (value: string) => {
      // Create a synthetic change event
      const syntheticEvent = {
        target: { value },
        currentTarget: { value },
        preventDefault: () => {},
        stopPropagation: () => {},
      } as React.ChangeEvent<HTMLInputElement>;

      sdkHandleInputChange(syntheticEvent);
    },
    [sdkHandleInputChange]
  );

  // Custom submit handler that works with our MentionInput component
  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      sdkHandleSubmit(e as unknown as React.FormEvent);
    },
    [sdkHandleSubmit]
  );

  // Fetch projects for context selection
  const { data: projectsData } = useProjects({
    variables: { limit: 100 },
  });

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

  // Handle initial message from URL params
  useEffect(() => {
    if (initialMessage && !initialMessageSent && selectedContexts.length > 0) {
      handleInputChange(initialMessage);

      // Create a submit event for the form
      const submitEvent = new Event("submit", { bubbles: true });
      handleSubmit(submitEvent as unknown as React.FormEvent);

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
    handleInputChange,
    handleSubmit,
    router,
    searchParams,
  ]);

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const handleScroll = useCallback((event: React.UIEvent<HTMLDivElement>) => {
    // Handle scroll - can be used for loading more messages if needed
  }, []);

  useLayoutEffect(() => {
    if (scrollRef.current) {
      const viewport = scrollRef.current.querySelector(
        "[data-radix-scroll-area-viewport]"
      );
      if (viewport) {
        const isNearBottom =
          viewport.scrollHeight - viewport.scrollTop - viewport.clientHeight <
          100;
        if (isNearBottom) {
          requestAnimationFrame(() => {
            viewport.scrollTop = viewport.scrollHeight;
          });
        }
      }
    }
  }, [messages]);

  const handleSelectContext = useCallback((context: ContextItem) => {
    setSelectedContexts((prev) => [...prev, context]);
  }, []);

  const handleRemoveContext = useCallback((contextId: string) => {
    setSelectedContexts((prev) => prev.filter((c) => c.id !== contextId));
  }, []);

  const handleSendVoiceMessage = useCallback(
    async (message: string) => {
      handleInputChange(message);

      // Create a submit event for the form
      const submitEvent = new Event("submit", { bubbles: true });
      handleSubmit(submitEvent as unknown as React.FormEvent);
    },
    [handleInputChange, handleSubmit]
  );

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

  // Update streaming state based on isLoading
  useEffect(() => {
    setIsStreaming(isLoading);
  }, [isLoading]);

  // Handle stopping the stream
  const handleStop = useCallback(() => {
    stop();
    setIsStreaming(false);
  }, [stop]);

  // Compute whether to show SQL button
  const showSqlButton = useMemo(() => {
    return (
      selectedChatId &&
      messages.some(
        (msg) =>
          msg.role === "assistant" &&
          typeof msg.content === "string" &&
          msg.content.toLowerCase().includes("sql")
      )
    );
  }, [selectedChatId, messages]);

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
                    isLoading={isLoading}
                    messages={messages}
                    selectedContexts={selectedContexts}
                    selectedChatId={selectedChatId}
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
          }}
        >
          <ChatInput
            onStop={handleStop}
            isStreaming={isStreaming}
            selectedContexts={selectedContexts}
            onSelectContext={handleSelectContext}
            onRemoveContext={handleRemoveContext}
            isVoiceModeActive={isVoiceModeActive}
            setIsVoiceModeActive={setIsVoiceModeActive}
            lockableContextIds={
              selectedChatId && linkedDatasetId ? [linkedDatasetId] : []
            }
            hasContext={selectedContexts.length > 0}
            input={input}
            handleInputChange={handleInputChange}
            handleSubmit={handleSubmit}
            isLoading={isLoading}
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
          isWaitingForResponse={isLoading}
        />
      )}
    </main>
  );
}

export default ChatPageClient;

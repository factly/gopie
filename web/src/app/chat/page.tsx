"use client";

import {
  useEffect,
  useRef,
  useState,
  useLayoutEffect,
  useCallback,
  useMemo,
} from "react";
import { useChatMessages } from "@/lib/queries/chat";
import { useCreateChat } from "@/lib/mutations/chat";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import { Table2, MessageSquarePlus, Trash2 } from "lucide-react";
import { useSidebar } from "@/components/ui/sidebar";
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
import { useDeleteChat } from "@/lib/mutations/chat";
import { useQueryClient } from "@tanstack/react-query";
import { Chat } from "@/lib/api-client";
import React from "react";

// Chat history component now used in the History tab
const ChatHistoryList = React.memo(function ChatHistoryList({
  setActiveTab,
  setSelectedContexts,
  setLinkedDatasetId,
}: {
  setActiveTab: (tab: string) => void;
  setSelectedContexts: (contexts: ContextItem[]) => void;
  setLinkedDatasetId: (datasetId: string | null) => void;
}) {
  const { selectedChatId, selectChat } = useChatStore();
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

  // Fetch all projects
  const { data: projectsData } = useProjects({
    variables: { limit: 100 },
  });

  // Delete chat mutation
  const deleteChat = useDeleteChat();

  // Fetch all chats across all datasets and projects
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
        // For each project, fetch its datasets using the React Query client directly
        const datasetPromises = projects.map(async (project) => {
          try {
            const queryKey = [
              "datasets",
              { projectId: project.id, limit: 100 },
            ];
            // Check cache first
            const cachedData = queryClient.getQueryData(queryKey);

            // Safely handle cached data with type assertion
            if (
              cachedData &&
              typeof cachedData === "object" &&
              "results" in cachedData
            ) {
              return { projectId: project.id, data: cachedData };
            }

            // If not in cache, fetch it
            const data = await queryClient.fetchQuery({
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

        // For each dataset, fetch its chats
        for (const result of datasetResults) {
          const projectId = result.projectId;
          const data = result.data;
          const project = projects.find((p) => p.id === projectId);

          // Properly type guard for data.results
          if (
            !project ||
            !data ||
            typeof data !== "object" ||
            !("results" in data) ||
            !Array.isArray(data.results)
          ) {
            continue;
          }

          for (const dataset of data.results) {
            try {
              const chatsResponse = await fetchChats(
                { datasetId: dataset.id, limit: 50 },
                { pageParam: 1 }
              );

              if (chatsResponse.data.results) {
                // Add project and dataset info to each chat
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

        // Sort chats by updated_at date (newest first)
        allChatsArray.sort((a, b) => {
          return (
            new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
          );
        });

        setAllChats(allChatsArray);

        // If a chat is already selected, find and set its dataset context
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
    selectChat(null, null);
    setLinkedDatasetId(null);
    setActiveTab("chat");
  };

  const handleDeleteChat = async (chatId: string) => {
    try {
      await deleteChat.mutateAsync(chatId);
      if (chatId === selectedChatId) {
        selectChat(null, null);
      }

      // Update the local state
      setAllChats((prev) => prev.filter((chat) => chat.id !== chatId));

      // Invalidate queries to refresh data
      await queryClient.invalidateQueries({ queryKey: ["chats"] });

      toast.success("Chat deleted successfully");
    } catch {
      toast.error("Failed to delete chat");
    }
  };

  const handleSelectChat = (
    chatId: string,
    chatName: string,
    datasetId?: string,
    datasetName?: string
  ) => {
    selectChat(chatId, chatName || "New Chat");

    // Auto-select dataset context for the selected chat
    if (datasetId && datasetName) {
      // Update context for this component
      setSelectedContexts([
        {
          id: datasetId,
          type: "dataset",
          name: datasetName,
        },
      ]);
      setLinkedDatasetId(datasetId);
    }

    setActiveTab("chat"); // Switch to chat tab when a chat is selected
  };

  // Clear linked dataset ID when no chat is selected
  useEffect(() => {
    if (!selectedChatId) {
      setLinkedDatasetId(null);
    }
  }, [selectedChatId]);

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
                      chat.datasetName
                    )
                  }
                >
                  <div className="flex items-center justify-between mb-1">
                    <div className="font-medium text-foreground/90 text-sm truncate max-w-[80%]">
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

interface OptimisticMessage {
  id: string;
  content: string;
  role: "user" | "assistant";
  created_at: string;
  isLoading?: boolean;
}

// Extract ChatInput as a separate component outside the main ChatPage
interface ChatInputProps {
  sendMessage: (message: string) => Promise<void>;
  isSending: boolean;
  selectedContexts: ContextItem[];
  onSelectContext: (context: ContextItem) => void;
  onRemoveContext: (contextId: string) => void;
  isVoiceModeActive: boolean;
  setIsVoiceModeActive: (active: boolean) => void;
  initialValue?: string;
  lockableContextIds?: string[];
}

const ChatInput = React.memo(
  ({
    sendMessage,
    isSending,
    selectedContexts,
    onSelectContext,
    onRemoveContext,
    isVoiceModeActive,
    setIsVoiceModeActive,
    initialValue = "",
    lockableContextIds = [],
  }: ChatInputProps) => {
    const [inputValue, setInputValue] = useState(initialValue);

    // Use callbacks to prevent recreation on every render
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
            lockableContextIds={lockableContextIds}
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

// Memoize ChatView component to prevent unnecessary rerenders
interface ChatViewProps {
  scrollRef: React.RefObject<HTMLDivElement | null>;
  handleScroll: (event: React.UIEvent<HTMLDivElement>) => void;
  isLoadingMessages: boolean;
  optimisticMessages: OptimisticMessage[];
  selectedChatId: string | null;
  allMessages: Array<{
    id: string;
    content: string;
    role: string;
    created_at: string;
  }>;
  selectedContexts: ContextItem[];
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
  }: ChatViewProps) => (
    <div className="flex-1 overflow-hidden relative">
      <div
        className={`z-10 absolute inset-x-0 top-0 h-8 bg-gradient-to-b from-background via-background to-transparent pointer-events-none ${
          allMessages.length > 0 ? "opacity-100" : "opacity-0"
        } transition-opacity duration-300`}
      />
      <ScrollArea
        ref={scrollRef}
        className="h-full px-4"
        onScroll={handleScroll}
      >
        <div className="pb-32 pt-8">
          {isLoadingMessages && !optimisticMessages.length ? (
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
                  role={message.role as "user" | "assistant"}
                  createdAt={message.created_at}
                  chatId={selectedChatId || undefined}
                  isLatest={
                    message.id === allMessages[allMessages.length - 1]?.id
                  }
                  datasetId={
                    selectedContexts.find((ctx) => ctx.type === "dataset")?.id
                  }
                />
              ))}
              {optimisticMessages.map((message) => (
                <ChatMessage
                  key={message.id}
                  id={message.id}
                  content={message.content}
                  role={message.role}
                  createdAt={message.created_at}
                  isLoading={message.isLoading}
                  chatId={selectedChatId || undefined}
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

export default function ChatPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const initialMessage = searchParams.get("initialMessage");
  const contextData = searchParams.get("contextData");
  const [activeTab, setActiveTab] = useState("chat");
  const queryClient = useQueryClient();

  const { setOpen } = useSidebar();
  const scrollRef = useRef<HTMLDivElement>(null);
  const { selectedChatId, selectedChatTitle, selectChat } = useChatStore();
  const [isSending, setIsSending] = useState(false);
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

  // Set initial contexts from URL parameters
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

  // Fetch all projects for dataset context lookup
  const { data: projectsData } = useProjects({
    variables: { limit: 100 },
  });

  // Set dataset context when a chat is selected
  useEffect(() => {
    if (selectedChatId && projectsData?.results?.length) {
      // Find the chat in the history to get its dataset information
      const findChatDataset = async () => {
        try {
          // For each project, get datasets using the queryClient
          const datasetPromises = projectsData.results.map(async (project) => {
            try {
              const queryKey = [
                "datasets",
                { projectId: project.id, limit: 100 },
              ];
              // Check cache first
              const cachedData = queryClient.getQueryData(queryKey);

              // Safely handle cached data with type assertion
              if (
                cachedData &&
                typeof cachedData === "object" &&
                "results" in cachedData
              ) {
                return { project, data: cachedData };
              }

              // If not in cache, fetch it
              const data = await queryClient.fetchQuery({
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
          });

          const datasetResults = await Promise.all(datasetPromises);

          // For each dataset, check if our chat belongs to it
          for (const result of datasetResults) {
            const project = result.project;
            const data = result.data;

            // Properly type guard for data.results
            if (
              !data ||
              typeof data !== "object" ||
              !("results" in data) ||
              !Array.isArray(data.results)
            ) {
              continue;
            }

            for (const dataset of data.results) {
              try {
                const chatsResponse = await fetchChats(
                  { datasetId: dataset.id, limit: 50 },
                  { pageParam: 1 }
                );

                if (!chatsResponse?.data?.results?.length) continue;

                // If we find our chat, set the dataset context and exit
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

                  // Set this as the only context, replacing any existing ones
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

  // Reset SQL executions when chat changes
  useEffect(() => {
    resetExecutedQueries();
  }, [selectedChatId, resetExecutedQueries]);

  // Close sidebar only on initial mount
  useEffect(() => {
    setOpen(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Handle initial message if provided in URL params
  useEffect(() => {
    if (initialMessage && !initialMessageSent && selectedContexts.length > 0) {
      const datasetContext = selectedContexts.find(
        (context) => context.type === "dataset"
      );
      if (datasetContext) {
        sendMessage(initialMessage);
        setInitialMessageSent(true);

        // Clean up URL
        const params = new URLSearchParams(searchParams.toString());
        params.delete("initialMessage");
        params.delete("contextData");
        router.replace(`/chat?${params.toString()}`);
      }
    }
  }, [
    initialMessage,
    initialMessageSent,
    selectedContexts,
    router,
    searchParams,
  ]);

  // Log when linked dataset changes
  useEffect(() => {
    if (linkedDatasetId) {
      console.log(`Dataset linked to current chat: ${linkedDatasetId}`);
    }
  }, [linkedDatasetId]);

  // Queries
  const {
    data: messagesData,
    isLoading: isLoadingMessages,
    refetch: refetchMessages,
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

  // Combine all pages of messages
  const allMessages = useMemo(() => {
    const messages =
      messagesData?.pages.flatMap((page) => page.data.results) ?? [];
    return messages.sort((a, b) => {
      const timeA = new Date(a.created_at).getTime();
      const timeB = new Date(b.created_at).getTime();
      if (timeA === timeB) {
        // If timestamps are equal, show user message first
        return a.role === "user" ? -1 : 1;
      }
      return timeA - timeB;
    });
  }, [messagesData?.pages]);

  // Flag to show SQL button - only if we have messages containing SQL
  const showSqlButton = useMemo(() => {
    return (
      selectedChatId &&
      allMessages.some((msg) => msg.content.toLowerCase().includes("sql"))
    );
  }, [selectedChatId, allMessages]);

  // Track latest assistant message for voice mode
  useEffect(() => {
    if (allMessages.length > 0) {
      const assistantMessages = allMessages.filter(
        (msg) => msg.role === "assistant"
      );
      if (assistantMessages.length > 0) {
        const lastAssistantMessage =
          assistantMessages[assistantMessages.length - 1];
        setLatestAssistantMessage(lastAssistantMessage.content);
      }
    }
  }, [allMessages]);

  // Also check optimistic messages to detect when an assistant response is being received
  useEffect(() => {
    const assistantOptimisticMessages = optimisticMessages.filter(
      (msg) => msg.role === "assistant" && !msg.isLoading
    );

    if (assistantOptimisticMessages.length > 0) {
      const lastOptimisticAssistant =
        assistantOptimisticMessages[assistantOptimisticMessages.length - 1];
      if (lastOptimisticAssistant.content) {
        setLatestAssistantMessage(lastOptimisticAssistant.content);
      }
    }
  }, [optimisticMessages]);

  // Clear latest assistant message when sending a new message
  useEffect(() => {
    if (isSending) {
      setLatestAssistantMessage(null);
    }
  }, [isSending]);

  // Clear optimistic messages automatically when changing chats
  useEffect(() => {
    setOptimisticMessages([]);
  }, [selectedChatId]);

  // Add an effect to clear optimistic messages when the real messages arrive
  useEffect(() => {
    if (!isSending && messagesData && optimisticMessages.length > 0) {
      // If we have messages data and we're not sending anymore,
      // clear any optimistic messages that might be stuck
      setOptimisticMessages([]);
    }
  }, [messagesData, isSending, optimisticMessages.length]);

  // Mutations
  const createChat = useCreateChat();

  // Automatically switch to chat tab when a chat is selected
  useEffect(() => {
    if (selectedChatId) {
      setActiveTab("chat");
    }
  }, [selectedChatId]);

  // Handle scroll to load more
  const handleScroll = useCallback(
    (event: React.UIEvent<HTMLDivElement>) => {
      const viewport = event.currentTarget;
      const isNearTop = viewport.scrollTop < 100;

      if (isNearTop && hasNextPage && !isFetchingNextPage) {
        fetchNextPage();
      }
    },
    [hasNextPage, isFetchingNextPage, fetchNextPage]
  );

  // Scroll to bottom whenever new messages are added (but not when loading previous messages)
  useLayoutEffect(() => {
    if (scrollRef.current) {
      const viewport = scrollRef.current.querySelector(
        "[data-radix-scroll-area-viewport]"
      );
      if (viewport) {
        // Only auto-scroll if we're already near the bottom
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

  // Modified to use useCallback to minimize rerenders when dependencies don't change
  const sendMessage = useCallback(
    async (message: string) => {
      if (!message.trim() || isSending) return;

      // Require at least one dataset in the context
      const datasetContext = selectedContexts.find(
        (ctx: ContextItem) => ctx.type === "dataset"
      );
      if (!datasetContext) {
        toast.error(
          "Please select at least one dataset in the context before sending a message"
        );
        return;
      }

      setIsSending(true);
      const optimisticId = Date.now().toString();
      const chatId = selectedChatId;

      try {
        // Add optimistic user message
        setOptimisticMessages((prev) => [
          ...prev,
          {
            id: `user-${optimisticId}`,
            content: message,
            role: "user",
            created_at: new Date().toISOString(),
          },
        ]);

        // Add optimistic loading message for assistant
        setOptimisticMessages((prev) => [
          ...prev,
          {
            id: `assistant-${optimisticId}`,
            content: "",
            role: "assistant",
            created_at: new Date().toISOString(),
            isLoading: true,
          },
        ]);

        // For now, we'll use the first dataset ID from the context
        // This is a temporary solution until the backend is updated
        const firstDatasetId = selectedContexts.find(
          (ctx) => ctx.type === "dataset"
        )?.id;

        // Need to maintain backward compatibility with the API
        // until the backend is updated to support the new context format
        const result = await createChat.mutateAsync({
          chatId: chatId || undefined,
          datasetId: firstDatasetId, // Will be removed later when backend is updated
          messages: [{ role: "user", content: message }],
        });

        await queryClient.invalidateQueries({
          queryKey: ["chat-messages"],
        });

        if (result.data.id) {
          // If new chat was created, select it
          if (!chatId) {
            selectChat(
              result.data.id,
              result.data.name ||
                result.data.messages[0]?.content.substring(0, 30) + "..."
            );
          }

          // First try to force refetch to get the real messages
          await refetchMessages();

          // Give the UI a moment to process the real messages, then remove optimistic ones
          setTimeout(() => {
            if (!isSending) {
              setOptimisticMessages([]);
            }
          }, 150);

          // Switch to chat tab when a new chat is created or a message is sent
          setActiveTab("chat");
        }
      } catch (error) {
        console.error("Error sending message:", error);
        toast.error("Failed to send message");

        // Remove optimistic messages on error
        setOptimisticMessages((prev) =>
          prev.filter((msg) => !msg.id.includes(optimisticId.toString()))
        );
      } finally {
        setIsSending(false);
      }
      // eslint-disable-next-line react-hooks/exhaustive-deps
    },
    [
      selectedChatId,
      createChat.mutateAsync,
      refetchMessages,
      selectChat,
      setActiveTab,
    ]
  );

  const handleSelectContext = useCallback((context: ContextItem) => {
    setSelectedContexts((prev) => [...prev, context]);
  }, []);

  const handleRemoveContext = useCallback((contextId: string) => {
    setSelectedContexts((prev) => prev.filter((c) => c.id !== contextId));
  }, []);

  // Function to handle voice message sending
  const handleSendVoiceMessage = useCallback(
    async (message: string) => {
      await sendMessage(message);
    },
    [sendMessage]
  );

  // Add a ref for the SQL panel
  const sqlPanelRef = useRef<HTMLDivElement>(null);
  const [sqlPanelWidth, setSqlPanelWidth] = useState(0);

  // Update the SQL panel width when the panel is resized
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

    // Initial width
    updateWidth();

    // Add resize observer to detect panel width changes
    const resizeObserver = new ResizeObserver(updateWidth);
    if (sqlPanelRef.current) {
      resizeObserver.observe(sqlPanelRef.current);
    }

    // Also update on window resize
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
          <ResizablePanel defaultSize={isOpen ? 60 : 100} minSize={50}>
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
                    selectChat(null, null);
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
              <ResizablePanel defaultSize={40} minSize={30} maxSize={60}>
                <div ref={sqlPanelRef} className="h-screen overflow-hidden">
                  <SqlResults />
                </div>
              </ResizablePanel>
            </>
          )}
        </ResizablePanelGroup>
      </div>
      {/* Fixed chat input at the bottom */}
      {activeTab === "chat" && (
        <div className="fixed bottom-0 left-0 right-0 z-10 w-full">
          <div
            style={{
              width: isOpen ? `calc(100% - ${sqlPanelWidth}px)` : "100%",
              transition: "width 0.2s ease-in-out",
            }}
          >
            <ChatInput
              sendMessage={sendMessage}
              isSending={isSending}
              selectedContexts={selectedContexts}
              onSelectContext={handleSelectContext}
              onRemoveContext={handleRemoveContext}
              isVoiceModeActive={isVoiceModeActive}
              setIsVoiceModeActive={setIsVoiceModeActive}
              initialValue={initialMessage || ""}
              lockableContextIds={
                selectedChatId && linkedDatasetId ? [linkedDatasetId] : []
              }
            />
          </div>
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

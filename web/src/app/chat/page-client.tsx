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
import { useChats } from "@/lib/queries/chat/list-chats";
import { useChatMessages } from "@/lib/queries/chat/get-messages";
import { useChatDetails } from "@/lib/queries/chat/get-chat";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import { Table2, MessageSquarePlus, Trash2 } from "lucide-react";
import { ChatMessage } from "@/components/chat/message";
import { ResultsPanel } from "@/components/chat/results-panel";
import {
  ResizablePanel,
  ResizablePanelGroup,
  ResizableHandle,
} from "@/components/ui/resizable";
import { useSqlStore } from "@/lib/stores/sql-store";
import { useVisualizationStore } from "@/lib/stores/visualization-store";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useChatStore } from "@/lib/stores/chat-store";
import { VoiceMode } from "@/components/chat/voice-mode";
import { VoiceModeToggle } from "@/components/chat/voice-mode-toggle";
import { MentionInput } from "@/components/chat/mention-input";
import { ContextPicker, ContextItem } from "@/components/chat/context-picker";
import { useSearchParams, useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { useQueryClient } from "@tanstack/react-query";
import { useSidebar } from "@/components/ui/sidebar";
import { UIMessage } from "ai";

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
  searchParams,
  router,
}: {
  setActiveTab: (tab: string) => void;
  setSelectedContexts: (contexts: ContextItem[]) => void;
  setLinkedDatasetId: (datasetId: string | null) => void;
  searchParams: URLSearchParams;
  router: ReturnType<typeof useRouter>;
}) {
  const { selectChatForDataset, selectedChatId } = useChatStore();
  const queryClient = useQueryClient();

  const deleteChat = useDeleteChat();

  // Use the infinite query hook
  const {
    data: chatsData,
    isLoading,
    error,
  } = useChats({
    variables: { userID: "1", limit: 100 }, // Using hardcoded user ID "1" as in the API route
  });

  // Flatten all pages, filter out null values, and sort chats by updated_at descending
  const allChats = useMemo(() => {
    if (!chatsData?.pages) return [];

    const allResults = chatsData.pages.flatMap(
      (page) => page.data.results || []
    );

    // Filter out null values and ensure we have valid chat objects
    const validChats = allResults.filter(
      (chat) =>
        chat !== null &&
        chat !== undefined &&
        typeof chat === "object" &&
        "updated_at" in chat
    );

    return validChats.sort((a, b) => {
      return (
        new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      );
    });
  }, [chatsData]);

  // Show error toast if there's an error
  useEffect(() => {
    if (error) {
      console.error("Error fetching user chats:", error);
      toast.error("Failed to load chat history");
    }
  }, [error]);

  const handleStartNewChat = () => {
    selectChatForDataset(null, null, null);
    setActiveTab("chat");
    setSelectedContexts([]);
    setLinkedDatasetId(null);

    // Clear URL parameters when starting a new chat
    const params = new URLSearchParams(searchParams.toString());
    params.delete("chatId");
    params.delete("initialMessage");
    params.delete("contextData");
    router.replace(`/chat?${params.toString()}`);
  };

  const handleDeleteChat = async (chatId: string) => {
    try {
      await deleteChat.mutateAsync({
        chatId,
        userId: "1", // Using hardcoded user ID "1" as in the API route
      });

      // Invalidate the chats query to refetch data
      await queryClient.invalidateQueries({ queryKey: ["chats"] });

      // If the deleted chat was selected, clear the selection
      const chatToDelete = allChats.find((chat) => chat.id === chatId);
      if (chatToDelete && chatToDelete.id === selectedChatId) {
        selectChatForDataset(null, null, null);
      }

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
                      chat.title || "New Chat"
                      // Note: Dataset and project info might need to be retrieved
                      // from the chat messages or stored in the chat object
                    )
                  }
                >
                  <div className="flex items-center justify-between mb-1">
                    <div className="font-medium text-foreground/90 text-sm truncate max-w-[calc(100%-60px)]">
                      {chat.title || "New Chat"}
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
                  {/* Note: Since the API doesn't return dataset/project info with chats,
                      we might need to fetch this information separately or store it differently */}
                  <div className="text-xs text-muted-foreground line-clamp-1">
                    Chat History
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
  isLoadingChatMessages?: boolean;
  hasNextPage?: boolean;
  fetchNextPage?: () => void;
  isFetchingNextPage?: boolean;
}

const ChatView = React.memo(
  ({
    scrollRef,
    handleScroll,
    isLoading,
    messages,
    selectedContexts,
    selectedChatId,
    isLoadingChatMessages = false,
    hasNextPage = false,
    fetchNextPage,
    isFetchingNextPage = false,
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
          {/* Load more button for pagination */}
          {hasNextPage && selectedChatId && (
            <div className="flex justify-center mb-4">
              <Button
                variant="outline"
                size="sm"
                onClick={fetchNextPage}
                disabled={isFetchingNextPage}
              >
                {isFetchingNextPage ? (
                  <>
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent mr-2" />
                    Loading...
                  </>
                ) : (
                  "Load more messages"
                )}
              </Button>
            </div>
          )}

          {(isLoading || isLoadingChatMessages) && messages.length === 0 ? (
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
  const chatIdFromUrl = searchParams.get("chatId");
  const [activeTab, setActiveTab] = useState("chat");
  const queryClient = useQueryClient();

  const {
    open: isSidebarOpen,
    isMobile,
    setOpen,
    setOpenMobile,
  } = useSidebar();
  const scrollRef = useRef<HTMLDivElement>(null);
  const {
    selectedChatId,
    selectedChatTitle,
    selectChatForDataset,
    setSelectedChatTitle,
  } = useChatStore();
  const [isStreaming, setIsStreaming] = useState(false);
  const {
    isOpen: sqlIsOpen,
    setIsOpen,
    resetExecutedQueries,
    results,
  } = useSqlStore();
  const {
    isOpen: isVisualizationOpen,
    setIsOpen: setVisualizationOpen,
    paths: visualizationPaths,
    clearPaths: clearVisualizationPaths,
  } = useVisualizationStore();

  // Combined panel state - show if either SQL or visualizations are available
  const isResultsPanelOpen = sqlIsOpen || isVisualizationOpen;
  const hasResults = !!(
    results?.data?.length ||
    results?.error ||
    visualizationPaths.length > 0
  );
  const [isVoiceModeActive, setIsVoiceModeActive] = useState(false);
  const [latestAssistantMessage, setLatestAssistantMessage] = useState<
    string | null
  >(null);

  const [selectedContexts, setSelectedContexts] = useState<ContextItem[]>([]);
  const [initialMessageSent, setInitialMessageSent] = useState(false);
  const [linkedDatasetId, setLinkedDatasetId] = useState<string | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);

  const sqlPanelRef = useRef<HTMLDivElement>(null);
  const [sqlPanelWidth, setSqlPanelWidth] = useState(0);

  // Helper function to update URL with chat state
  const updateUrlWithChatId = useCallback(
    (chatId: string | null) => {
      const params = new URLSearchParams(searchParams.toString());
      if (chatId) {
        params.set("chatId", chatId);
      } else {
        params.delete("chatId");
        params.delete("initialMessage");
        params.delete("contextData");
      }
      router.replace(`/chat?${params.toString()}`);
    },
    [searchParams, router]
  );

  // Fetch all chat messages when a chat is selected
  const {
    data: chatMessagesData,
    isLoading: isLoadingChatMessages,
    error: chatMessagesError,
    hasNextPage,
    fetchNextPage,
    isFetchingNextPage,
  } = useChatMessages({
    variables: {
      chatId: selectedChatId || "",
      limit: 50,
    },
    enabled: !!selectedChatId,
  });

  const allChatMessages = useMemo(() => {
    return chatMessagesData?.pages.flatMap((page) => page.data) || [];
  }, [chatMessagesData]);

  // Fetch chat details when a chat is selected
  const {
    data: chatDetailsData,
    isLoading: isLoadingChatDetails,
    error: chatDetailsError,
  } = useChatDetails({
    variables: {
      chatId: selectedChatId || "",
      userId: "1", // Using hardcoded user ID "1" as in other queries
    },
    enabled: !!selectedChatId,
  });

  const chatDetails = chatDetailsData?.data;

  // State to control whether to use query messages or streaming messages
  const [useStreamingMessages, setUseStreamingMessages] = useState(false);

  // AI SDK Chat Implementation
  const {
    messages: streamingMessages,
    input,
    handleInputChange: sdkHandleInputChange,
    handleSubmit: sdkHandleSubmit,
    isLoading,
    stop,
    error,
    data,
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
      // Pass the current chat ID if available
      chat_id: selectedChatId || undefined,
    },
    onResponse: async (response) => {
      console.log(
        "Chat response received:",
        response.status,
        response.statusText
      );
      // Switch to streaming messages when we start receiving a response
      setUseStreamingMessages(true);
    },
    onFinish: (message, { usage, finishReason }) => {
      console.log("Chat message finished:", message);
      console.log("Usage:", usage);
      console.log("Finish reason:", finishReason);
      console.log("Current selectedChatId when finishing:", selectedChatId);

      // Update latest assistant message for voice mode
      if (message.role === "assistant") {
        setLatestAssistantMessage(message.content);
        setIsStreaming(false);
      }

      // If this was a new chat (no selectedChatId), invalidate chats list
      if (!selectedChatId) {
        console.log("New chat completed, invalidating chats list");
        queryClient.invalidateQueries({ queryKey: ["chats"] });
      }

      // Switch back to query messages and invalidate to get the complete conversation
      setUseStreamingMessages(false);
      queryClient.invalidateQueries({
        queryKey: ["chat-messages", { chatId: selectedChatId }],
      });
    },
    onError: (err) => {
      console.error("Chat error:", err);
      toast.error("Error processing chat: " + (err.message || "Unknown error"));
      // Switch back to query messages on error
      setUseStreamingMessages(false);
    },
    initialMessages: [], // Don't use initial messages from query
  });

  // Determine which messages to display
  const displayMessages = useMemo(() => {
    if (useStreamingMessages && streamingMessages.length > 0) {
      // When streaming, combine query messages with streaming messages
      return [...allChatMessages, ...streamingMessages];
    }
    // Otherwise, use query messages
    return allChatMessages;
  }, [useStreamingMessages, streamingMessages, allChatMessages]);

  // Log messages for debugging
  useEffect(() => {
    console.log("Messages updated:", displayMessages);
  }, [displayMessages]);

  // Log chat title state for debugging
  useEffect(() => {
    console.log("Chat title state:", {
      selectedChatTitle,
      selectedChatId,
      isLoadingChatDetails,
      chatDetails: chatDetails?.title,
    });
    if (chatDetails && chatDetails.title) {
      selectChatForDataset(linkedDatasetId, selectedChatId, chatDetails.title);
      setSelectedChatTitle(chatDetails.title);
    }
  }, [
    selectedChatTitle,
    selectedChatId,
    isLoadingChatDetails,
    chatDetails,
    selectChatForDataset,
    linkedDatasetId,
    setSelectedChatTitle,
  ]);

  // Handle data stream for chat creation
  useEffect(() => {
    if (data && data.length > 0) {
      console.log("Data stream received:", data);
      console.log("Current selectedChatId in data effect:", selectedChatId);

      // Check for chat creation message - look for the most recent one
      const chatCreatedMessages = data.filter((item: unknown) => {
        return (
          typeof item === "object" &&
          item !== null &&
          "type" in item &&
          (item as { type: string }).type === "chat-created"
        );
      }) as { type: string; chatId: string }[];

      console.log("Found chat creation messages:", chatCreatedMessages);

      // Get the latest chat creation message
      const latestChatCreated =
        chatCreatedMessages[chatCreatedMessages.length - 1];

      if (latestChatCreated) {
        console.log(
          "Processing chat creation data:",
          latestChatCreated,
          "Current selectedChatId:",
          selectedChatId
        );

        if (!selectedChatId) {
          console.log(
            "New chat ID created via data stream:",
            latestChatCreated.chatId
          );
          // Update the chat store with the new chat ID and a default title
          const datasetContext = selectedContexts.find(
            (ctx) => ctx.type === "dataset"
          );
          const chatTitle = `Chat ${new Date().toLocaleTimeString()}`;

          selectChatForDataset(
            datasetContext?.id || null,
            latestChatCreated.chatId,
            chatTitle
          );

          // Update URL with the new chat ID
          updateUrlWithChatId(latestChatCreated.chatId);

          // Invalidate both chat list and messages queries to refresh
          queryClient.invalidateQueries({ queryKey: ["chats"] });
          queryClient.invalidateQueries({
            queryKey: ["chat-messages", { chatId: latestChatCreated.chatId }],
          });
        } else {
          console.log(
            "Chat ID already set, ignoring data stream chat creation"
          );
        }
      }
    }
  }, [
    data,
    selectedChatId,
    selectedContexts,
    selectChatForDataset,
    queryClient,
    updateUrlWithChatId,
  ]);

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

  // Note: Projects are now fetched when needed for context selection

  // Initialize chat from URL on first load
  useEffect(() => {
    if (!isInitialized && chatIdFromUrl && chatIdFromUrl !== selectedChatId) {
      // Load the chat from URL if it's different from current selection
      selectChatForDataset(null, chatIdFromUrl, "Loading...");
      setIsInitialized(true);
    } else if (!isInitialized) {
      setIsInitialized(true);
    }
  }, [chatIdFromUrl, selectedChatId, selectChatForDataset, isInitialized]);

  // Update chat title when chat details are loaded
  useEffect(() => {
    console.log("Chat details effect:", {
      chatDetails,
      selectedChatId,
      linkedDatasetId,
      chatDetailsId: chatDetails?.id,
      chatDetailsTitle: chatDetails?.title,
    });

    if (
      chatDetails &&
      selectedChatId &&
      chatDetails.id === selectedChatId &&
      chatDetails.title
    ) {
      console.log("Updating chat title to:", chatDetails.title);
      selectChatForDataset(linkedDatasetId, selectedChatId, chatDetails.title);
    }
  }, [chatDetails, selectedChatId, linkedDatasetId]);

  // Handle chat details loading error
  useEffect(() => {
    if (chatDetailsError) {
      console.error("Error fetching chat details:", chatDetailsError);
      toast.error("Failed to load chat details");
    }
  }, [chatDetailsError]);

  // Reset streaming state when switching chats
  useEffect(() => {
    setUseStreamingMessages(false);
  }, [selectedChatId]);

  // This logic is now handled by the useChatDetails hook above

  // Handle chat messages loading error
  useEffect(() => {
    if (chatMessagesError) {
      console.error("Error fetching chat messages:", chatMessagesError);
      toast.error("Failed to load chat messages");
    }
  }, [chatMessagesError]);

  // Update URL when selectedChatId changes
  useEffect(() => {
    if (isInitialized && selectedChatId !== chatIdFromUrl) {
      updateUrlWithChatId(selectedChatId);
    }
  }, [selectedChatId, chatIdFromUrl, updateUrlWithChatId, isInitialized]);

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
    resetExecutedQueries();
    clearVisualizationPaths();
  }, [selectedChatId, resetExecutedQueries, clearVisualizationPaths]);

  // Handle initial message from URL params
  useEffect(() => {
    if (
      initialMessage &&
      !initialMessageSent &&
      selectedContexts.length > 0 &&
      isInitialized
    ) {
      handleInputChange(initialMessage);

      // Create a submit event for the form
      const submitEvent = new Event("submit", { bubbles: true });
      handleSubmit(submitEvent as unknown as React.FormEvent);

      setInitialMessageSent(true);

      // Only remove initialMessage and contextData, preserve chatId
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
    isInitialized,
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
  }, [displayMessages]);

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
    if (!isResultsPanelOpen) {
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
  }, [isResultsPanelOpen, sqlPanelRef]);

  // Update streaming state based on isLoading
  useEffect(() => {
    setIsStreaming(isLoading);
  }, [isLoading]);

  // Handle stopping the stream
  const handleStop = useCallback(() => {
    stop();
    setIsStreaming(false);
  }, [stop]);

  // Close sidebar when chat page opens
  useEffect(() => {
    if (isMobile) {
      setOpenMobile(false);
    } else {
      setOpen(false);
    }
  }, []); // Empty dependency array means this runs only once on mount

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
                    {isLoadingChatDetails && selectedChatId
                      ? "Loading..."
                      : selectedChatTitle
                      ? selectedChatTitle
                      : "Chat"}
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
                    setSelectedContexts([]);

                    // Clear URL parameters when starting a new chat
                    const params = new URLSearchParams(searchParams.toString());
                    params.delete("chatId");
                    params.delete("initialMessage");
                    params.delete("contextData");
                    router.replace(`/chat?${params.toString()}`);
                  }}
                >
                  <MessageSquarePlus className="h-4 w-4 mr-1" />
                  New Chat
                </Button>
                {hasResults && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="mr-2"
                    onClick={() => {
                      if (isResultsPanelOpen) {
                        setIsOpen(false);
                        setVisualizationOpen(false);
                      } else {
                        if (results?.data?.length || results?.error) {
                          setIsOpen(true);
                        }
                        if (visualizationPaths.length > 0) {
                          setVisualizationOpen(true);
                        }
                      }
                    }}
                  >
                    <Table2 className="h-4 w-4 mr-1" />
                    Results
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
                    messages={displayMessages}
                    selectedContexts={selectedContexts}
                    selectedChatId={selectedChatId}
                    isLoadingChatMessages={isLoadingChatMessages}
                    hasNextPage={hasNextPage}
                    fetchNextPage={fetchNextPage}
                    isFetchingNextPage={isFetchingNextPage}
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
                  searchParams={searchParams}
                  router={router}
                />
              </TabsContent>
            </Tabs>
          </ResizablePanel>
          {isResultsPanelOpen && (
            <>
              <ResizableHandle />
              <ResizablePanel defaultSize={70} minSize={30}>
                <div ref={sqlPanelRef} className="h-screen overflow-hidden">
                  <ResultsPanel
                    isOpen={isResultsPanelOpen}
                    onClose={() => {
                      setIsOpen(false);
                      setVisualizationOpen(false);
                    }}
                  />
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
            width: isResultsPanelOpen
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

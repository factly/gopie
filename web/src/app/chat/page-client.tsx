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
import { MessageSquarePlus, Trash2 } from "lucide-react";
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
import { History, PanelLeft } from "lucide-react";
import { useChatStore } from "@/lib/stores/chat-store";
// import { VoiceMode } from "@/components/chat/voice-mode";
// import { VoiceModeToggle } from "@/components/chat/voice-mode-toggle";
import { MentionInput } from "@/components/chat/mention-input";
import { ContextPicker, ContextItem } from "@/components/chat/context-picker";
import { ShareChatDialog } from "@/components/chat/share-chat-dialog";
import { ChatVisibilityIndicator } from "@/components/chat/chat-visibility-indicator";
import { ReadOnlyMessage } from "@/components/chat/read-only-message";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useSearchParams, useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { useQueryClient } from "@tanstack/react-query";
import { useSidebar } from "@/components/ui/sidebar";
import { UIMessage } from "ai";
import { useAuthStore } from "@/lib/stores/auth-store";

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
  currentUserId,
  updateUrlWithContext,
}: {
  setActiveTab: (tab: string) => void;
  setSelectedContexts: (contexts: ContextItem[]) => void;
  setLinkedDatasetId: (datasetId: string | null) => void;
  currentUserId: string;
  updateUrlWithContext: (contexts: ContextItem[]) => void;
}) {
  const { selectChatForDataset, selectedChatId } = useChatStore();
  const queryClient = useQueryClient();
  const { resetExecutedQueries, setIsOpen } = useSqlStore();
  const { clearPaths: clearVisualizationPaths, setIsOpen: setVisualizationOpen } = useVisualizationStore();

  const deleteChat = useDeleteChat();

  // Use the infinite query hook
  const {
    data: chatsData,
    isLoading,
    error,
  } = useChats({
    variables: { userID: currentUserId, limit: 100 },
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

  const handleDeleteChat = async (chatId: string) => {
    try {
      await deleteChat.mutateAsync({
        chatId,
        userId: currentUserId,
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
        updateUrlWithContext([]);
        setLinkedDatasetId(null);
        // Clear results when deleting the current chat
        resetExecutedQueries();
        clearVisualizationPaths();
        setIsOpen(false);
        setVisualizationOpen(false);
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
    // Clear results when selecting a different chat
    resetExecutedQueries();
    clearVisualizationPaths();
    setIsOpen(false);
    setVisualizationOpen(false);

    if (datasetId && datasetName && projectId) {
      const newContexts = [
        {
          id: datasetId,
          type: "dataset" as const,
          name: datasetName,
          projectId: projectId,
        },
      ];
      setSelectedContexts(newContexts);
      updateUrlWithContext(newContexts);
      selectChatForDataset(datasetId, chatId, chatName || "New Chat");
      setLinkedDatasetId(datasetId);
    } else {
      setSelectedContexts([]);
      updateUrlWithContext([]);
      selectChatForDataset(null, chatId, chatName || "New Chat");
      setLinkedDatasetId(null);
    }
    setActiveTab("chat");
  };

  useEffect(() => {
    if (!selectedChatId) {
      setLinkedDatasetId(null);
    }
  }, [selectedChatId, setLinkedDatasetId, selectChatForDataset]);

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
    <div className="flex flex-col">


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
                    "group relative flex flex-col px-4 py-3 hover:bg-muted cursor-pointer transition-colors",
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
                      <ChatVisibilityIndicator visibility={chat.visibility} />
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
                    {dateString}
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
  // isVoiceModeActive: boolean;
  // setIsVoiceModeActive: (active: boolean) => void;
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
    // isVoiceModeActive,
    // setIsVoiceModeActive,
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
        <div className="flex items-start gap-2 w-full pr-2">
          <ContextPicker
            selectedContexts={selectedContexts}
            onSelectContext={onSelectContext}
            onRemoveContext={onRemoveContext}
            triggerClassName="h-10 w-10 bg-transparent text-foreground hover:bg-black/5 dark:hover:bg-white/5"
            lockableContextIds={lockableContextIds}
          />
          <MentionInput
            value={input}
            onChange={handleMentionInputChange}
            onSubmit={handleSubmit}
            disabled={isLoading}
            placeholder="Ask questions about your data..."
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
            // actionButtons={
            //   <VoiceModeToggle
            //     isActive={isVoiceModeActive}
            //     onToggle={() => setIsVoiceModeActive(!isVoiceModeActive)}
            //   />
            // }
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
  // selectedContexts: ContextItem[]; // Removed since not used in component
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
    // selectedContexts, // Removed since not used in component
    selectedChatId,
    isLoadingChatMessages = false,
    hasNextPage = false,
    fetchNextPage,
    isFetchingNextPage = false,
  }: ChatViewProps) => (
    <div className="flex-1 overflow-hidden relative min-h-0">
      <div
        className={`z-10 absolute inset-x-0 top-0 h-8 bg-gradient-to-b from-background via-background to-transparent pointer-events-none ${
          messages.length > 0 ? "opacity-100" : "opacity-0"
        } transition-opacity duration-300`}
      />
      <ScrollArea
        ref={scrollRef}
        className="h-full w-full"
        onScroll={handleScroll}
      >
        <div className="px-4 pb-32 pt-8">
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
                    <div className="h-4 w-4 animate-spin border-2 border-current border-t-transparent mr-2" />
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
          ) : !selectedChatId && messages.length === 0 ? null : (
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
  const contextsFromUrl = searchParams.get("contexts");
  const chatIdFromUrl = searchParams.get("chatId");
  const tabFromUrl = searchParams.get("tab");
  const [activeTab, setActiveTab] = useState(tabFromUrl === "history" ? "history" : "chat");
  const queryClient = useQueryClient();

  // Get current user from auth store
  const { user } = useAuthStore();
  const currentUserId = user?.id || "1"; // Fallback to "1" if no user

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
  const [showLoadingMessage, setShowLoadingMessage] = useState(false);
  const {
    isOpen: sqlIsOpen,
    setIsOpen,
    resetExecutedQueries,
    // results, // removed unused variable
  } = useSqlStore();
  const {
    isOpen: isVisualizationOpen,
    setIsOpen: setVisualizationOpen,
    // paths: visualizationPaths, // removed unused variable
    clearPaths: clearVisualizationPaths,
  } = useVisualizationStore();

  // Combined panel state - show if either SQL or visualizations are available
  const isResultsPanelOpen = sqlIsOpen || isVisualizationOpen;
  // const [isVoiceModeActive, setIsVoiceModeActive] = useState(false);
  // const [latestAssistantMessage, setLatestAssistantMessage] = useState<
  //   string | null
  // >(null);

  const [selectedContexts, setSelectedContexts] = useState<ContextItem[]>([]);
  const [initialMessageSent, setInitialMessageSent] = useState(false);
  const [linkedDatasetId, setLinkedDatasetId] = useState<string | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);
  const [contextInitialized, setContextInitialized] = useState(false);

  const sqlPanelRef = useRef<HTMLDivElement>(null);

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

  // Helper function to update URL with context data
  const updateUrlWithContext = useCallback(
    (contexts: ContextItem[]) => {
      const params = new URLSearchParams(searchParams.toString());
      if (contexts.length > 0) {
        params.set("contexts", encodeURIComponent(JSON.stringify(contexts)));
      } else {
        params.delete("contexts");
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
      userId: currentUserId,
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
      setIsStreaming(true);
      // Hide loading message once we start receiving the actual stream
      setShowLoadingMessage(false);
    },
    onFinish: (message, { usage, finishReason }) => {
      console.log("Chat message finished:", message);
      console.log("Usage:", usage);
      console.log("Finish reason:", finishReason);
      console.log("Current selectedChatId when finishing:", selectedChatId);

      // Update latest assistant message for voice mode
      if (message.role === "assistant") {
        // setLatestAssistantMessage(message.content); // Removed voice mode state
        setIsStreaming(false);
        setShowLoadingMessage(false);
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
      setIsStreaming(false);
      setShowLoadingMessage(false);
    },
    initialMessages: [], // Don't use initial messages from query
  });

  // Determine which messages to display
  const displayMessages = useMemo(() => {
    let messages = [];
    
    if (useStreamingMessages) {
      // When streaming, show streaming messages (which includes the user message immediately)
      // If we have a selectedChatId, prepend existing messages
      if (selectedChatId && allChatMessages.length > 0) {
        messages = [...allChatMessages, ...streamingMessages];
      } else {
        // For new chats, just show streaming messages
        messages = streamingMessages;
      }
    } else {
      // Otherwise, use query messages
      messages = allChatMessages;
    }
    
    // Add optimistic loading message if needed
    if (showLoadingMessage && messages.length > 0) {
      // Check if the last message is from the user and there's no assistant message yet
      const lastMessage = messages[messages.length - 1];
      const hasAssistantResponse = streamingMessages.some(msg => msg.role === 'assistant' && msg.content);
      
      if (lastMessage.role === 'user' && !hasAssistantResponse) {
        // Add a loading assistant message
        messages = [...messages, {
          id: 'loading-' + Date.now(),
          role: 'assistant' as const,
          content: '',
          createdAt: new Date()
        } as UIMessage];
      }
    }
    
    return messages;
  }, [useStreamingMessages, streamingMessages, allChatMessages, selectedChatId, showLoadingMessage]);

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
      // Prevent submission if no context is selected
      if (selectedContexts.length === 0) {
        toast.error("Please select at least one project or dataset before sending a message");
        return;
      }
      
      // For new chats, immediately switch to streaming messages to show the user message
      if (!selectedChatId && input.trim()) {
        setUseStreamingMessages(true);
      }
      
      // Set loading state immediately
      setIsStreaming(true);
      setShowLoadingMessage(true);
      
      sdkHandleSubmit(e as unknown as React.FormEvent);
    },
    [sdkHandleSubmit, selectedContexts, selectedChatId, input]
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

  // Initialize contexts from URL on first load
  useEffect(() => {
    if (!contextInitialized && contextsFromUrl && !contextData) {
      try {
        const parsedContexts = JSON.parse(decodeURIComponent(contextsFromUrl)) as ContextItem[];
        if (Array.isArray(parsedContexts) && parsedContexts.length > 0) {
          setSelectedContexts(parsedContexts);
          
          // Set linked dataset if there's a dataset context
          const datasetContext = parsedContexts.find(ctx => ctx.type === "dataset");
          if (datasetContext) {
            setLinkedDatasetId(datasetContext.id);
          }
        }
      } catch (error) {
        console.error("Failed to parse contexts from URL:", error);
      }
      setContextInitialized(true);
    } else if (!contextInitialized) {
      setContextInitialized(true);
    }
  }, [contextsFromUrl, contextData, contextInitialized]);

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
  }, [chatDetails, selectedChatId, linkedDatasetId, selectChatForDataset, setSelectedChatTitle]);

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
    setShowLoadingMessage(false);
    setIsStreaming(false);
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

  // Refresh chat details when chat ID changes
  useEffect(() => {
    if (selectedChatId) {
      queryClient.invalidateQueries({
        queryKey: ["chat-details", { chatId: selectedChatId }],
      });
    }
  }, [selectedChatId, queryClient]);

  useEffect(() => {
    if (contextData) {
      try {
        const parsedContexts = JSON.parse(
          decodeURIComponent(contextData)
        ) as ContextItem[];
        if (Array.isArray(parsedContexts) && parsedContexts.length > 0) {
          // Clear existing chat when navigating with new context data
          selectChatForDataset(null, null, null);
          setLinkedDatasetId(null);
          setSelectedContexts(parsedContexts);
          // Clear results when navigating with new context data
          resetExecutedQueries();
          clearVisualizationPaths();
          setIsOpen(false);
          setVisualizationOpen(false);
          // Clear URL parameters to avoid re-applying context data
          const params = new URLSearchParams(searchParams.toString());
          params.delete("contextData");
          router.replace(`/chat?${params.toString()}`);
        }
      } catch (error) {
        console.error("Failed to parse context data:", error);
      }
    }
  }, [contextData, resetExecutedQueries, clearVisualizationPaths, setIsOpen, setVisualizationOpen, selectChatForDataset, setLinkedDatasetId, searchParams, router]);

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
      isInitialized &&
      !isLoading // Don't submit if already loading
    ) {
      // Decode the initial message
      const decodedMessage = decodeURIComponent(initialMessage);
      
      // Set the input value
      handleInputChange(decodedMessage);

      // Mark as sent immediately to prevent double submission
      setInitialMessageSent(true);

      // Use requestAnimationFrame to ensure React has updated the DOM
      requestAnimationFrame(() => {
        // Another frame to ensure the input value is properly set
        requestAnimationFrame(() => {
          // Now submit the form
          const form = document.querySelector('form');
          if (form && form instanceof HTMLFormElement) {
            // Try using requestSubmit if available (modern browsers)
            if ('requestSubmit' in form && typeof form.requestSubmit === 'function') {
              form.requestSubmit();
            } else {
              // Fallback for older browsers
              const submitEvent = new Event('submit', { 
                bubbles: true, 
                cancelable: true 
              });
              form.dispatchEvent(submitEvent);
            }
          } else {
            // Direct fallback if form is not found
            const submitEvent = new Event("submit", { 
              bubbles: true, 
              cancelable: true 
            });
            handleSubmit(submitEvent as unknown as React.FormEvent);
          }
        });
      });

      // Clean up URL parameters after a short delay
      setTimeout(() => {
        const params = new URLSearchParams(searchParams.toString());
        params.delete("initialMessage");
        params.delete("contextData");
        router.replace(`/chat?${params.toString()}`);
      }, 500);
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
    isLoading,
  ]);

  const handleScroll = useCallback(() => {
    // Handle scroll - can be used for loading more messages if needed
  }, []);

  useLayoutEffect(() => {
    if (scrollRef.current && displayMessages.length > 0) {
      const viewport = scrollRef.current.querySelector(
        "[data-radix-scroll-area-viewport]"
      );
      if (viewport) {
        const isNearBottom =
          viewport.scrollHeight - viewport.scrollTop - viewport.clientHeight <
          150;
        // Only auto-scroll if user is near the bottom or if it's a new message being added
        const lastMessage = displayMessages[displayMessages.length - 1];
        const shouldAutoScroll =
          isNearBottom &&
          (lastMessage?.role === "assistant" || lastMessage?.role === "user");

        if (shouldAutoScroll) {
          requestAnimationFrame(() => {
            viewport.scrollTo({
              top: viewport.scrollHeight,
              behavior: "smooth",
            });
          });
        }
      }
    }
  }, [displayMessages]);

  const handleSelectContext = useCallback((context: ContextItem) => {
    setSelectedContexts((prev) => {
      const newContexts = [...prev, context];
      updateUrlWithContext(newContexts);
      return newContexts;
    });
  }, [updateUrlWithContext]);

  const handleRemoveContext = useCallback((contextId: string) => {
    setSelectedContexts((prev) => {
      const newContexts = prev.filter((c) => c.id !== contextId);
      updateUrlWithContext(newContexts);
      return newContexts;
    });
  }, [updateUrlWithContext]);

  // const handleSendVoiceMessage = useCallback(
  //   async (message: string) => {
  //     handleInputChange(message);

  //     // Create a submit event for the form
  //     const submitEvent = new Event("submit", { bubbles: true });
  //     handleSubmit(submitEvent as unknown as React.FormEvent);
  //   },
  //   [handleInputChange, handleSubmit]
  // );

  // Removed unused sqlPanelWidth state management

  // Update streaming state based on isLoading
  useEffect(() => {
    setIsStreaming(isLoading);
  }, [isLoading]);

  // Handle stopping the stream
  const handleStop = useCallback(() => {
    stop();
    setIsStreaming(false);
  }, [stop]);

  // Check if current user owns the chat
  const isCurrentUserOwner =
    !chatDetails || chatDetails.created_by === currentUserId;

  const isAuthDisabled = String(process.env.NEXT_PUBLIC_ENABLE_AUTH).trim() !== "true";

  console.log("currentUserId", currentUserId);
  console.log("chatDetails", chatDetails);
  console.log("isCurrentUserOwner", isCurrentUserOwner);
  console.log("chatDetails.created_by", chatDetails?.created_by);

  // Close sidebar when chat page opens
  useEffect(() => {
    if (isMobile) {
      setOpenMobile(false);
    } else {
      setOpen(false);
    }
  }, [isMobile, setOpen, setOpenMobile]); // Added missing dependencies

  return (
    <main className="flex flex-col w-full h-[calc(100vh-16px)]">
      <div className="flex w-full relative overflow-hidden h-full">
        <ResizablePanelGroup direction="horizontal">
          <ResizablePanel minSize={30}>
            <div className="relative w-full h-full">
              <Tabs
                value={activeTab}
                onValueChange={(value) => {
                  setActiveTab(value);
                  // Update URL with tab parameter
                  const params = new URLSearchParams(searchParams.toString());
                  if (value === "history") {
                    params.set("tab", "history");
                  } else {
                    params.delete("tab");
                  }
                  router.replace(`/chat?${params.toString()}`);
                }}
                className="w-full h-full flex flex-col relative"
              >
              <div className="flex w-full items-center border-b relative z-10">
                <Button
                  variant="ghost"
                  size="sm"
                  className="mr-2 ml-2 p-1 h-10 w-8"
                  onClick={() => {
                    if (isMobile) {
                      setOpenMobile(!isSidebarOpen);
                    } else {
                      setOpen(!isSidebarOpen);
                    }
                  }}
                >
                  <PanelLeft className="h-4 w-4" />
                </Button>
                <TabsList className="flex-1 h-10 grid grid-cols-1 rounded-none bg-background">
                  <TabsTrigger
                    value="chat"
                    className="data-[state=active]:border-b-2 data-[state=active]:border-primary data-[state=active]:bg-background data-[state=active]:shadow-none data-[state=active]:font-medium rounded-none px-4 py-2 text-sm transition-all truncate"
                  >
                    <div className="flex items-center gap-2 truncate">
                      {chatDetails?.visibility && (
                        <ChatVisibilityIndicator
                          visibility={chatDetails.visibility}
                        />
                      )}
                      <span className="truncate">
                        {isLoadingChatDetails && selectedChatId
                          ? "Loading..."
                          : selectedChatTitle
                          ? selectedChatTitle
                          : "Chat"}
                      </span>
                    </div>
                  </TabsTrigger>
                </TabsList>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="sm"
                      className={`mr-2 ${activeTab === "history" ? "bg-muted border-b-2 border-primary" : ""}`}
                      onClick={() => {
                        setActiveTab("history");
                        // Update URL with tab parameter
                        const params = new URLSearchParams(searchParams.toString());
                        params.set("tab", "history");
                        router.replace(`/chat?${params.toString()}`);
                      }}
                    >
                      <History className="h-4 w-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>History</p>
                  </TooltipContent>
                </Tooltip>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="mr-2"
                      onClick={() => {
                        selectChatForDataset(null, null, null);
                        setLinkedDatasetId(null);
                        setActiveTab("chat");
                        setSelectedContexts([]);
                        updateUrlWithContext([]);

                    // Clear results when starting a new chat
                    resetExecutedQueries();
                    clearVisualizationPaths();
                    setIsOpen(false);
                    setVisualizationOpen(false);

                        // Clear URL parameters when starting a new chat
                        const params = new URLSearchParams(searchParams.toString());
                        params.delete("chatId");
                        params.delete("initialMessage");
                        params.delete("contextData");
                        params.delete("contexts");
                        router.replace(`/chat?${params.toString()}`);
                      }}
                    >
                      <MessageSquarePlus className="h-4 w-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>New Chat</p>
                  </TooltipContent>
                </Tooltip>
                {selectedChatId && (
                  <ShareChatDialog
                    chatId={selectedChatId}
                    currentVisibility={chatDetails?.visibility || "private"}
                  />
                )}

              </div>

              <TabsContent
                value="chat"
                className="flex-1 overflow-hidden flex flex-col data-[state=inactive]:hidden p-0 border-none min-h-0"
              >
                <div className="flex flex-col h-full min-h-0 relative">
                  <ChatView
                    scrollRef={scrollRef}
                    handleScroll={handleScroll}
                    isLoading={isLoading}
                    messages={displayMessages}
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
                  currentUserId={currentUserId}
                  updateUrlWithContext={updateUrlWithContext}
                />
              </TabsContent>
              </Tabs>
              {activeTab === "chat" && (
                <>
                  {!selectedChatId && displayMessages.length === 0 ? (
                    <div className="absolute inset-0 flex items-center justify-center px-4 pointer-events-none">
                      <div className="w-full max-w-2xl pointer-events-auto">
                        <div className="mb-6 text-center">
                          <h1 className="text-2xl md:text-3xl font-bold text-foreground mb-2">
                            Chat with your data
                          </h1>
                          <p className="text-sm text-muted-foreground">
                            Select contexts and ask questions about your data
                          </p>
                        </div>
                        <div
                          className="bg-card border border-border shadow-lg 
                          ring-[1.5px] ring-foreground/10 
                          hover:ring-foreground/20 hover:shadow-xl hover:border-foreground/20
                          focus-within:ring-primary/30 focus-within:border-primary/50 focus-within:shadow-primary/10
                          transition-all duration-200"
                        >
                          <div className="flex items-center">
                            <div className="flex items-center justify-center h-12 w-12">
                              <ContextPicker
                                selectedContexts={selectedContexts}
                                onSelectContext={handleSelectContext}
                                onRemoveContext={handleRemoveContext}
                                triggerClassName="flex items-center justify-center h-9 w-9 text-muted-foreground hover:bg-muted hover:text-foreground transition-all duration-200 bg-muted/70"
                              />
                            </div>
                            <MentionInput
                              value={input}
                              onChange={handleInputChange}
                              onSubmit={handleSubmit}
                              disabled={isLoading}
                              placeholder="Ask questions about your data..."
                              selectedContexts={selectedContexts}
                              onSelectContext={handleSelectContext}
                              onRemoveContext={handleRemoveContext}
                              className="flex-1"
                              showSendButton={true}
                              isSending={isLoading}
                              isStreaming={isStreaming}
                              stopMessageStream={handleStop}
                              lockableContextIds={[]}
                              hasContext={selectedContexts.length > 0}
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="absolute bottom-0 left-0 right-0 z-20">
                      {isCurrentUserOwner || isAuthDisabled ? (
                        <ChatInput
                          onStop={handleStop}
                          isStreaming={isStreaming}
                          selectedContexts={selectedContexts}
                          onSelectContext={handleSelectContext}
                          onRemoveContext={handleRemoveContext}
                          // isVoiceModeActive={isVoiceModeActive}
                          // setIsVoiceModeActive={setIsVoiceModeActive}
                          lockableContextIds={
                            selectedChatId && linkedDatasetId ? [linkedDatasetId] : []
                          }
                          hasContext={selectedContexts.length > 0}
                          input={input}
                          handleInputChange={handleInputChange}
                          handleSubmit={handleSubmit}
                          isLoading={isLoading}
                        />
                      ) : selectedChatId ? (
                        <ReadOnlyMessage
                          chatOwner={chatDetails?.created_by}
                          chatVisibility={chatDetails?.visibility}
                          chatTitle={chatDetails?.title}
                        />
                      ) : null}
                    </div>
                  )}
                </>
              )}
            </div>
          </ResizablePanel>
          {isResultsPanelOpen && (
            <>
              <ResizableHandle />
              <ResizablePanel defaultSize={70} minSize={30}>
                <div ref={sqlPanelRef} className="h-[calc(100vh-16px)]">
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

      {/* {isVoiceModeActive && latestAssistantMessage && (
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
      )} */}
    </main>
  );
}

export default ChatPageClient;

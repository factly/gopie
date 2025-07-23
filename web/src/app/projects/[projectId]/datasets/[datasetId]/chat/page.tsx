"use client";

import {
  useEffect,
  useRef,
  useState,
  useLayoutEffect,
  useCallback,
  useMemo,
  use,
} from "react";
import { useChatMessages } from "@/lib/queries/chat";
import { useCreateChat } from "@/lib/mutations/chat";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import { Table2, MessageSquarePlus } from "lucide-react";
import { useSidebar } from "@/components/ui/sidebar";
import { motion, AnimatePresence } from "framer-motion";
import { ChatMessage } from "@/components/chat/message";
import { SqlResults } from "@/components/chat/sql-results";
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import { useSqlStore } from "@/lib/stores/sql-store";
import { useVisualizationStore } from "@/lib/stores/visualization-store";
import { ChatTabs } from "@/components/chat/chat-tabs";
import { useChatStore } from "@/lib/stores/chat-store";
import { VoiceMode } from "@/components/chat/voice-mode";
import { VoiceModeToggle } from "@/components/chat/voice-mode-toggle";
import { ChatHistory } from "@/components/chat/chat-history";
import { MentionInput } from "@/components/chat/mention-input";
import { ContextPicker, ContextItem } from "@/components/chat/context-picker";
import { useDataset } from "@/lib/queries/dataset/get-dataset";

interface ChatPageProps {
  params: Promise<{
    projectId: string;
    datasetId: string;
  }>;
}

interface OptimisticMessage {
  id: string;
  content: string;
  role: "user" | "assistant";
  created_at: string;
  isLoading?: boolean;
}

export default function ChatPage({ params: paramsPromise }: ChatPageProps) {
  const params = use(paramsPromise);
  const { setOpen } = useSidebar();
  const scrollRef = useRef<HTMLDivElement>(null);
  const { getSelectedChatForDataset, selectChatForDataset } = useChatStore();
  const { id: selectedChatId, title: selectedChatTitle } =
    getSelectedChatForDataset(params.datasetId);
  const [isSending, setIsSending] = useState(false);
  const [optimisticMessages, setOptimisticMessages] = useState<
    OptimisticMessage[]
  >([]);
  const { isOpen, setIsOpen, resetExecutedQueries } = useSqlStore();
  const { clearPaths: clearVisualizationPaths, setIsOpen: setVisualizationOpen } = useVisualizationStore();
  const [isVoiceModeActive, setIsVoiceModeActive] = useState(false);
  const [latestAssistantMessage, setLatestAssistantMessage] = useState<
    string | null
  >(null);

  const [inputValue, setInputValue] = useState("");
  const [selectedContexts, setSelectedContexts] = useState<ContextItem[]>([]);

  // Fetch current dataset information
  const { data: datasetData } = useDataset({
    variables: {
      projectId: params.projectId,
      datasetId: params.datasetId,
    },
    enabled: !!params.projectId && !!params.datasetId,
  });

  // Add dataset to context by default when dataset data is available
  useEffect(() => {
    if (datasetData && params.projectId) {
      const datasetContext: ContextItem = {
        id: params.datasetId,
        type: "dataset",
        name: datasetData.alias || `Dataset ${params.datasetId}`,
        projectId: params.projectId,
      };

      setSelectedContexts((prev) => {
        if (!prev.some((ctx) => ctx.id === params.datasetId)) {
          return [...prev, datasetContext];
        }
        return prev;
      });
    }
  }, [datasetData, params.datasetId, params.projectId]);

  // Close sidebar only on initial mount
  useEffect(() => {
    setOpen(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
    const messages = messagesData?.pages.flatMap((page) => page.data) ?? [];
    return messages.sort((a, b) => {
      const timeA = new Date(a.createdAt || "").getTime();
      const timeB = new Date(b.createdAt || "").getTime();
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
        console.log(
          "Updated latest assistant message:",
          lastAssistantMessage.content.slice(0, 50) + "..."
        );
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
        console.log(
          "Setting latest assistant message from optimistic:",
          lastOptimisticAssistant.content.slice(0, 50) + "..."
        );
        setLatestAssistantMessage(lastOptimisticAssistant.content);
      }
    }
  }, [optimisticMessages]);

  // Clear latest assistant message when sending a new message
  useEffect(() => {
    if (isSending) {
      console.log(
        "Clearing latest assistant message due to new message being sent"
      );
      setLatestAssistantMessage(null);
    }
  }, [isSending]);

  // Mutations
  const createChat = useCreateChat();

  // Reset optimistic messages when changing chats
  useEffect(() => {
    setOptimisticMessages([]);
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

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || isSending) return;

    try {
      await sendMessage(inputValue);
      setInputValue("");
    } catch (error) {
      console.error("Failed to send message:", error);
      toast.error("Failed to send message");
    }
  };

  const sendMessage = async (message: string) => {
    if (!message.trim() || isSending) return;

    setIsSending(true);
    const optimisticId = Date.now().toString();
    let chatId = selectedChatId;

    try {
      // Collect context information for the backend
      // Note: We're preparing this but the backend may not use it yet
      const contextData =
        selectedContexts.length > 0
          ? selectedContexts.map((ctx) => ({
              id: ctx.id,
              type: ctx.type,
              projectId: ctx.projectId || undefined,
            }))
          : [];

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

      // Create a new chat or use existing one
      if (!chatId) {
        const result = await createChat.mutateAsync({
          datasetId: params.datasetId,
          messages: [{ role: "user", content: message }],
          // Backend will need to be updated to use contextData
        });
        chatId = result.data.id;
        selectChatForDataset(
          params.datasetId,
          chatId,
          message.substring(0, 40) + "..."
        );

        // Log the contexts for debugging
        if (contextData.length > 0) {
          console.log("Sending contexts:", contextData);
        }
      } else {
        // Send message to existing chat
        await createChat.mutateAsync({
          datasetId: params.datasetId,
          chatId: chatId,
          messages: [{ role: "user", content: message }],
          // Backend will need to be updated to use contextData
        });

        // Log the contexts for debugging
        if (contextData.length > 0) {
          console.log("Sending contexts:", contextData);
        }

        // Refresh messages to get the response
        await refetchMessages();
      }

      // Remove ALL optimistic messages related to this interaction after successful API call
      setOptimisticMessages((prev) =>
        prev.filter((msg) => !msg.id.includes(optimisticId.toString()))
      );
    } catch (error) {
      toast.error("Failed to send message");
      console.error(error);
      // Clean up optimistic messages in case of error
      setOptimisticMessages((prev) =>
        prev.filter((msg) => !msg.id.includes(optimisticId.toString()))
      );
      throw error; // Re-throw to handle in caller
    } finally {
      setIsSending(false);
    }
  };

  // Sort optimistic messages by time
  const sortedOptimisticMessages = useMemo(() => {
    return optimisticMessages.sort((a, b) => {
      const timeA = new Date(a.created_at).getTime();
      const timeB = new Date(b.created_at).getTime();
      if (timeA === timeB) {
        return a.role === "user" ? -1 : 1;
      }
      return timeA - timeB;
    });
  }, [optimisticMessages]);

  // Handle context selection
  const handleSelectContext = (context: ContextItem) => {
    setSelectedContexts((prev) => [...prev, context]);
  };

  // Handle context removal but prevent removing the current dataset
  const handleRemoveContext = (contextId: string) => {
    // Don't allow removing the current dataset
    if (contextId === params.datasetId) return;

    setSelectedContexts((prev) => prev.filter((c) => c.id !== contextId));
  };

  const ChatInput = () => {
    return (
      <div className="flex flex-col gap-2 w-full">
        <div className="flex items-center gap-2">
          <div className="flex-1 flex gap-2 items-center">
            <ContextPicker
              selectedContexts={selectedContexts}
              onSelectContext={handleSelectContext}
              onRemoveContext={handleRemoveContext}
              currentDatasetId={params.datasetId}
              currentProjectId={params.projectId}
              triggerClassName="h-11 w-11 rounded-full"
              lockableContextIds={[params.datasetId]}
            />
            <MentionInput
              value={inputValue}
              onChange={setInputValue}
              onSubmit={handleSendMessage}
              disabled={isSending}
              placeholder="Type your message... (use @ to mention datasets or projects)"
              selectedContexts={selectedContexts}
              onSelectContext={handleSelectContext}
              onRemoveContext={handleRemoveContext}
              className="flex-1"
              showSendButton={true}
              isSending={isSending}
              actionButtons={
                <>
                  {!selectedChatId && (
                    <ChatHistory
                      datasetId={params.datasetId}
                      variant="ghost"
                      className="mr-0.5"
                    />
                  )}
                  <VoiceModeToggle
                    isActive={isVoiceModeActive}
                    onToggle={() => setIsVoiceModeActive(!isVoiceModeActive)}
                    className="h-9 w-9 flex-shrink-0 rounded-full mr-0.5"
                    variant="ghost"
                  />
                </>
              }
            />
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="h-screen flex w-full bg-background">
      <ResizablePanelGroup direction="horizontal">
        <ResizablePanel minSize={30}>
          <div className="flex h-full flex-col overflow-hidden">
            <div className="border-b bg-background/80 backdrop-blur-sm z-10 shadow-sm p-4 flex justify-between items-center">
              <h1 className="font-semibold flex items-center gap-2">
                {selectedChatId ? (
                  <span className="truncate max-w-60 text-foreground/90">
                    {selectedChatTitle || "New Chat"}
                  </span>
                ) : (
                  <span className="text-foreground/90">New Chat</span>
                )}
              </h1>

              <div className="flex gap-2 items-center">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    selectChatForDataset(params.datasetId, null, null);
                    // Clear results when starting a new chat
                    resetExecutedQueries();
                    clearVisualizationPaths();
                    setIsOpen(false);
                    setVisualizationOpen(false);
                  }}
                  className="gap-1.5 h-9 font-medium shadow-sm"
                >
                  <MessageSquarePlus className="h-3.5 w-3.5" />
                  New Chat
                </Button>
                {showSqlButton && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setIsOpen(!isOpen)}
                    className="gap-1.5 h-9 font-medium shadow-sm"
                  >
                    <Table2 className="h-3.5 w-3.5" />
                    {isOpen ? "Hide Results" : "Show Results"}
                  </Button>
                )}
              </div>
            </div>

            {selectedChatId ? (
              <ChatTabs datasetId={params.datasetId}>
                <div className="relative flex-1">
                  <AnimatePresence mode="wait">
                    <motion.div
                      className="absolute inset-0 flex flex-col"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 0.3 }}
                    >
                      {/* Messages */}
                      <ScrollArea
                        ref={scrollRef}
                        className="flex-1 px-4 py-6"
                        onScroll={handleScroll}
                      >
                        {isLoadingMessages && !isFetchingNextPage ? (
                          <div className="space-y-6 px-2">
                            {Array.from({ length: 3 }).map((_, i) => (
                              <Skeleton key={i} className="h-24 w-full" />
                            ))}
                          </div>
                        ) : (
                          <div className="space-y-6 px-2">
                            {/* Loading more indicator */}
                            {isFetchingNextPage && (
                              <div className="flex justify-center py-3">
                                <span className="h-5 w-5 animate-spin rounded-full border-2 border-muted-foreground border-t-transparent" />
                              </div>
                            )}

                            {/* Real messages */}
                            {allMessages.map((message, index) => (
                              <ChatMessage
                                key={message.id}
                                id={message.id}
                                content={message.content}
                                role={message.role as "user" | "assistant"}
                                createdAt={message.createdAt?.toString() || ""} // TODO: fix this
                                chatId={selectedChatId || undefined}
                                isLatest={
                                  index === allMessages.length - 1 &&
                                  !sortedOptimisticMessages.length
                                }
                              />
                            ))}

                            {/* Optimistic messages */}
                            {sortedOptimisticMessages.map((message, index) => (
                              <ChatMessage
                                key={message.id}
                                id={message.id}
                                content={message.content}
                                role={message.role}
                                createdAt={message.created_at}
                                isLoading={message.isLoading}
                                isLatest={
                                  index ===
                                    sortedOptimisticMessages.length - 1 &&
                                  !message.isLoading
                                }
                              />
                            ))}
                          </div>
                        )}
                      </ScrollArea>

                      {/* Input Area */}
                      <motion.div
                        className="border-t bg-background/80 backdrop-blur-sm p-4 shadow-sm"
                        initial={{ y: 100 }}
                        animate={{ y: 0 }}
                        transition={{
                          type: "spring",
                          stiffness: 260,
                          damping: 20,
                        }}
                      >
                        <div className="max-w-5xl mx-auto w-full">
                          <ChatInput />
                        </div>
                      </motion.div>
                    </motion.div>
                  </AnimatePresence>

                  {/* Voice Mode Component */}
                  <VoiceMode
                    isActive={isVoiceModeActive}
                    onToggle={() => setIsVoiceModeActive(!isVoiceModeActive)}
                    onSendMessage={sendMessage}
                    latestAssistantMessage={latestAssistantMessage}
                    datasetId={params.datasetId}
                    isWaitingForResponse={isSending}
                  />
                </div>
              </ChatTabs>
            ) : (
              <div className="relative flex-1">
                <motion.div
                  className="absolute inset-0 flex flex-col items-center justify-center p-4 gap-6"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3, ease: "easeInOut" }}
                >
                  <div className="text-center space-y-3 mb-6">
                    <h1 className="text-3xl font-semibold text-foreground">
                      Welcome to GoPie Chat
                    </h1>
                    <p className="text-muted-foreground text-lg">
                      Start a conversation by typing a message below
                    </p>
                  </div>
                  <div className="w-full max-w-3xl px-4">
                    <ChatInput />
                  </div>
                </motion.div>

                {/* Voice Mode Component */}
                <VoiceMode
                  isActive={isVoiceModeActive}
                  onToggle={() => setIsVoiceModeActive(!isVoiceModeActive)}
                  onSendMessage={sendMessage}
                  latestAssistantMessage={latestAssistantMessage}
                  datasetId={params.datasetId}
                  isWaitingForResponse={isSending}
                />
              </div>
            )}
          </div>
        </ResizablePanel>
        {isOpen && (
          <>
            <ResizableHandle />
            <ResizablePanel defaultSize={70} minSize={30}>
              <SqlResults />
            </ResizablePanel>
          </>
        )}
      </ResizablePanelGroup>
    </div>
  );
}

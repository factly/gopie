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
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import { Send, MessageSquarePlus, Table2 } from "lucide-react";
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
import { ChatHistory } from "@/components/chat/chat-history";
import { useChatStore } from "@/lib/stores/chat-store";
import { AudioInput } from "@/components/chat/audio-input";
import { VoiceMode } from "@/components/chat/voice-mode";
import { VoiceModeToggle } from "@/components/chat/voice-mode-toggle";

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
  const inputRef = useRef<HTMLInputElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const { selectedChatId, setSelectedChatId } = useChatStore();
  const [isSending, setIsSending] = useState(false);
  const [optimisticMessages, setOptimisticMessages] = useState<
    OptimisticMessage[]
  >([]);
  const { isOpen, results, setIsOpen } = useSqlStore();
  const [isVoiceModeActive, setIsVoiceModeActive] = useState(false);
  const [latestAssistantMessage, setLatestAssistantMessage] = useState<
    string | null
  >(null);

  const [inputValue, setInputValue] = useState("");

  // Close sidebar only on initial mount
  useEffect(() => {
    setOpen(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Empty dependency array means it only runs once on mount

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

  // Track latest assistant message for voice mode
  useEffect(() => {
    // Wait a short delay to ensure message is fully received
    // This helps with state synchronization and timing
    const timer = setTimeout(() => {
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
    }, 500);

    return () => clearTimeout(timer);
  }, [allMessages]);

  // Clear latest assistant message when sending a new message
  // This ensures we don't process the same message repeatedly
  useEffect(() => {
    if (isSending) {
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
    if (!inputRef.current?.value && !inputValue) return;
    if (isSending) return;

    const message = inputRef.current?.value || inputValue;
    await sendMessage(message);
  };

  // Extracted send message logic for reuse in voice mode
  const sendMessage = async (message: string) => {
    if (!message || isSending) return;

    setIsSending(true);

    // Add optimistic user message
    const optimisticUserMessage: OptimisticMessage = {
      id: Date.now().toString(),
      content: message,
      role: "user",
      created_at: new Date().toISOString(),
    };
    setOptimisticMessages((prev) => [...prev, optimisticUserMessage]);

    // Add optimistic loading message for assistant
    const optimisticLoadingMessage: OptimisticMessage = {
      id: Date.now().toString() + "-loading",
      content: "",
      role: "assistant",
      created_at: new Date().toISOString(),
      isLoading: true,
    };
    setOptimisticMessages((prev) => [...prev, optimisticLoadingMessage]);

    // Clear input immediately
    if (inputRef.current) {
      inputRef.current.value = "";
    }
    setInputValue("");

    try {
      if (!selectedChatId) {
        const result = await createChat.mutateAsync({
          datasetId: params.datasetId,
          messages: [{ role: "user", content: message }],
        });
        setSelectedChatId(result.data.id);
      } else {
        await createChat.mutateAsync({
          chatId: selectedChatId,
          datasetId: params.datasetId,
          messages: [{ role: "user", content: message }],
        });
      }
      // Clear optimistic messages after successful response
      setOptimisticMessages([]);
      await refetchMessages();
    } catch {
      toast.error("Failed to send message");
      // Remove the loading message on error
      setOptimisticMessages((prev) => prev.slice(0, -1));
    } finally {
      setIsSending(false);
    }
  };

  const handleStartNewChat = () => {
    setSelectedChatId(null);
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

  const isEmpty = !allMessages.length && !optimisticMessages.length;

  const ChatInput = () => {
    return (
      <form onSubmit={handleSendMessage} className="flex gap-2">
        <Input
          ref={inputRef}
          placeholder="Type your message..."
          className="flex-1"
          disabled={isSending || isVoiceModeActive}
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
        />
        {!isVoiceModeActive && (
          <>
            <AudioInput
              onTranscriptionReceived={(text) => {
                setInputValue(text);
                setTimeout(() => {
                  const sendButton = document.getElementById(
                    "send-message-button"
                  ) as HTMLButtonElement;
                  if (sendButton) {
                    sendButton.click();
                    setInputValue("");
                  }
                }, 100);
              }}
              datasetId={params.datasetId}
            />
            <ChatHistory datasetId={params.datasetId} />
          </>
        )}
        <Button
          id="send-message-button"
          type="submit"
          disabled={isSending || isVoiceModeActive}
          size="icon"
        >
          {isSending ? (
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-background border-t-foreground" />
          ) : (
            <Send className="h-4 w-4" />
          )}
        </Button>
      </form>
    );
  };

  return (
    <div className="flex h-screen bg-background">
      <ResizablePanelGroup direction="horizontal">
        <ResizablePanel defaultSize={isOpen ? 40 : 100} minSize={30}>
          <div className="flex h-full flex-col">
            {/* Header */}
            <div className="border-b bg-background p-4 flex items-center justify-between">
              <h2 className="font-semibold">Chat</h2>
              <div className="flex items-center gap-2">
                {!isOpen && results && selectedChatId && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setIsOpen(true)}
                    className="gap-2"
                  >
                    <Table2 className="h-4 w-4" />
                    Show Results
                  </Button>
                )}
                <VoiceModeToggle
                  isActive={isVoiceModeActive}
                  onToggle={() => setIsVoiceModeActive(!isVoiceModeActive)}
                />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleStartNewChat}
                  className="gap-2"
                >
                  <MessageSquarePlus className="h-4 w-4" />
                  New Chat
                </Button>
              </div>
            </div>

            <div className="relative flex-1">
              <AnimatePresence mode="wait">
                {isEmpty ? (
                  <motion.div
                    className="absolute inset-0 flex flex-col items-center justify-center p-4 gap-4"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -20 }}
                    transition={{ duration: 0.3, ease: "easeInOut" }}
                  >
                    <div className="text-center space-y-2 mb-4">
                      <h1 className="text-2xl font-semibold">
                        Welcome to Gopie Chat
                      </h1>
                      <p className="text-muted-foreground">
                        Start a conversation by typing a message below
                      </p>
                    </div>
                    <div className="w-full max-w-2xl">
                      <ChatInput />
                    </div>
                  </motion.div>
                ) : (
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
                      className="flex-1 p-4"
                      onScroll={handleScroll}
                    >
                      {isLoadingMessages && !isFetchingNextPage ? (
                        <div className="space-y-4">
                          {Array.from({ length: 3 }).map((_, i) => (
                            <Skeleton key={i} className="h-20 w-full" />
                          ))}
                        </div>
                      ) : (
                        <div className="space-y-4">
                          {/* Loading more indicator */}
                          {isFetchingNextPage && (
                            <div className="flex justify-center py-2">
                              <span className="h-4 w-4 animate-spin rounded-full border-2 border-muted-foreground border-t-transparent" />
                            </div>
                          )}

                          {/* Real messages */}
                          {allMessages.map((message, index) => (
                            <ChatMessage
                              key={message.id}
                              id={message.id}
                              content={message.content}
                              role={message.role}
                              createdAt={message.created_at}
                              chatId={selectedChatId || undefined}
                              isLatest={
                                index === allMessages.length - 1 &&
                                !sortedOptimisticMessages.length
                              }
                              datasetId={params.datasetId}
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
                                index === sortedOptimisticMessages.length - 1 &&
                                !message.isLoading
                              }
                              datasetId={params.datasetId}
                            />
                          ))}
                        </div>
                      )}
                    </ScrollArea>

                    {/* Input Area */}
                    <motion.div
                      className="border-t bg-background p-4"
                      initial={{ y: 100 }}
                      animate={{ y: 0 }}
                      transition={{
                        type: "spring",
                        stiffness: 260,
                        damping: 20,
                      }}
                    >
                      <ChatInput />
                    </motion.div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </ResizablePanel>
        {isOpen && (
          <>
            <ResizableHandle />
            <ResizablePanel defaultSize={60} minSize={40}>
              <SqlResults />
            </ResizablePanel>
          </>
        )}
      </ResizablePanelGroup>

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
  );
}

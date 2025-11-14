"use client";

import React, { useEffect, useState, useMemo, useCallback, useRef } from "react";

// Constants
const TAB_RENDER_DELAY_MS = 50; // Delay to let tab content render before scrolling
import { useChatMessages } from "@/lib/queries/chat/get-messages";
import { useChatDetails } from "@/lib/queries/chat/get-chat";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { MessageSquarePlus, History, PanelLeft } from "lucide-react";
import { ResultsPanel } from "@/components/chat/results-panel";
import {
  ResizablePanel,
  ResizablePanelGroup,
  ResizableHandle,
} from "@/components/ui/resizable";
import { useSqlStore } from "@/lib/stores/sql-store";
import { useVisualizationStore } from "@/lib/stores/visualization-store";
import { Tabs, TabsContent } from "@/components/ui/tabs";
import { useChatStore } from "@/lib/stores/chat-store";
import { ShareChatDialog } from "@/components/chat/share-chat-dialog";
import { ReadOnlyMessage } from "@/components/chat/read-only-message";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useQueryClient } from "@tanstack/react-query";
import { useSidebar } from "@/components/ui/sidebar";
import { useAuthStore } from "@/lib/stores/auth-store";
import { useChatScroll } from "@/hooks/use-chat-scroll";
import { ChatHistoryList } from "@/components/chat/chat-history-list";

// Import new components and hooks
import { ChatInput } from "@/components/chat/chat-input";
import { ChatView } from "@/components/chat/chat-view";
import { EmptyChatView } from "@/components/chat/empty-chat-view";
import { useChatSession } from "@/hooks/use-chat-session";
import { useUrlSync } from "@/hooks/use-url-sync";
import { useContextManager } from "@/hooks/use-context-manager";
import { useMessageDisplay } from "@/hooks/use-message-display";
import { useChatInitialization } from "@/hooks/use-chat-initialization";
import { useHistoricalChatLoader } from "@/hooks/use-historical-chat-loader";
import { ChatSkeleton } from "@/components/chat/chat-skeleton";
import type { GoPieUIMessage } from "@/types/chat-message";

function ChatPageClient() {
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
  const {
    selectedChatId,
    selectedChatTitle,
    selectChatForDataset,
    setSelectedChatTitle,
  } = useChatStore();
  
  const {
    isOpen: sqlIsOpen,
    setIsOpen,
  } = useSqlStore();
  const {
    isOpen: isVisualizationOpen,
    setIsOpen: setVisualizationOpen,
  } = useVisualizationStore();

  const [linkedDatasetId, setLinkedDatasetId] = useState<string | null>(null);
  const [hasLoadedContextFromMessages, setHasLoadedContextFromMessages] = useState(false);
  const isNewChat = !selectedChatId;

  const sqlPanelRef = useRef<HTMLDivElement>(null);

  // Use URL sync hook
  const {
    updateUrlWithChatId,
    updateUrlWithContext,
    updateTabParam,
    chatIdFromUrl,
    initialMessage,
    contextData,
    contextsFromUrl,
    tabFromUrl,
  } = useUrlSync({ selectedChatId, isInitialized: true });

  const [activeTab, setActiveTab] = useState(
    tabFromUrl === "history" ? "history" : "chat"
  );

  // No need to track creating chat state anymore - handled inside hook

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
    refetchOnWindowFocus: false,
  });

  const allChatMessages = useMemo(() => {
    return (chatMessagesData?.pages.flatMap((page) => page.data) || []) as GoPieUIMessage[];
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

  // Use context manager hook
  const {
    selectedContexts,
    setSelectedContexts,
    handleSelectContext,
    handleRemoveContext,
    isInputFocused,
    setIsInputFocused,
  } = useContextManager({
    allChatMessages,
    hasLoadedContextFromMessages,
    setHasLoadedContextFromMessages,
    selectedChatId,
    isLoadingChatMessages,
    updateUrlWithContext,
    setLinkedDatasetId,
    contextsFromUrl,
    contextData,
  });

  // Use chat session hook with simplified logic
  const {
    streamingMessages,
    input,
    handleInputChange,
    handleSubmit: chatSessionHandleSubmit,
    isLoading,
    isStreaming,
    handleStop,
    showLoadingMessage,
    useStreamingMessages,
    streamingSessionBaselineRef,
    pendingUserMessage,
    isPreparingChat,
    chatId,
  } = useChatSession({
    selectedChatId,
    selectedContexts,
    updateUrlWithChatId,
    isNewChat,
  });

  // No need to sync creating chat states anymore

  // Use message display hook
  const { displayMessages } = useMessageDisplay({
    useStreamingMessages,
    streamingMessages,
    allChatMessages,
    selectedChatId,
    showLoadingMessage,
    streamingSessionBaselineRef,
    pendingUserMessage,
  });

  // Combined panel state - show if either SQL or visualizations are available
  const isResultsPanelOpen = sqlIsOpen || isVisualizationOpen;

  // Load and execute SQL/visualization for historical chats
  useHistoricalChatLoader({
    messages: allChatMessages,
    chatId: selectedChatId,
    isLoading: isLoadingChatMessages,
    enabled: !!selectedChatId && !isNewChat && allChatMessages.length > 0,
  });

  // Use custom scroll hook
  const {
    scrollRef,
    showScrollButton,
    scrollToBottom,
    resetScrollState,
  } = useChatScroll({
    messages: displayMessages,
    streamingMessages,
    isStreaming,
    showLoadingMessage,
    activeTab,
  });

  // Wrap handleSubmit to include resetScrollState
  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      chatSessionHandleSubmit(e, resetScrollState);
    },
    [chatSessionHandleSubmit, resetScrollState]
  );

  // Use chat initialization hook
  useChatInitialization({
    chatIdFromUrl,
    contextData,
    initialMessage,
    selectedContexts,
    setSelectedContexts,
    setLinkedDatasetId,
    handleInputChange,
    handleSubmit,
    isLoading,
    chatId,
    isPreparingChat,
  });

  // Log chat title state for debugging
  useEffect(() => {
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

  // Update chat title when chat details are loaded
  useEffect(() => {
    if (
      chatDetails &&
      selectedChatId &&
      chatDetails.id === selectedChatId &&
      chatDetails.title
    ) {
      selectChatForDataset(linkedDatasetId, selectedChatId, chatDetails.title);
    }
  }, [
    chatDetails,
    selectedChatId,
    linkedDatasetId,
    selectChatForDataset,
    setSelectedChatTitle,
  ]);

  // Handle chat details loading error
  useEffect(() => {
    if (chatDetailsError) {
      console.error("Error fetching chat details:", chatDetailsError);
      toast.error("Failed to load chat details");
    }
  }, [chatDetailsError]);

  // Handle chat messages loading error
  useEffect(() => {
    if (chatMessagesError) {
      console.error("Error fetching chat messages:", chatMessagesError);
      toast.error("Failed to load chat messages");
    }
  }, [chatMessagesError]);

  // Refresh chat details when chat ID changes
  useEffect(() => {
    if (selectedChatId) {
      queryClient.invalidateQueries({
        queryKey: ["chat-details", { chatId: selectedChatId }],
      });
    }
  }, [selectedChatId, queryClient]);

  // Function to reset scroll states
  const resetScrollStates = useCallback(() => {
    resetScrollState();
  }, [resetScrollState]);

  // Check if current user owns the chat
  const isCurrentUserOwner =
    !chatDetails || chatDetails.created_by === currentUserId;

  const isAuthDisabled =
    String(process.env.NEXT_PUBLIC_ENABLE_AUTH).trim() !== "true";

  // Close sidebar when chat page opens (only on mount)
  useEffect(() => {
    if (isMobile) {
      setOpenMobile(false);
    } else {
      setOpen(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
                  updateTabParam(value === "history" ? value : null);
                  // When switching to chat tab, trigger a scroll check
                  if (value === "chat" && selectedChatId) {
                    // Small delay to let the tab content render
                    setTimeout(() => {
                      if (scrollRef.current) {
                        const viewport = scrollRef.current.querySelector(
                          "[data-radix-scroll-area-viewport]"
                        ) as HTMLElement;
                        if (viewport) {
                          // Scroll to bottom for existing chat
                          viewport.scrollTo({
                            top: viewport.scrollHeight,
                            behavior: "auto",
                          });
                        }
                      }
                    }, TAB_RENDER_DELAY_MS);
                  }
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
                  <div className="flex-1"></div>
                  {(selectedChatId || chatId) && (
                    <>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Button
                            variant="ghost"
                            size="sm"
                            className={`mr-2 ${
                              activeTab === "history"
                                ? "bg-muted border-b-2 border-primary"
                                : ""
                            }`}
                            onClick={() => {
                              // Use window.location for a hard navigation to clear all state
                              window.location.href = "/chat?tab=history";
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
                              // Use window.location for a hard navigation to bypass all React state/effects
                              window.location.href = "/chat";
                            }}
                          >
                            <MessageSquarePlus className="h-4 w-4" />
                          </Button>
                        </TooltipTrigger>
                        <TooltipContent>
                          <p>New Chat</p>
                        </TooltipContent>
                      </Tooltip>
                      <ShareChatDialog
                        chatId={selectedChatId || chatId || ""}
                        currentVisibility={chatDetails?.visibility || "private"}
                      />
                    </>
                  )}
                </div>

                <TabsContent
                  value="chat"
                  className="flex-1 overflow-hidden flex flex-col data-[state=inactive]:hidden p-0 border-none min-h-0"
                >
                  {/* Show skeleton when loading historical chat messages or when preparing first message */}
                  {(isLoadingChatMessages && selectedChatId && displayMessages.length === 0) ||
                   (isPreparingChat && displayMessages.length === 0) ||
                   (pendingUserMessage && displayMessages.length === 0 && !useStreamingMessages) ? (
                    <ChatSkeleton />
                  ) : (
                    /* Show ChatView when we have any activity */
                    (displayMessages.length > 0 || pendingUserMessage || isLoading || useStreamingMessages || isStreaming) && (
                      <div className="flex flex-col h-full min-h-0 relative">
                        <ChatView
                          scrollRef={scrollRef}
                          isLoading={isLoading}
                          messages={displayMessages}
                          selectedChatId={selectedChatId || chatId}
                          isLoadingChatMessages={isLoadingChatMessages}
                          hasNextPage={hasNextPage}
                          fetchNextPage={fetchNextPage}
                          isFetchingNextPage={isFetchingNextPage}
                          showScrollButton={showScrollButton}
                          onScrollToBottom={scrollToBottom}
                          isWaitingForChatId={isPreparingChat}
                        />
                      </div>
                    )
                  )}
                </TabsContent>

                <TabsContent
                  value="history"
                  className="flex-1 overflow-hidden p-4 flex flex-col data-[state=inactive]:hidden border-none"
                >
                  <ChatHistoryList
                    currentUserId={currentUserId}
                    onTabChange={setActiveTab}
                    onContextChange={setSelectedContexts}
                    onLinkedDatasetChange={setLinkedDatasetId}
                    onUrlUpdate={updateUrlWithContext}
                    onScrollReset={resetScrollStates}
                  />
                </TabsContent>
              </Tabs>
              {activeTab === "chat" && (
                <>
                  {/* Show empty chat view only when truly empty - no activity at all and not loading */}
                  {displayMessages.length === 0 && !pendingUserMessage && !isLoading && !useStreamingMessages && !isStreaming && !isLoadingChatMessages && !isPreparingChat ? (
                    <EmptyChatView
                      selectedContexts={selectedContexts}
                      onSelectContext={handleSelectContext}
                      onRemoveContext={handleRemoveContext}
                      input={input}
                      handleInputChange={handleInputChange}
                      handleSubmit={handleSubmit}
                      isLoading={isLoading || isPreparingChat}
                      isStreaming={isStreaming}
                      handleStop={handleStop}
                      isInputFocused={isInputFocused}
                      setIsInputFocused={setIsInputFocused}
                    />
                  ) : (
                    <div className="absolute bottom-0 left-0 right-0 z-20">
                      {isCurrentUserOwner || isAuthDisabled ? (
                        <ChatInput
                          onStop={handleStop}
                          isStreaming={isStreaming}
                          selectedContexts={selectedContexts}
                          onSelectContext={handleSelectContext}
                          onRemoveContext={handleRemoveContext}
                          lockableContextIds={
                            selectedChatId && linkedDatasetId
                              ? [linkedDatasetId]
                              : []
                          }
                          hasContext={selectedContexts.length > 0}
                          input={input}
                          handleInputChange={handleInputChange}
                          handleSubmit={handleSubmit}
                          isLoading={isLoading || isPreparingChat}
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
              <ResizableHandle withHandle />
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
    </main>
  );
}

export default ChatPageClient;
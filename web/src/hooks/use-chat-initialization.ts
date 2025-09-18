import { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ContextItem } from "@/components/chat/context-picker";
import { useChatStore } from "@/lib/stores/chat-store";
import { useResultsPanelStore } from "@/lib/stores/results-panel-store";
import { useSqlStore } from "@/lib/stores/sql-store";
import { useVisualizationStore } from "@/lib/stores/visualization-store";

// Constants
const URL_CLEANUP_DELAY_MS = 500; // Delay before cleaning up URL parameters after initial message

interface UseChatInitializationProps {
  chatIdFromUrl: string | null;
  contextData: string | null;
  initialMessage: string | null;
  selectedContexts: ContextItem[];
  setSelectedContexts: (contexts: ContextItem[]) => void;
  setLinkedDatasetId: (id: string | null) => void;
  handleInputChange: (value: string) => void;
  handleSubmit: (e: React.FormEvent) => void;
  isLoading: boolean;
}

export function useChatInitialization({
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
}: UseChatInitializationProps & { chatId?: string | null; isPreparingChat?: boolean }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { selectedChatId, selectChatForDataset } = useChatStore();
  const { setActiveTab: setResultsPanelActiveTab } = useResultsPanelStore();
  const { resetExecutedQueries, setIsOpen } = useSqlStore();
  const { clearPaths: clearVisualizationPaths, setIsOpen: setVisualizationOpen } = useVisualizationStore();
  
  const [isInitialized, setIsInitialized] = useState(false);
  const [initialMessageSent, setInitialMessageSent] = useState(false);

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

  // Handle context data from URL
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
          // Open the SQL panel and set to SQL tab if we have an initial message to show the empty state
          if (initialMessage) {
            setIsOpen(true);
            setResultsPanelActiveTab("sql");
          } else {
            setIsOpen(false);
          }
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
  }, [
    contextData,
    resetExecutedQueries,
    clearVisualizationPaths,
    setIsOpen,
    setVisualizationOpen,
    selectChatForDataset,
    setLinkedDatasetId,
    setSelectedContexts,
    searchParams,
    router,
    setResultsPanelActiveTab,
    initialMessage,
  ]);

  // Handle initial message from URL params
  useEffect(() => {
    if (
      initialMessage &&
      !initialMessageSent &&
      selectedContexts.length > 0 &&
      isInitialized &&
      !isLoading && // Don't submit if already loading
      !isPreparingChat && // Wait for chat to be created
      (chatId || chatIdFromUrl) // Only proceed if we have a chat ID
    ) {
      // Decode the initial message from URL
      const decodedMessage = decodeURIComponent(initialMessage);

      // Set the input value
      handleInputChange(decodedMessage);

      // Mark as sent immediately to prevent double submission
      setInitialMessageSent(true);

      // Open SQL panel immediately when sending the initial message
      // This shows the empty state while the query is being processed
      setIsOpen(true);
      setResultsPanelActiveTab("sql");

      // Use requestAnimationFrame to ensure React has updated the DOM
      requestAnimationFrame(() => {
        // Another frame to ensure the input value is properly set
        requestAnimationFrame(() => {
          // Now submit the form
          const form = document.querySelector("form");
          if (form && form instanceof HTMLFormElement) {
            // Try using requestSubmit if available (modern browsers)
            if (
              "requestSubmit" in form &&
              typeof form.requestSubmit === "function"
            ) {
              form.requestSubmit();
            } else {
              // Fallback for older browsers
              const submitEvent = new Event("submit", {
                bubbles: true,
                cancelable: true,
              });
              form.dispatchEvent(submitEvent);
            }
          } else {
            // Direct fallback if form is not found
            const submitEvent = new Event("submit", {
              bubbles: true,
              cancelable: true,
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
      }, URL_CLEANUP_DELAY_MS);
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
    isPreparingChat,
    chatId,
    setIsOpen,
    chatIdFromUrl,
    setResultsPanelActiveTab,
  ]);

  // Clear results when switching chats
  useEffect(() => {
    resetExecutedQueries();
    clearVisualizationPaths();
  }, [selectedChatId, resetExecutedQueries, clearVisualizationPaths]);

  return { isInitialized };
}
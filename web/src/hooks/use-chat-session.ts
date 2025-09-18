import { useCallback, useEffect, useRef, useState } from "react";
import { useChat } from "@ai-sdk/react";
import { toast } from "sonner";
import { ContextItem } from "@/components/chat/context-picker";
import { useQueryClient } from "@tanstack/react-query";
import { useChatStore } from "@/lib/stores/chat-store";
import { DefaultChatTransport } from "ai";
import { useSqlStore } from "@/lib/stores/sql-store";
import { useVisualizationStore } from "@/lib/stores/visualization-store";
import { useCreateInitialChat } from "@/lib/mutations/chat/create-initial-chat";
import { useUpdateChatTitle } from "@/lib/mutations/chat/update-chat-title";
import { useDatasetSql } from "@/lib/mutations/dataset/sql";
import { parseSqlError } from "@/lib/sql-error-utils";
import { useResultsPanelStore } from "@/lib/stores/results-panel-store";
import type { GoPieUIMessage } from "@/types/chat-message";

// Constants
const QUERY_INVALIDATION_DELAY_MS = 100; // Delay before invalidating queries to ensure smooth transition

interface UseChatSessionProps {
  selectedChatId: string | null;
  selectedContexts: ContextItem[];
  updateUrlWithChatId: (chatId: string | null) => void;
  isNewChat?: boolean;
}

export function useChatSession({
  selectedChatId,
  selectedContexts,
  updateUrlWithChatId,
  isNewChat = false,
}: UseChatSessionProps) {
  const queryClient = useQueryClient();
  const { selectChatForDataset } = useChatStore();
  const { setIsOpen: setSqlPanelOpen, setResults: setSqlResults, setIsLoading: setSqlLoading, resetExecutedQueries } = useSqlStore();
  const { clearPaths, setPaths: setVisualizationPaths } = useVisualizationStore();
  const { setActiveTab } = useResultsPanelStore();
  const executeSql = useDatasetSql();
  const createInitialChatMutation = useCreateInitialChat();
  const updateChatTitleMutation = useUpdateChatTitle();
  const [isStreaming, setIsStreaming] = useState(false);
  const [showLoadingMessage, setShowLoadingMessage] = useState(false);
  const [useStreamingMessages, setUseStreamingMessages] = useState(false);
  const [pendingUserMessage, setPendingUserMessage] = useState<string | null>(null);
  const streamingSessionBaselineRef = useRef(0);
  const lastStreamingCountRef = useRef(0);

  // Track executed SQL queries to prevent duplicates
  const executedQueriesRef = useRef(new Set<string>());
  // Mutex to prevent concurrent SQL executions
  const sqlExecutionMutexRef = useRef<Map<string, Promise<void>>>(new Map());
  // Track if this is the first message in the chat
  const isFirstMessageRef = useRef(true);

  // Use a ref to store the current selectedContexts value
  const selectedContextsRef = useRef(selectedContexts);
  useEffect(() => {
    selectedContextsRef.current = selectedContexts;
  }, [selectedContexts]);

  // Chat ID management - simplified now that we create upfront
  const [chatId, setChatId] = useState<string | null>(selectedChatId);
  const [isPreparingChat, setIsPreparingChat] = useState(false);

  // Create a new chat when needed (for new chats)
  useEffect(() => {
    if (isNewChat && !selectedChatId && !chatId && !isPreparingChat && selectedContexts.length > 0) {
      setIsPreparingChat(true);

      // Clear any previous SQL results and visualizations when starting a new chat
      setSqlResults(null);
      clearPaths();
      resetExecutedQueries();
      // Open the SQL panel to show the empty state while loading
      setSqlPanelOpen(true);
      setActiveTab("sql");

      const projectIds = selectedContexts
        .filter((ctx) => ctx.type === "project")
        .map((ctx) => ctx.id);
      const datasetIds = selectedContexts
        .filter((ctx) => ctx.type === "dataset")
        .map((ctx) => ctx.id);

      // Store the pending message to use as title when user sends first message
      const pendingTitle = "New Chat";

      createInitialChatMutation.mutate(
        {
          title: pendingTitle, // Use placeholder title initially
          projectIds,
          datasetIds,
        },
        {
          onSuccess: (data) => {
            setChatId(data.id);

            // Update the store and URL
            const datasetContext = selectedContexts.find(
              (ctx) => ctx.type === "dataset"
            );
            selectChatForDataset(
              datasetContext?.id || null,
              data.id,
              data.title
            );
            updateUrlWithChatId(data.id);
            setIsPreparingChat(false);
          },
          onError: (error) => {
            console.error("Failed to create chat:", error);
            toast.error("Failed to create chat session");
            setIsPreparingChat(false);
          },
        }
      );
    }
  }, [isNewChat, selectedChatId, chatId, isPreparingChat, selectedContexts, createInitialChatMutation, selectChatForDataset, updateUrlWithChatId, resetExecutedQueries, clearPaths, setSqlResults, setSqlPanelOpen, setActiveTab]);

  // Update chat ID when selectedChatId changes
  useEffect(() => {
    if (selectedChatId) {
      setChatId(selectedChatId);
    }
  }, [selectedChatId]);

  // Manage input state manually (AI SDK v5 no longer manages it)
  const [input, setInput] = useState("");

  const chatResult = useChat<GoPieUIMessage>({
    transport: new DefaultChatTransport({
      api: "/api/chat",
      prepareSendMessagesRequest: ({ messages }) => {
        // Use the ref to get the current value of selectedContexts
        const currentContexts = selectedContextsRef.current;

        const projectIds = currentContexts
          .filter((ctx) => ctx.type === "project")
          .map((ctx) => ctx.id);
        const datasetIds = currentContexts
          .filter((ctx) => ctx.type === "dataset")
          .map((ctx) => ctx.id);

        return {
          body: {
            messages,
            project_ids: projectIds,
            dataset_ids: datasetIds,
            chat_id: chatId || undefined,  // Send chat ID if we have one
          },
        };
      },
    }),
    id: chatId || undefined,  // Use the real chat ID
    onData: ({ type, data }) => {
      // Handle transient data parts that arrive during streaming
      if (type === 'data-chat-created' && data) {
        const { chatId: newChatId } = data as { chatId: string };
        if (newChatId && !chatId) {
          setChatId(newChatId);
          const datasetContext = selectedContextsRef.current.find(
            (ctx) => ctx.type === "dataset"
          );
          selectChatForDataset(
            datasetContext?.id || null,
            newChatId,
            `Chat ${new Date().toLocaleTimeString()}`
          );
          updateUrlWithChatId(newChatId);
        }
      }

      // Handle SQL query data parts
      if (type === 'data-sql-query' && data) {
        const sqlData = data as { id: string; query: string; status: string };
        if (sqlData.status === 'pending' && sqlData.query) {
          // Check if we've already executed this query
          // Include chat ID and message ID in the key for better uniqueness
          const currentChatId = chatId || 'temp';
          const queryKey = `${currentChatId}-${sqlData.id}-${sqlData.query}`;

          // Check if this query is already being executed or has been executed
          if (!executedQueriesRef.current.has(queryKey) && !sqlExecutionMutexRef.current.has(queryKey)) {
            // Mark as executed immediately to prevent other calls
            executedQueriesRef.current.add(queryKey);

            // Create a promise for this execution to act as a mutex
            const executionPromise = (async () => {
              try {
                setSqlLoading(true);
                const result = await executeSql.mutateAsync({
                  query: sqlData.query,
                  limit: 20,
                  offset: 0,
                });
                setSqlResults({
                  data: result.data ?? [],
                  total: result.count ?? result.data?.length ?? 0,
                  columns: result.columns,
                  executionTime: result.executionTime,
                  query: sqlData.query,
                  chatId: chatId ?? undefined,
                });
                setSqlPanelOpen(true);
                setActiveTab("sql");
              } catch (error) {
                const errorDetails = parseSqlError(error);
                setSqlResults({
                  data: [],
                  total: 0,
                  error: errorDetails.message,
                  errorDetails,
                  query: sqlData.query,
                  chatId: chatId ?? undefined,
                });
                setSqlPanelOpen(true);
                setActiveTab("sql");
              } finally {
                setSqlLoading(false);
                // Clean up the mutex after execution completes
                sqlExecutionMutexRef.current.delete(queryKey);
              }
            })();

            // Store the promise in the mutex map
            sqlExecutionMutexRef.current.set(queryKey, executionPromise);

            // Execute the promise
            queueMicrotask(() => executionPromise);
          }
        }
      }

      // Handle visualization data parts
      if (type === 'data-visualization' && data) {
        const vizData = data as { paths: string[]; status: string };
        if (vizData.status === 'ready' && vizData.paths.length > 0) {
          setVisualizationPaths(vizData.paths, chatId ?? undefined);
          setActiveTab("visualizations");
        }
      }

      // Handle intermediate thoughts (now persistent)
      if (type === 'data-intermediate-thought' && data) {
        // These are now persistent and will be available in message.parts
        // The message component will pick them up from there
      }

      // Handle status notifications (transient)
      if (type === 'data-status-notification' && data) {
        const notification = data as { message: string; level: string };
        if (notification.level === 'error') {
          toast.error(notification.message);
        } else if (notification.level === 'warning') {
          toast.warning(notification.message);
        } else if (notification.level === 'success') {
          toast.success(notification.message);
        } else {
          toast(notification.message);
        }
      }
    },
    onFinish: ({ message }) => {
      if (message && message.role === "assistant") {
        setIsStreaming(false);
        setShowLoadingMessage(false);
        // Keep useStreamingMessages true so we continue showing the streamed messages
        // Don't set it to false here - let the message display hook handle it
      }

      // Don't clear executed queries here - they should persist until the next message is sent
      // This prevents duplicate SQL execution if the same data part comes through again

      // Try to sync with backend after a delay to ensure data is persisted
      setTimeout(() => {
        // Always invalidate chats to update the list
        queryClient.invalidateQueries({ queryKey: ["chats"] });

        // Don't automatically switch away from streaming messages
        // Let the UI continue showing streaming messages until backend is ready
        // The switch will happen naturally when allChatMessages updates via React Query
      }, QUERY_INVALIDATION_DELAY_MS);
    },
    onError: (err) => {
      console.error("Chat error:", err);
      toast.error("Error processing chat: " + (err.message || "Unknown error"));
      setUseStreamingMessages(false);
      setIsStreaming(false);
      setShowLoadingMessage(false);
    },
  });

  const { messages: streamingMessages, sendMessage, status, stop, error } = chatResult;

  // Handle streaming state based on status
  useEffect(() => {
    if (status === "streaming") {
      setUseStreamingMessages(true);
      setIsStreaming(true);
      setShowLoadingMessage(false);
      setPendingUserMessage(null);

      // Update last streaming count to track new messages
      if (streamingMessages.length > lastStreamingCountRef.current) {
        lastStreamingCountRef.current = streamingMessages.length;
      }
    }
  }, [status, streamingMessages.length]);

  // Clear pending user message once it appears in streaming messages
  useEffect(() => {
    if (pendingUserMessage && streamingMessages.length > 0) {
      // Check if the pending message is now in streaming messages
      const pendingInStreaming = streamingMessages.some(msg =>
        msg.role === "user" &&
        msg.parts?.[0]?.type === "text" &&
        (msg.parts[0] as { text?: string }).text === pendingUserMessage
      );
      if (pendingInStreaming) {
        setPendingUserMessage(null);
      }
    }
  }, [streamingMessages, pendingUserMessage]);

  // Display any errors in the UI
  useEffect(() => {
    if (error) {
      console.error("Chat error state:", error);
      toast.error(`Error: ${error.message || "Unknown error"}`);
    }
  }, [error]);

  // Update streaming state based on status
  const isLoading = status === "submitted" || status === "streaming";

  // Custom input handler that works with MentionInput component
  const handleInputChange = useCallback(
    (value: string) => {
      setInput(value);
    },
    []
  );

  // Custom submit handler that works with MentionInput component
  const handleSubmit = useCallback(
    async (e: React.FormEvent, resetScrollState?: () => void) => {
      e.preventDefault();

      if (selectedContexts.length === 0) {
        toast.error(
          "Please select at least one project or dataset before sending a message"
        );
        return;
      }

      if (input?.trim()) {
        // If we don't have a chat ID yet, we need to wait for it
        if (!chatId) {
          toast.error("Please wait for chat to initialize");
          return;
        }

        // Store the user message optimistically for immediate display
        setPendingUserMessage(input);

        // If this is the first message, update the chat title
        if (isFirstMessageRef.current && chatId) {
          // Update the chat title with the user's first message
          // Truncate to a reasonable length for the title
          const newTitle = input.length > 100 ? input.substring(0, 100) + '...' : input;

          // Update the title in the local store immediately for better UX
          const datasetContext = selectedContextsRef.current.find(
            (ctx) => ctx.type === "dataset"
          );
          selectChatForDataset(
            datasetContext?.id || null,
            chatId,
            newTitle
          );

          // Update the title on the backend
          updateChatTitleMutation.mutate(
            {
              chatId,
              title: newTitle,
            },
            {
              onSuccess: () => {
                // Invalidate the chats query to refresh the chat list
                queryClient.invalidateQueries({ queryKey: ["chats"] });
              },
              onError: (error) => {
                console.error("Failed to update chat title:", error);
                // The local update stays even if the backend update fails
              },
            }
          );

          isFirstMessageRef.current = false;
        }

        // Track the current streaming message count to detect new messages
        lastStreamingCountRef.current = streamingMessages.length;
        // Store baseline for this session (not used for duplicate detection anymore)
        streamingSessionBaselineRef.current = streamingMessages.length;
        // Immediately switch to streaming mode
        setUseStreamingMessages(true);
        setIsStreaming(false); // Not streaming yet, just sending
        setShowLoadingMessage(false); // Don't show loading message, we have pending user message

        // Clear executed queries and mutex for the new message
        executedQueriesRef.current.clear();
        sqlExecutionMutexRef.current.clear();

        // Reset SQL results and visualizations when sending a new message
        setSqlResults(null);
        clearPaths();

        // Always open the SQL panel and set to SQL tab when sending messages
        setSqlPanelOpen(true);
        setActiveTab("sql");

        if (resetScrollState) {
          resetScrollState();
        }

        // Send message using the new API
        // Note: AI SDK v5 will add the user message to streamingMessages when server responds
        // Don't pass chat_id separately in body - it's already in prepareSendMessagesRequest
        sendMessage({ text: input });
        setInput(""); // Clear input after sending
      }
    },
    [sendMessage, selectedContexts, input, streamingMessages.length, chatId, setSqlResults, clearPaths, setSqlPanelOpen, queryClient, selectChatForDataset, setActiveTab, updateChatTitleMutation]
  );

  // Handle stopping the stream
  const handleStop = useCallback(() => {
    stop();
    setIsStreaming(false);
  }, [stop]);

  // Reset streaming and states when switching chats
  useEffect(() => {
    // Reset when switching to a different chat
    if (streamingMessages.length === 0) {
      setUseStreamingMessages(false);
      setShowLoadingMessage(false);
      setIsStreaming(false);
      streamingSessionBaselineRef.current = 0;
      setInput(""); // Clear input when switching chats
      executedQueriesRef.current.clear(); // Clear executed queries
      sqlExecutionMutexRef.current.clear(); // Clear mutex map
      isFirstMessageRef.current = true; // Reset first message flag when switching chats
    }
  }, [selectedChatId, streamingMessages.length]);

  return {
    streamingMessages,
    input,
    handleInputChange,
    handleSubmit,
    isLoading,
    isStreaming,
    handleStop,
    showLoadingMessage,
    useStreamingMessages,
    streamingSessionBaselineRef,
    pendingUserMessage,
    isPreparingChat,
    chatId,
  };
}
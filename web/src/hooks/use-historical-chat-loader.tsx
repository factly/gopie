import { useEffect, useRef } from "react";
import { useSqlStore } from "@/lib/stores/sql-store";
import { useVisualizationStore } from "@/lib/stores/visualization-store";
import { useResultsPanelStore } from "@/lib/stores/results-panel-store";
import { useDatasetSql } from "@/lib/mutations/dataset/sql";
import { parseSqlError } from "@/lib/sql-error-utils";
import { processMessageParts } from "@/lib/utils/message-processing";
import type { GoPieUIMessage } from "@/types/chat-message";

interface UseHistoricalChatLoaderOptions {
  messages: GoPieUIMessage[];
  chatId: string | null;
  isLoading: boolean;
  enabled?: boolean;
}

export function useHistoricalChatLoader({
  messages,
  chatId,
  isLoading,
  enabled = true,
}: UseHistoricalChatLoaderOptions) {
  const executeSql = useDatasetSql();
  const {
    setResults: setSqlResults,
    setIsOpen: setSqlPanelOpen,
    setIsLoading: setSqlLoading,
    resetPagination,
    setOnPageChange
  } = useSqlStore();
  const { setPaths: setVisualizationPaths, setIsOpen: setVisualizationOpen } = useVisualizationStore();
  const { setActiveTab } = useResultsPanelStore();

  // Track if we've already executed for this chat
  const executedChatRef = useRef<string | null>(null);
  const isExecutingRef = useRef(false);

  useEffect(() => {
    // Skip if not enabled, still loading, no chat ID, or no messages
    if (!enabled || isLoading || !chatId || messages.length === 0) {
      return;
    }

    // Skip if we've already executed for this chat
    if (executedChatRef.current === chatId || isExecutingRef.current) {
      return;
    }

    // Find the last assistant message with SQL or visualization
    let lastSqlQuery: string | null = null;
    let lastVisualizationPaths: string[] = [];

    // Iterate through messages in reverse to find the most recent SQL/visualization
    for (let i = messages.length - 1; i >= 0; i--) {
      const message = messages[i];

      // Only process assistant messages
      if (message.role !== "assistant") {
        continue;
      }

      // Process message parts to extract SQL and visualizations
      if (message.parts) {
        const processed = processMessageParts(message.parts);

        // Get the last SQL query if we haven't found one yet
        if (!lastSqlQuery && processed.sqlQueries.length > 0) {
          lastSqlQuery = processed.sqlQueries[processed.sqlQueries.length - 1];
        }

        // Get visualization paths if we haven't found any yet
        if (lastVisualizationPaths.length === 0 && processed.visualizationResults.length > 0) {
          lastVisualizationPaths = processed.visualizationResults;
        }

        // If we've found both, we can stop searching
        if (lastSqlQuery && lastVisualizationPaths.length > 0) {
          break;
        }
      }
    }

    // Mark this chat as executed
    executedChatRef.current = chatId;
    isExecutingRef.current = true;

    // Show the results panel immediately if we have SQL or visualizations
    if (lastSqlQuery || lastVisualizationPaths.length > 0) {
      // Open the appropriate panel
      if (lastSqlQuery) {
        setSqlPanelOpen(true);
        setActiveTab("sql");
      } else if (lastVisualizationPaths.length > 0) {
        setVisualizationOpen(true);
        setActiveTab("visualizations");
      }
    }

    // Execute the last SQL query if found
    if (lastSqlQuery) {
      // Reset pagination for the new query
      resetPagination();

      const executeQuery = async (query: string, page: number = 1, limit: number = 20) => {
        const offset = (page - 1) * limit;
        setSqlLoading(true);

        try {
          const result = await executeSql.mutateAsync({
            query,
            limit,
            offset,
          });

          setSqlResults({
            data: result.data ?? [],
            total: result.count ?? result.data?.length ?? 0,
            columns: result.columns,
            executionTime: result.executionTime,
            query,
            chatId: chatId || undefined,
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
            query,
            chatId: chatId || undefined,
          });
          setSqlPanelOpen(true);
          setActiveTab("sql");
        } finally {
          setSqlLoading(false);
          isExecutingRef.current = false;
        }
      };

      // Set up pagination callback
      setOnPageChange((page: number, limit: number) => {
        executeQuery(lastSqlQuery, page, limit);
      });

      // Execute the query asynchronously
      queueMicrotask(() => executeQuery(lastSqlQuery, 1, 20));
    } else {
      isExecutingRef.current = false;
    }

    // Set visualization paths if found
    if (lastVisualizationPaths.length > 0) {
      setVisualizationPaths(lastVisualizationPaths, chatId || undefined);
      if (!lastSqlQuery) {
        // Only switch to visualizations tab if there's no SQL
        setVisualizationOpen(true);
        setActiveTab("visualizations");
      }
    }
  }, [
    messages,
    chatId,
    isLoading,
    enabled,
    executeSql,
    setSqlResults,
    setSqlPanelOpen,
    setSqlLoading,
    resetPagination,
    setOnPageChange,
    setVisualizationPaths,
    setVisualizationOpen,
    setActiveTab
  ]);

  // Reset when chat changes
  useEffect(() => {
    if (chatId !== executedChatRef.current) {
      executedChatRef.current = null;
      isExecutingRef.current = false;
    }
  }, [chatId]);
}
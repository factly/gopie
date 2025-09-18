import { useState, useCallback, useEffect } from "react";
import { ContextItem } from "@/components/chat/context-picker";
import { apiClient } from "@/lib/api-client";
import { UIMessage } from "ai";

// Type definitions for tool invocations
interface ToolInvocationPart {
  type: "tool-invocation";
  toolInvocation: {
    toolName: string;
    args: {
      project_ids?: string[];
      dataset_ids?: string[];
    };
  };
}

interface SetContextToolInvocation extends ToolInvocationPart {
  toolInvocation: {
    toolName: "set_context";
    args: {
      project_ids?: string[];
      dataset_ids?: string[];
    };
  };
}

interface UseContextManagerProps {
  allChatMessages: UIMessage[];
  hasLoadedContextFromMessages: boolean;
  setHasLoadedContextFromMessages: (loaded: boolean) => void;
  selectedChatId: string | null;
  isLoadingChatMessages: boolean;
  updateUrlWithContext: (contexts: ContextItem[]) => void;
  setLinkedDatasetId: (id: string | null) => void;
  contextsFromUrl: string | null;
  contextData: string | null;
}

export function useContextManager({
  allChatMessages,
  hasLoadedContextFromMessages,
  setHasLoadedContextFromMessages,
  selectedChatId,
  isLoadingChatMessages,
  updateUrlWithContext,
  setLinkedDatasetId,
  contextsFromUrl,
  contextData,
}: UseContextManagerProps) {
  const [selectedContexts, setSelectedContexts] = useState<ContextItem[]>([]);
  const [contextInitialized, setContextInitialized] = useState(false);
  const [isInputFocused, setIsInputFocused] = useState(false);

  // Extract context from the last user message when chat messages are loaded
  useEffect(() => {
    if (
      allChatMessages.length > 0 &&
      !hasLoadedContextFromMessages &&
      selectedChatId &&
      !isLoadingChatMessages
    ) {
      // Find the last user message
      const lastUserMessage = [...allChatMessages]
        .reverse()
        .find((msg) => msg.role === "user");

      if (lastUserMessage?.parts) {
        // Look for set_context tool invocation in the message parts
        let contextArgs: {
          project_ids?: string[];
          dataset_ids?: string[];
        } | null = null;

        for (const part of lastUserMessage.parts) {
          // Check if this is a tool invocation part
          if (typeof part === "object" && part && "type" in part && part.type === "tool-invocation" && "toolInvocation" in part) {
            const toolPart = part as unknown as ToolInvocationPart;

            if (toolPart.toolInvocation?.toolName === "set_context") {
              contextArgs = (toolPart as SetContextToolInvocation).toolInvocation.args;
              break;
            }
          }
        }

        if (contextArgs) {
          const args = contextArgs;
          const newContexts: ContextItem[] = [];

          // Fetch actual names for projects and datasets using Promise.allSettled for better error resilience
          const fetchContextDetails = async () => {
            try {
              // Prepare promises for fetching project details
              const projectPromises = (args.project_ids || []).map(async (projectId) => {
                try {
                  const response = await apiClient.get(`v1/api/projects/${projectId}`);
                  const project = (await response.json()) as { name?: string };
                  return {
                    id: projectId,
                    type: "project" as const,
                    name: project.name || "Project",
                    projectId: projectId,
                  };
                } catch (error) {
                  console.warn(`Failed to fetch project ${projectId}:`, error);
                  return {
                    id: projectId,
                    type: "project" as const,
                    name: "Project",
                    projectId: projectId,
                  };
                }
              });

              // Prepare promises for fetching dataset details
              const datasetPromises = (args.dataset_ids || []).map(async (datasetId) => {
                try {
                  const response = await apiClient.get(`v1/api/datasets/${datasetId}`);
                  const dataset = (await response.json()) as { alias?: string; name?: string };
                  const projectId = args.project_ids?.[0] || undefined;
                  return {
                    id: datasetId,
                    type: "dataset" as const,
                    name: dataset.alias || dataset.name || "Dataset",
                    projectId: projectId,
                  };
                } catch (error) {
                  console.warn(`Failed to fetch dataset ${datasetId}:`, error);
                  const projectId = args.project_ids?.[0] || undefined;
                  return {
                    id: datasetId,
                    type: "dataset" as const,
                    name: "Dataset",
                    projectId: projectId,
                  };
                }
              });

              // Use Promise.allSettled to handle partial failures gracefully
              const allPromises = [...projectPromises, ...datasetPromises];
              const results = await Promise.allSettled(allPromises);
              
              // Extract successful results
              results.forEach((result) => {
                if (result.status === "fulfilled") {
                  newContexts.push(result.value as ContextItem);
                }
              });

              if (newContexts.length > 0) {
                console.log(
                  "Loading context from last user message:",
                  newContexts
                );
                setSelectedContexts(newContexts);
                updateUrlWithContext(newContexts);

                // Set linked dataset if there's a dataset context
                const datasetContext = newContexts.find(
                  (ctx) => ctx.type === "dataset"
                );
                if (datasetContext) {
                  setLinkedDatasetId(datasetContext.id);
                }
              }
            } catch (error) {
              console.error("Error fetching context details:", error);
            }
          };

          // Execute the async function
          fetchContextDetails();
        }
      }

      // Mark that we've attempted to load context from messages
      setHasLoadedContextFromMessages(true);
    }
  }, [
    allChatMessages,
    hasLoadedContextFromMessages,
    selectedChatId,
    isLoadingChatMessages,
    updateUrlWithContext,
    setLinkedDatasetId,
    setHasLoadedContextFromMessages,
  ]);

  // Initialize contexts from URL on first load
  useEffect(() => {
    if (!contextInitialized && contextsFromUrl && !contextData) {
      try {
        const parsedContexts = JSON.parse(
          decodeURIComponent(contextsFromUrl)
        ) as ContextItem[];
        if (Array.isArray(parsedContexts) && parsedContexts.length > 0) {
          setSelectedContexts(parsedContexts);

          // Set linked dataset if there's a dataset context
          const datasetContext = parsedContexts.find(
            (ctx) => ctx.type === "dataset"
          );
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
  }, [contextsFromUrl, contextData, contextInitialized, setLinkedDatasetId]);

  const handleSelectContext = useCallback(
    (context: ContextItem) => {
      setSelectedContexts((prev) => {
        const newContexts = [...prev, context];
        // Schedule URL update after state update to avoid calling setState during render
        setTimeout(() => {
          updateUrlWithContext(newContexts);
        }, 0);
        return newContexts;
      });
      // Stop flashing when context is selected
      setIsInputFocused(false);
    },
    [updateUrlWithContext]
  );

  const handleRemoveContext = useCallback(
    (contextId: string) => {
      setSelectedContexts((prev) => {
        const newContexts = prev.filter((c) => c.id !== contextId);
        // Schedule URL update after state update to avoid calling setState during render
        setTimeout(() => {
          updateUrlWithContext(newContexts);
        }, 0);
        return newContexts;
      });
    },
    [updateUrlWithContext]
  );

  // Reset context loading flag when switching chats
  useEffect(() => {
    setHasLoadedContextFromMessages(false);
  }, [selectedChatId, setHasLoadedContextFromMessages]);

  return {
    selectedContexts,
    setSelectedContexts,
    handleSelectContext,
    handleRemoveContext,
    isInputFocused,
    setIsInputFocused,
  };
}
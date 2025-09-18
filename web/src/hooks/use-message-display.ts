import { useMemo, MutableRefObject } from "react";
import { UIMessage } from "ai";

interface UseMessageDisplayProps {
  useStreamingMessages: boolean;
  streamingMessages: UIMessage[];
  allChatMessages: UIMessage[];
  selectedChatId: string | null;
  showLoadingMessage: boolean;
  streamingSessionBaselineRef: MutableRefObject<number>;
  pendingUserMessage?: string | null;
}

export function useMessageDisplay({
  useStreamingMessages,
  streamingMessages,
  allChatMessages,
  selectedChatId: _selectedChatId,
  showLoadingMessage: _showLoadingMessage,
  streamingSessionBaselineRef: _streamingSessionBaselineRef,
  pendingUserMessage,
}: UseMessageDisplayProps) {
  const displayMessages = useMemo(() => {
    let messages: UIMessage[] = [];

    // Determine which messages to display based on current state
    if (allChatMessages.length > 0) {
      // If we have backend messages, prefer those as the source of truth
      if (useStreamingMessages && streamingMessages.length > allChatMessages.length) {
        // Only show streaming messages if there are MORE than backend (new messages being streamed)
        // Create a set of backend message IDs for efficient lookup
        const backendMessageIds = new Set(allChatMessages.map(msg => msg.id));

        // Filter streaming messages to only include those NOT in backend
        const newStreamingMessages = streamingMessages.filter(
          msg => !backendMessageIds.has(msg.id)
        );

        // Only combine if there are actually new messages
        if (newStreamingMessages.length > 0) {
          messages = [...allChatMessages, ...newStreamingMessages];
        } else {
          // No new messages, just show backend
          messages = allChatMessages;
        }
      } else {
        // Not actively streaming or no new messages - just show backend messages
        messages = allChatMessages;
      }
    } else if (streamingMessages.length > 0) {
      // No backend messages yet - show streaming messages as fallback
      messages = streamingMessages;
    }
    // If both are empty, messages stays as empty array

    // Add pending user message if it exists and not already in streaming messages
    // This handles the brief moment before AI SDK adds the user message
    if (pendingUserMessage && useStreamingMessages) {
      // Check if the pending message is already in streaming messages
      const pendingInStreaming = streamingMessages.some(msg =>
        msg.role === "user" &&
        msg.parts?.[0]?.type === "text" &&
        (msg.parts[0] as { text?: string }).text === pendingUserMessage
      );

      if (!pendingInStreaming) {
        // Create the pending message
        const pendingMsg: UIMessage = {
          id: "pending-" + Date.now(),
          role: "user" as const,
          createdAt: new Date(),
          parts: [{ type: "text" as const, text: pendingUserMessage }],
        } as UIMessage;

        // Append the pending message to existing messages
        messages = [...messages, pendingMsg];
      }
    }

    // Don't add loading message - let the actual streaming content appear

    return messages;
  }, [
    useStreamingMessages,
    streamingMessages,
    allChatMessages,
    pendingUserMessage,
  ]);

  return { displayMessages };
}
import { apiClient } from "@/lib/api-client";
import { UIMessage } from "ai";
import { createInfiniteQuery } from "react-query-kit";

interface GetMessagesVariables {
  chatId: string;
  limit?: number;
  page?: number;
}

interface ChoiceDelta {
  content: string | null;
  function_call: Record<string, unknown> | null;
  refusal: string | null;
  role: "user" | "assistant" | "system" | "intermediate" | null;
  tool_calls: Array<{
    index: number;
    id: string;
    function: {
      arguments: string;
      name: string;
    };
    type: string;
  }> | null;
}

interface Choice {
  delta: ChoiceDelta;
  finish_reason: string | null;
  index: number;
  logprobs: Record<string, unknown> | null;
}

interface MessageChunk {
  id: string;
  chat_id: string;
  created_at: string;
  model: string;
  object: "user.message" | "chat.completion.chunk";
  choices: Choice[];
}

interface MessagesResponse {
  data: MessageChunk[];
}

// Function to transform OpenAI format chunks to UIMessage format
function transformChunksToMessages(chunks: MessageChunk[]): UIMessage[] {
  const messages: UIMessage[] = [];

  // Sort chunks by created_at to ensure proper order
  const sortedChunks = chunks.sort(
    (a, b) =>
      new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
  );

  let currentAssistantMessage: {
    id: string;
    textContent: string;
    streamingContent: string;
    createdAt: Date;
    toolInvocations: Array<{
      state: string;
      step: number;
      toolCallId: string;
      toolName: string;
      args: Record<string, unknown>;
      result: {
        type: string;
        toolCallId: string;
        toolName: string;
        args: Record<string, unknown>;
      };
    }>;
    parts: Array<Record<string, unknown>>;
  } | null = null;

  for (const chunk of sortedChunks) {
    if (!chunk.choices || chunk.choices.length === 0) continue;

    const choice = chunk.choices[0];
    const delta = choice.delta;

    // Handle user messages - these are complete messages
    if (
      chunk.object === "user.message" &&
      delta.role === "user" &&
      delta.content
    ) {
      // Finalize any pending assistant message before adding user message
      if (currentAssistantMessage) {
        finalizeAssistantMessage(currentAssistantMessage, messages);
        currentAssistantMessage = null;
      }

      messages.push({
        id: chunk.id,
        role: "user",
        content: delta.content,
        createdAt: new Date(chunk.created_at),
        parts: [
          {
            type: "text",
            text: delta.content,
          },
        ],
      } as UIMessage);
      continue;
    }

    // Handle chat completion chunks - these need to be aggregated
    if (chunk.object === "chat.completion.chunk") {
      // Initialize assistant message if not already started
      if (!currentAssistantMessage) {
        currentAssistantMessage = {
          id: chunk.id, // Use first chunk's ID as the message ID
          textContent: "",
          streamingContent: "",
          createdAt: new Date(chunk.created_at),
          toolInvocations: [],
          parts: [{ type: "step-start" }],
        };
      }

      // Handle final assistant message (the one with role "assistant")
      if (delta.role === "assistant" && delta.content) {
        // This is the final message with complete content
        currentAssistantMessage.textContent = delta.content;
        continue;
      }

      // Handle tool calls
      if (delta.tool_calls) {
        for (const toolCall of delta.tool_calls) {
          try {
            const args = JSON.parse(toolCall.function.arguments);

            const toolInvocation = {
              state: "result",
              step: 0,
              toolCallId: toolCall.id,
              toolName: toolCall.function.name,
              args: args,
              result: {
                type: "tool-call",
                toolCallId: toolCall.function.name,
                toolName: toolCall.function.name,
                args: args,
              },
            };

            currentAssistantMessage.toolInvocations.push(toolInvocation);

            // Add tool invocation to parts
            currentAssistantMessage.parts.push({
              type: "tool-invocation",
              toolInvocation: toolInvocation,
            });
          } catch (error) {
            console.warn("Failed to parse tool call arguments:", error);
          }
        }
      }

      // Handle content chunks (streaming assistant response)
      if (delta.content && !delta.role) {
        // Append content to the streaming content
        currentAssistantMessage.streamingContent += delta.content;
      }
    }
  }

  // Finalize any remaining assistant message
  if (currentAssistantMessage) {
    finalizeAssistantMessage(currentAssistantMessage, messages);
  }

  return messages;
}

function finalizeAssistantMessage(
  assistantMessage: {
    id: string;
    textContent: string;
    streamingContent: string;
    createdAt: Date;
    toolInvocations: Array<{
      state: string;
      step: number;
      toolCallId: string;
      toolName: string;
      args: Record<string, unknown>;
      result: {
        type: string;
        toolCallId: string;
        toolName: string;
        args: Record<string, unknown>;
      };
    }>;
    parts: Array<Record<string, unknown>>;
  },
  messages: UIMessage[]
) {
  // Combine final text content and streaming content
  let finalContent = assistantMessage.textContent;
  if (assistantMessage.streamingContent) {
    // If we have streaming content, combine it with the final content
    finalContent =
      assistantMessage.textContent + assistantMessage.streamingContent;
  }

  // Add text part if we have content
  if (finalContent) {
    assistantMessage.parts.push({
      type: "text",
      text: finalContent,
    });
  }

  messages.push({
    id: assistantMessage.id,
    role: "assistant",
    content: finalContent,
    createdAt: assistantMessage.createdAt,
    parts: assistantMessage.parts,
    toolInvocations: assistantMessage.toolInvocations,
  } as UIMessage);
}

async function fetchMessages(
  { chatId, limit }: GetMessagesVariables,
  context: { pageParam: number }
): Promise<{ data: UIMessage[] }> {
  try {
    const searchParams = new URLSearchParams({
      limit: (limit || 10).toString(),
      page: context.pageParam.toString(),
    });

    const response = await apiClient.get(
      `v1/api/chat/${chatId}/messages?${searchParams}`
    );

    const messagesResponse: MessagesResponse = await response.json();

    // Transform the OpenAI format to UIMessage format
    const transformedMessages = transformChunksToMessages(
      messagesResponse.data
    );
    console.log("transformedMessages", transformedMessages);

    return { data: transformedMessages };
  } catch (error) {
    throw new Error("Failed to fetch chat messages: " + error);
  }
}

export const useChatMessages = createInfiniteQuery<
  { data: UIMessage[] },
  GetMessagesVariables,
  Error,
  number
>({
  queryKey: ["chat-messages"],
  fetcher: fetchMessages,
  initialPageParam: 1,
  getNextPageParam: (lastPage, allPages) => {
    const totalPages = Math.ceil(lastPage.data.length / 10);
    const nextPage = allPages.length + 1;
    return nextPage <= totalPages ? nextPage : undefined;
  },
});

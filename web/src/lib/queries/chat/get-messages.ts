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
      const parts: Array<Record<string, unknown>> = [
        {
          type: "text",
          text: delta.content,
        },
      ];

      // Check if user message has tool calls (like set_context)
      if (delta.tool_calls && delta.tool_calls.length > 0) {
        for (const toolCall of delta.tool_calls) {
          try {
            const args = JSON.parse(toolCall.function.arguments);
            
            // Add tool invocation to parts
            parts.push({
              type: "tool-invocation",
              toolInvocation: {
                state: "result",
                toolCallId: toolCall.id,
                toolName: toolCall.function.name,
                args: args,
                result: {
                  type: "tool-call",
                  toolCallId: toolCall.id,
                  toolName: toolCall.function.name,
                  args: args,
                },
              },
            });
          } catch (error) {
            console.warn("Failed to parse user tool call arguments:", error);
          }
        }
      }

      messages.push({
        id: chunk.id,
        role: "user",
        content: delta.content,
        createdAt: new Date(chunk.created_at),
        parts: parts,
      } as UIMessage);
      continue;
    }

    // Handle assistant messages - these are now complete messages
    if (
      chunk.object === "chat.completion.chunk" &&
      delta.role === "assistant" &&
      delta.content
    ) {
      const toolInvocations: Array<{
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
      }> = [];

      const parts: Array<Record<string, unknown>> = [{ type: "step-start" }];

      // Process tool calls if they exist
      if (delta.tool_calls && delta.tool_calls.length > 0) {
        for (let i = 0; i < delta.tool_calls.length; i++) {
          const toolCall = delta.tool_calls[i];
          try {
            const args = JSON.parse(toolCall.function.arguments);

            const toolInvocation = {
              state: "result",
              step: i,
              toolCallId: toolCall.id,
              toolName: toolCall.function.name,
              args: args,
              result: {
                type: "tool-call",
                toolCallId: toolCall.id,
                toolName: toolCall.function.name,
                args: args,
              },
            };

            toolInvocations.push(toolInvocation);

            // Add tool invocation to parts
            parts.push({
              type: "tool-invocation",
              toolInvocation: toolInvocation,
            });
          } catch (error) {
            console.warn("Failed to parse tool call arguments:", error);
          }
        }
      }

      // Add text content to parts
      if (delta.content) {
        parts.push({
          type: "text",
          text: delta.content,
        });
      }

      messages.push({
        id: chunk.id,
        role: "assistant",
        content: delta.content,
        createdAt: new Date(chunk.created_at),
        parts: parts,
        toolInvocations: toolInvocations,
      } as UIMessage);
      continue;
    }
  }

  return messages;
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

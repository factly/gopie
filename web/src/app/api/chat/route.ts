import { createOpenAI } from "@ai-sdk/openai";
import { streamText, createDataStreamResponse } from "ai";
import { z } from "zod";

// Allow streaming responses up to 30 seconds
export const maxDuration = 30;

export async function POST(req: Request) {
  try {
    // Parse the request body
    const body = await req.json();
    const { messages, project_ids, dataset_ids, chat_id } = body;

    // Validate environment variable
    if (!process.env.NEXT_PUBLIC_GOPIE_API_URL) {
      throw new Error("NEXT_PUBLIC_GOPIE_API_URL is not defined");
    }

    console.log("Processing request with:", {
      messageCount: messages?.length,
      hasProjectIds: !!project_ids,
      hasDatasetIds: !!dataset_ids,
      chatId: chat_id,
    });

    // Create OpenAI-compatible client pointed at our API
    const openAI = createOpenAI({
      baseURL: process.env.NEXT_PUBLIC_GOPIE_API_URL + "/v1/api",
      apiKey: "not-needed",
      name: "GoPie",
    });

    // Build headers object
    const headers: Record<string, string> = {
      "x-project-ids": project_ids?.join(",") || "",
      "x-dataset-ids": dataset_ids?.join(",") || "",
      "x-user-id": "1",
    };

    // Add chat ID header if available
    if (chat_id) {
      headers["x-chat-id"] = chat_id;
    }

    return createDataStreamResponse({
      execute: async (dataStream) => {
        // Store chat ID for later use
        let newChatId: string | null = null;

        // Stream the text response
        const result = streamText({
          model: openAI("chatgpt-4o-latest"),
          messages: [
            {
              role: "user",
              content: messages[messages.length - 1].content,
            },
          ],
          headers,
          onChunk: ({ chunk }) => {
            if (chunk.type === "text-delta") {
              console.log("📝 Text chunk:", chunk.textDelta);
            } else if (chunk.type === "tool-call") {
              console.log("🔧 Tool call chunk:", chunk.toolName, chunk.args);
            } else if (chunk.type === "tool-call-streaming-start") {
              console.log("🔧 Tool call start:", chunk.toolName);
            } else if (chunk.type === "tool-call-delta") {
              console.log(
                "🔧 Tool call delta:",
                chunk.toolName,
                chunk.argsTextDelta
              );
            } else {
              console.log("📦 Other chunk:", chunk.type, chunk);

              // Check if this chunk has finish_reason === "stop" and capture its ID
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              const chunkData = chunk as Record<string, any>;
              if (
                chunkData.finish_reason === "stop" &&
                chunkData.id &&
                !chat_id
              ) {
                console.log(
                  "🏁 Found event with stop reason, ID:",
                  chunkData.id
                );
                newChatId = chunkData.id;
              }
            }
          },
          onFinish: (result) => {
            console.log("🔧 Result:", result);
            console.log("✅ Chat stream finished");
            console.log("📊 Usage:", result.usage);
            console.log("🔧 Tool calls:", result.toolCalls?.length || 0);
            console.log("🔧 Tool results:", result.toolResults?.length || 0);
          },
          onStepFinish: (result) => {
            console.log("🔧 Step finish:", result);
          },
          onError: (error) => {
            console.error("❌ Chat API error:", error);
          },
          tools: {
            tool_messages: {
              type: "function",
              parameters: z.object({
                messages: z.any(),
              }),
              execute: async ({ messages }) => {
                console.log("🔧 Tool message executed:", messages);
                return {
                  type: "tool-call",
                  toolCallId: "tool_messages",
                  toolName: "tool_messages",
                  args: {
                    messages,
                  },
                };
              },
            },
            datasets_used: {
              type: "function",
              parameters: z.object({
                datasets: z.any(),
              }),
              execute: async ({ datasets }) => {
                console.log("🔧 Datasets used executed:", datasets);
                return {
                  type: "tool-call",
                  toolCallId: "datasets_used",
                  toolName: "datasets_used",
                  args: {
                    datasets,
                  },
                };
              },
            },
            sql_query: {
              type: "function",
              parameters: z.object({
                query: z.string(),
              }),
              execute: async ({ query }) => {
                console.log("🔧 SQL query executed:", query);
                return {
                  type: "tool-call",
                  toolCallId: "sql_query",
                  toolName: "sql_query",
                  args: {
                    query,
                  },
                };
              },
            },
          },
          toolChoice: "required",
        });

        console.log("📡 Merging AI stream into data stream");
        await result.mergeIntoDataStream(dataStream);

        // Send chat ID as the last event if this is a new chat
        if (newChatId) {
          console.log("💬 New chat created with ID:", newChatId);
          dataStream.writeData({
            type: "chat-created",
            chatId: newChatId,
          });
        }
      },
      onError: (error) => {
        console.error("Data stream error:", error);
        return error instanceof Error ? error.message : String(error);
      },
    });
  } catch (error) {
    console.error("Chat API error:", error);

    // Return a proper error response
    return new Response(
      JSON.stringify({
        error: "Failed to process chat request",
        details: error instanceof Error ? error.message : String(error),
      }),
      {
        status: 500,
        headers: {
          "Content-Type": "application/json",
        },
      }
    );
  }
}

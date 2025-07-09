import { createOpenAI } from "@ai-sdk/openai";
import { streamText, createDataStreamResponse } from "ai";
import { z } from "zod";
import { getSession } from "@/lib/auth/auth-utils";

// Allow streaming responses up to 30 seconds
export const maxDuration = 30;

export async function POST(req: Request) {
  try {
    const isAuthEnabled = process.env.NEXT_PUBLIC_ENABLE_AUTH === "true";

    // Retrieve session only when auth is enabled
    const session = isAuthEnabled ? await getSession() : null;

    if (isAuthEnabled && !session) {
      return new Response(
        JSON.stringify({
          error: "Unauthorized",
          details: "No valid session found",
        }),
        {
          status: 401,
          headers: {
            "Content-Type": "application/json",
          },
        }
      );
    }

    // Parse the request body
    const body = await req.json();
    const { messages, project_ids, dataset_ids, chat_id } = body;

    // Validate environment variable
    if (!process.env.GOPIE_API_URL) {
      throw new Error("GOPIE_API_URL is not defined");
    }

    console.log("Processing request with:", {
      messageCount: messages?.length,
      hasProjectIds: !!project_ids,
      hasDatasetIds: !!dataset_ids,
      chatId: chat_id,
      authEnabled: isAuthEnabled,
      userId: isAuthEnabled ? session?.user.id : "system",
    });

    // Create OpenAI-compatible client pointed at our API
    const openAI = createOpenAI({
      baseURL: process.env.GOPIE_API_URL + "/v1/api",
      apiKey: "not-needed",
      name: "GoPie",
    });

    // Build headers object with authentication
    const headers: Record<string, string> = {
      "x-project-ids": project_ids?.join(",") || "",
      "x-dataset-ids": dataset_ids?.join(",") || "",
    };

    if (isAuthEnabled && session) {
      headers["Authorization"] = `Bearer ${session.accessToken}`;

      if (session.user.organizationId) {
        headers["x-organization-id"] = session.user.organizationId;
      }
    } else {
      // Auth disabled: use admin headers
      headers["x-user-id"] = "system";
      headers["x-organization-id"] = "system";
    }

    // Add chat ID header if available
    if (chat_id) {
      headers["x-chat-id"] = chat_id;
    }

    return createDataStreamResponse({
      execute: async (dataStream) => {
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
            }
          },
          onFinish: (result) => {
            console.log("🔧 Result:", result);
            console.log("✅ Chat stream finished");
            console.log("📊 Usage:", result.usage);
            console.log("🔧 Tool calls:", result.toolCalls?.length || 0);
            console.log("🔧 Tool results:", result.toolResults?.length || 0);

            // Send chat ID immediately if this is a new chat
            if (!chat_id && result.response?.id) {
              console.log("💬 New chat created with ID:", result.response.id);
              dataStream.writeData({
                type: "chat-created",
                chatId: result.response.id,
              });
            }
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
                role: z.string(),
                content: z.string(),
              }),
              execute: async ({ role, content }) => {
                return {
                  type: "tool-call",
                  toolCallId: "tool_messages",
                  toolName: "tool_messages",
                  args: {
                    role,
                    content,
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
            sql_queries: {
              type: "function",
              parameters: z.object({
                queries: z.array(z.string()),
              }),
              execute: async ({ queries }) => {
                console.log("🔧 SQL queries executed:", queries);
                return {
                  type: "tool-call",
                  toolCallId: "sql_queries",
                  toolName: "sql_queries",
                  args: {
                    queries,
                  },
                };
              },
            },
            visualization_result: {
              type: "function",
              parameters: z.object({
                s3_paths: z.array(z.string()),
              }),
              execute: async ({ s3_paths }) => {
                console.log("🔧 Visualization result executed:", s3_paths);
                return {
                  type: "tool-call",
                  toolCallId: "visualization_result",
                  toolName: "visualization_result",
                  args: {
                    s3_paths,
                  },
                };
              },
            },
            visualization_paths: {
              type: "function",
              parameters: z.object({
                paths: z.array(z.string()),
              }),
              execute: async ({ paths }) => {
                console.log("🔧 Visualization paths executed:", paths);
                return {
                  type: "tool-call",
                  toolCallId: "visualization_paths",
                  toolName: "visualization_paths",
                  args: {
                    paths,
                  },
                };
              },
            },
          },
          toolChoice: "required",
        });

        console.log("📡 Merging AI stream into data stream");
        await result.mergeIntoDataStream(dataStream);
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

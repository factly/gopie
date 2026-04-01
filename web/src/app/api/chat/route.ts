import { auth } from "@/lib/auth/auth";
import { headers as nextHeaders } from "next/headers";
import {
  createUIMessageStream,
  createUIMessageStreamResponse,
} from "ai";
import type { GoPieUIMessage } from "@/types/chat-message";
import { LRUCache } from "@/lib/utils/lru-cache";
import { transformUIMessagesToBackend } from "@/lib/utils/message-transformation";

// Allow streaming responses up to 30 seconds
export const maxDuration = 30;

/**
 * Parse SSE data from backend stream
 */
interface ParsedSSEData {
  done?: boolean;
  chat_id?: string;
  id?: string;
  choices?: Array<{
    delta?: {
      content?: string;
      tool_calls?: Array<{
        function?: {
          name?: string;
          arguments?: string;
        };
        id?: string;
      }>;
    };
    finish_reason?: string;
  }>;
}

function parseSSEData(line: string): ParsedSSEData | null {
  if (!line.startsWith('data: ')) return null;
  const data = line.slice(6);
  if (data === '[DONE]') return { done: true };
  try {
    return JSON.parse(data) as ParsedSSEData;
  } catch {
    return null;
  }
}

export async function POST(req: Request) {
  try {
    const isAuthEnabled =
      String(process.env.NEXT_PUBLIC_ENABLE_AUTH).trim() === "true";

    // Retrieve session only when auth is enabled
    const session = isAuthEnabled
      ? await auth.api.getSession({ headers: await nextHeaders() })
      : null;

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

    // Convert UI messages to OpenAI format for backend
    const backendMessages = transformUIMessagesToBackend(messages);

    // Check if messages is empty
    if (!backendMessages || backendMessages.length === 0) {
      // Return error using the new streaming format
      const stream = createUIMessageStream<GoPieUIMessage>({
        execute: async ({ writer }) => {
          writer.write({
            type: 'data-status-notification',
            data: {
              message: 'No messages provided',
              level: 'error'
            },
            transient: true,
          });
        },
      });
      return createUIMessageStreamResponse({ stream });
    }

    // Build headers for the backend request
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      "x-project-ids": project_ids?.join(",") || "",
      "x-dataset-ids": dataset_ids?.join(",") || "",
    };

    if (isAuthEnabled && session) {
      // Forward the browser's session cookie to the backend so BetterAuthMiddleware can validate it
      headers["Cookie"] = (await nextHeaders()).get("cookie") ?? "";
      const orgId = (session.session as { activeOrganizationId?: string }).activeOrganizationId;
      if (orgId) {
        headers["x-organization-id"] = orgId;
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

    // Create UI message stream
    const stream = createUIMessageStream<GoPieUIMessage>({
      execute: async ({ writer }) => {
        try {
          // Make request to backend
          const backendResponse = await fetch(
            `${process.env.GOPIE_API_URL}/v1/api/chat/completions`,
            {
              method: "POST",
              headers,
              body: JSON.stringify({
                model: "chatgpt-4o-latest",
                messages: backendMessages,
                stream: true,
              }),
            }
          );

          if (!backendResponse.ok) {
            // Try to get the actual error message from the response
            let errorMessage = backendResponse.statusText;
            try {
              const errorBody = await backendResponse.text();
              try {
                const errorJson = JSON.parse(errorBody);
                errorMessage = errorJson.message || errorJson.error || errorMessage;
              } catch {
                if (errorBody) {
                  errorMessage = errorBody;
                }
              }
            } catch (e) {
              console.error("Could not read error body:", e);
            }

            writer.write({
              type: 'data-status-notification',
              data: {
                message: errorMessage,
                level: 'error'
              },
              transient: true,
            });
            return;
          }

          const reader = backendResponse.body?.getReader();
          const decoder = new TextDecoder();
          let chatIdSent = false;
          let isStreamingText = false;
          const textId = 'text-1';

          // Track SQL queries and their IDs for reconciliation
          // Using LRU cache to prevent unbounded memory growth in long sessions
          const sqlQueries = new LRUCache<string, string>(50); // query -> id mapping with max 50 entries
          let sqlCounter = 0;

          // Track intermediate thoughts
          let intermediateCounter = 0;

          if (!reader) {
            throw new Error("No response body reader");
          }

          // Text stream placeholder - removed as unused
          let buffer = "";

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop() || "";

            for (const line of lines) {
              const trimmed = line.trim();
              if (!trimmed) continue;

              const parsed = parseSSEData(trimmed);
              if (!parsed) {
                if (trimmed.startsWith("data: ")) {
                  console.warn("Incomplete JSON, waiting for next chunk:", trimmed);
                  buffer = trimmed;
                }
                continue;
              }

              if (parsed.done) {
                console.log("Stream complete");
                break;
              }

              // Handle chat ID from backend
              const chatId = parsed.chat_id || parsed.id;
              if (chatId && chatId !== "" && !chatIdSent) {
                chatIdSent = true;
                writer.write({
                  type: 'data-chat-created',
                  data: { chatId },
                  transient: true, // Don't persist in message history
                });
              }

              // Handle tool calls
              if (parsed.choices?.[0]?.delta?.tool_calls) {
                for (const toolCall of parsed.choices[0].delta.tool_calls) {
                  if (toolCall.function) {
                    try {
                      const args = JSON.parse(toolCall.function.arguments || "{}");
                      const functionName = toolCall.function.name;

                      switch (functionName) {
                        case "tool_messages":
                          if (args.role === "intermediate" && args.content) {
                            // Send intermediate thoughts as persistent data parts
                            writer.write({
                              type: 'data-intermediate-thought',
                              data: { content: args.content },
                              // Not transient - we want these to persist in message.parts
                              id: `intermediate-${++intermediateCounter}`,
                            });
                          }
                          break;

                        case "sql_queries":
                          if (args.queries) {
                            const queries = Array.isArray(args.queries) ? args.queries : [args.queries];
                            for (const query of queries) {
                              if (typeof query === 'string') {
                                // Generate or get existing ID for this query
                                let queryId = sqlQueries.get(query);
                                if (!queryId) {
                                  queryId = `sql-${++sqlCounter}`;
                                  sqlQueries.set(query, queryId);
                                }

                                // Send SQL query with pending status
                                writer.write({
                                  type: 'data-sql-query',
                                  id: queryId,
                                  data: {
                                    id: queryId,
                                    query,
                                    status: 'pending',
                                  },
                                });
                              }
                            }
                          }
                          break;

                        case "datasets_used":
                          if (args.datasets && Array.isArray(args.datasets)) {
                            writer.write({
                              type: 'data-datasets-used',
                              data: { datasets: args.datasets },
                            });
                          }
                          break;

                        case "visualization_paths":
                        case "visualization_result":
                          const paths = args.paths ||
                            (args.visualization_json_paths?.map((v: { json_path?: string }) => v.json_path)) ||
                            [];
                          if (paths.length > 0) {
                            writer.write({
                              type: 'data-visualization',
                              id: `viz-${toolCall.id || Date.now()}`,
                              data: {
                                id: `viz-${toolCall.id || Date.now()}`,
                                paths,
                                status: 'ready',
                              },
                            });
                          }
                          break;

                        case "set_context":
                          if (args.project_ids || args.dataset_ids) {
                            writer.write({
                              type: 'data-context-info',
                              data: {
                                projectIds: args.project_ids || [],
                                datasetIds: args.dataset_ids || [],
                              },
                            });
                          }
                          break;
                      }
                    } catch (e) {
                      console.error("Failed to parse tool arguments:", e);
                    }
                  }
                }
              }

              // Handle text content
              if (parsed.choices?.[0]?.delta?.content) {
                // textBuffer tracking removed - not needed with new streaming

                // Start text streaming if not started
                if (!isStreamingText) {
                  isStreamingText = true;
                  writer.write({
                    type: 'text-start',
                    id: textId,
                  });
                }

                // Stream the text delta
                writer.write({
                  type: 'text-delta',
                  id: textId,
                  delta: parsed.choices[0].delta.content,
                });
              }

              // Handle finish reason
              if (parsed.choices?.[0]?.finish_reason === "stop") {
                if (isStreamingText) {
                  writer.write({
                    type: 'text-end',
                    id: textId,
                  });
                  isStreamingText = false;
                }
              }
            }
          }

          // Ensure text streaming is properly closed
          if (isStreamingText) {
            writer.write({
              type: 'text-end',
              id: textId,
            });
          }

          // Send finish event
          writer.write({
            type: 'finish',
          });

        } catch (error) {
          console.error("Stream processing error:", error);
          writer.write({
            type: 'data-status-notification',
            data: {
              message: error instanceof Error ? error.message : 'Unknown error occurred',
              level: 'error'
            },
            transient: true,
          });
        }
      },
    });

    return createUIMessageStreamResponse({ stream });
  } catch (error) {
    console.error("Chat API error:", error);

    // Return error in new streaming format
    const stream = createUIMessageStream<GoPieUIMessage>({
      execute: async ({ writer }) => {
        writer.write({
          type: 'data-status-notification',
          data: {
            message: error instanceof Error ? error.message : String(error),
            level: 'error'
          },
          transient: true,
        });
      },
    });

    return createUIMessageStreamResponse({ stream });
  }
}
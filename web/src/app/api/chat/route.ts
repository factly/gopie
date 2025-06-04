import { createOpenAI } from "@ai-sdk/openai";
import { streamText } from "ai";
import { z } from "zod";

// Allow streaming responses up to 30 seconds
export const maxDuration = 30;

export async function POST(req: Request) {
  try {
    // Parse the request body
    const body = await req.json();
    const { messages, project_ids, dataset_ids } = body;

    // Validate environment variable
    if (!process.env.NEXT_PUBLIC_GOPIE_API_URL) {
      throw new Error("NEXT_PUBLIC_GOPIE_API_URL is not defined");
    }

    console.log("Processing request with:", {
      messageCount: messages?.length,
      hasProjectIds: !!project_ids,
      hasDatasetIds: !!dataset_ids,
    });

    // Create OpenAI-compatible client pointed at our API
    const openAI = createOpenAI({
      baseURL: process.env.NEXT_PUBLIC_GOPIE_API_URL + "/v1/api",
      apiKey: "not-needed",
      name: "GoPie",
    });

    // Stream the text response
    const result = streamText({
      model: openAI("chatgpt-4o-latest"),
      messages,
      headers: {
        "x-project-ids": project_ids?.join(",") || "",
        "x-dataset-ids": dataset_ids?.join(",") || "",
      },
      onError: (error) => {
        console.error("Chat API error:", error);
      },
      tools: {
        tool_messages: {
          type: "function",
          parameters: z.object({
            messages: z.any(),
          }),
          execute: async ({ messages }) => {
            console.log("Tool message:", messages);
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
            console.log("Datasets used:", datasets);
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
            console.log("SQL query:", query);
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
      experimental_activeTools: ["tool_messages", "datasets_used", "sql_query"],
    });

    // Return the streaming response directly without consuming it first
    return result.toDataStreamResponse();
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

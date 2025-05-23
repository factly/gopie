import { createMutation } from "react-query-kit";
import { apiClient } from "@/lib/api-client";
import { type KyResponse } from "ky";

interface ChatWithAgentParams {
  chatId?: string;
  datasetIds?: string[];
  projectIds?: string[];
  prompt: string;
  signal?: AbortSignal;
}

// The mutation function will return the raw KyResponse object
// to allow the caller to process the text/event-stream.
export const useChatWithAgent = createMutation<
  KyResponse,
  ChatWithAgentParams,
  Error
>({
  mutationKey: ["chat-with-agent"],
  mutationFn: async (params: ChatWithAgentParams): Promise<KyResponse> => {
    const response = await apiClient.post("v1/api/chats/agent", {
      json: {
        chat_id: params.chatId,
        dataset_ids: params.datasetIds,
        project_ids: params.projectIds,
        prompt: params.prompt,
      },
      signal: params.signal,
      // Ky throws HTTPError for non-2xx responses by default.
      // The response object itself is returned to the caller for stream processing.
      // The apiClient is configured with timeout: false, which is suitable for long-lived streams.
    });
    return response;
  },
});

import { createMutation } from "react-query-kit";
import { ChatWithMessages } from "@/lib/api-client";
import { apiClient } from "@/lib/api-client";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

interface CreateChatParams {
  chatId?: string;
  datasetId?: string;
  createdBy?: string;
  messages: ChatMessage[];
}

export const useCreateChat = createMutation({
  mutationKey: ["create-chat"],
  mutationFn: async (
    params: CreateChatParams
  ): Promise<{ data: ChatWithMessages }> => {
    const response = await apiClient.post("v1/api/chat", {
      json: {
        chat_id: params.chatId,
        dataset_id: params.datasetId,
        created_by: params.createdBy,
        messages: params.messages,
      },
    });

    return response.json();
  },
});

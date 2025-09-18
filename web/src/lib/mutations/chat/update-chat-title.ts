import { createMutation } from "react-query-kit";
import { apiClient } from "@/lib/api-client";

interface UpdateChatTitleParams {
  chatId: string;
  title: string;
}

interface UpdateChatTitleResponse {
  id: string;
  title: string;
}

export const useUpdateChatTitle = createMutation({
  mutationKey: ["update-chat-title"],
  mutationFn: async (
    params: UpdateChatTitleParams
  ): Promise<UpdateChatTitleResponse> => {
    const response = await apiClient.put(`v1/api/chat/${params.chatId}/title`, {
      json: {
        title: params.title,
      },
    });

    return response.json();
  },
});
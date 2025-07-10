import { createMutation } from "react-query-kit";
import { apiClient } from "@/lib/api-client";

export type ChatVisibility = "public" | "private" | "organization";

interface UpdateChatVisibilityParams {
  chatId: string;
  visibility: ChatVisibility;
}

export const useUpdateChatVisibility = createMutation({
  mutationKey: ["update-chat-visibility"],
  mutationFn: async ({ chatId, visibility }: UpdateChatVisibilityParams) => {
    const response = await apiClient.put(`v1/api/chat/${chatId}/visibility`, {
      json: {
        visibility,
      },
    });

    return response.json();
  },
});

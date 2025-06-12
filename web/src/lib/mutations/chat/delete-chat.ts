import { apiClient } from "@/lib/api-client";
import { createMutation } from "react-query-kit";

interface DeleteChatParams {
  chatId: string;
  userId: string;
}

export const useDeleteChat = createMutation({
  mutationKey: ["delete-chat"],
  mutationFn: async ({ chatId, userId }: DeleteChatParams) => {
    await apiClient.delete(`v1/api/chat/${chatId}`, {
      headers: {
        "x-user-id": userId,
      },
    });
  },
});

import { apiClient } from "@/lib/api-client";
import { createMutation } from "react-query-kit";

interface DeleteMessageParams {
  chatId: string;
  messageId: string;
}

export const useDeleteMessage = createMutation({
  mutationKey: ["delete-message"],
  mutationFn: async ({ chatId, messageId }: DeleteMessageParams) => {
    await apiClient.delete(`v1/api/chat/${chatId}/messages/${messageId}`);
  },
});

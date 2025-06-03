import { apiClient } from "@/lib/api-client";
import { createMutation } from "react-query-kit";

export const useDeleteChat = createMutation({
  mutationKey: ["delete-chat"],
  mutationFn: async (chatId: string) => {
    await apiClient.delete(`v1/api/chat/${chatId}`);
  },
});

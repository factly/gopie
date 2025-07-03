import { apiClient } from "@/lib/api-client";
import { createQuery } from "react-query-kit";

interface GetChatVariables {
  chatId: string;
  userId: string;
}

interface ChatDetails {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  created_by: string;
  Visibility?: "public" | "private" | "organization";
  [key: string]: unknown; // For additional properties
}

async function fetchChat({
  chatId,
  userId,
}: GetChatVariables): Promise<{ data: ChatDetails }> {
  try {
    const response = await apiClient.get(`v1/api/chat/${chatId}`, {
      headers: {
        userID: userId,
      },
    });

    return await response.json();
  } catch (error) {
    throw new Error("Failed to fetch chat details: " + error);
  }
}

export const useChatDetails = createQuery<
  { data: ChatDetails },
  GetChatVariables,
  Error
>({
  queryKey: ["chat-details"],
  fetcher: fetchChat,
});

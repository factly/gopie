import { ChatMessage, PaginatedResponse } from "@/lib/api-client";
import { apiClient } from "@/lib/api-client";
import { createInfiniteQuery } from "react-query-kit";

interface GetMessagesVariables {
  chatId: string;
  limit?: number;
  page?: number;
}

async function fetchMessages(
  { chatId, limit }: GetMessagesVariables,
  context: { pageParam: number }
): Promise<{ data: PaginatedResponse<ChatMessage> }> {
  try {
    const searchParams = new URLSearchParams({
      limit: (limit || 20).toString(),
      page: context.pageParam.toString(),
    });

    const response = await apiClient.get(
      `v1/api/chat/${chatId}/messages?${searchParams}`
    );
    return response.json();
  } catch (error) {
    throw new Error("Failed to fetch chat messages: " + error);
  }
}

export const useChatMessages = createInfiniteQuery<
  { data: PaginatedResponse<ChatMessage> },
  GetMessagesVariables,
  Error,
  number
>({
  queryKey: ["chat-messages"],
  fetcher: fetchMessages,
  initialPageParam: 1,
  getNextPageParam: (lastPage, allPages) => {
    const totalPages = Math.ceil(
      lastPage.data.total / (lastPage.data.limit || 20)
    );
    const nextPage = allPages.length + 1;
    return nextPage <= totalPages ? nextPage : undefined;
  },
});

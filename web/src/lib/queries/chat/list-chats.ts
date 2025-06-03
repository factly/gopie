import { Chat, PaginatedResponse } from "@/lib/api-client";
import { apiClient } from "@/lib/api-client";
import { createInfiniteQuery } from "react-query-kit";

interface ListChatsVariables {
  datasetId: string;
  limit?: number;
  page?: number;
}

export async function fetchChats(
  { datasetId, limit }: ListChatsVariables,
  context: { pageParam: number }
): Promise<{ data: PaginatedResponse<Chat> }> {
  try {
    const searchParams = new URLSearchParams({
      dataset_id: datasetId,
      limit: (limit || 10).toString(),
      page: context.pageParam.toString(),
    });

    const response = await apiClient.get(`v1/api/chat?${searchParams}`);
    return response.json();
  } catch (error) {
    throw new Error("Failed to fetch chats: " + error);
  }
}

export const useChats = createInfiniteQuery<
  { data: PaginatedResponse<Chat> },
  ListChatsVariables,
  Error,
  number
>({
  queryKey: ["chats"],
  fetcher: fetchChats,
  initialPageParam: 1,
  getNextPageParam: (lastPage, allPages) => {
    const totalPages = Math.ceil(
      lastPage.data.total / (lastPage.data.limit || 10)
    );
    const nextPage = allPages.length + 1;
    return nextPage <= totalPages ? nextPage : undefined;
  },
});

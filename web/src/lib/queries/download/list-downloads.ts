import { apiClient } from "@/lib/api-client";
import { useQuery } from "@tanstack/react-query";
import { Download } from "@/lib/stores/download-store";

interface ListDownloadsParams {
  limit?: number;
  offset?: number;
}

export const listDownloads = async ({ limit = 10, offset = 0 }: ListDownloadsParams = {}) => {
  const response = await apiClient.get(`v1/api/downloads?limit=${limit}&offset=${offset}`);
  return response.json<Download[]>();
};

export const useListDownloads = (params?: ListDownloadsParams) => {
  return useQuery({
    queryKey: ['downloads', params],
    queryFn: () => listDownloads(params),
  });
};
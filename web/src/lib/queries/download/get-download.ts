import { apiClient } from "@/lib/api-client";
import { useQuery } from "@tanstack/react-query";
import { Download } from "@/lib/stores/download-store";

export const getDownload = async (downloadId: string) => {
  const response = await apiClient.get(`v1/api/downloads/${downloadId}`);
  return response.json<Download>();
};

export const useGetDownload = (downloadId: string, enabled = true) => {
  return useQuery({
    queryKey: ['downloads', downloadId],
    queryFn: () => getDownload(downloadId),
    enabled,
  });
};
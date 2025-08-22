import { apiClient } from "@/lib/api-client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useDownloadStore } from "@/lib/stores/download-store";

export const deleteDownload = async (downloadId: string) => {
  await apiClient.delete(`v1/api/downloads/${downloadId}`);
};

export const useDeleteDownload = () => {
  const queryClient = useQueryClient();
  const { removeDownload } = useDownloadStore();

  return useMutation({
    mutationFn: deleteDownload,
    onSuccess: (_, downloadId) => {
      removeDownload(downloadId);
      queryClient.invalidateQueries({ queryKey: ['downloads'] });
    },
  });
};
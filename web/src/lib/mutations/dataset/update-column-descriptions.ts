import { apiClient } from "@/lib/api-client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { GetColumnDescriptionsResponse } from "@/lib/queries/dataset/get-column-descriptions";

export interface UpdateColumnDescriptionsRequest {
  column_descriptions: Record<string, string>;
}

export const updateColumnDescriptions = async (
  datasetId: string,
  data: UpdateColumnDescriptionsRequest
): Promise<GetColumnDescriptionsResponse> => {
  const response = await apiClient.patch(
    `v1/api/datasets/${datasetId}/column-descriptions`,
    {
      json: data,
    }
  );
  return response.json();
};

export const useUpdateColumnDescriptions = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ datasetId, data }: { datasetId: string; data: UpdateColumnDescriptionsRequest }) =>
      updateColumnDescriptions(datasetId, data),
    onSuccess: (_, variables) => {
      // Invalidate the column descriptions query to refetch the updated data
      queryClient.invalidateQueries({
        queryKey: ["column-descriptions", variables.datasetId],
      });
    },
  });
};
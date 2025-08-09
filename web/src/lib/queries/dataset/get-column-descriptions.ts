import { apiClient } from "@/lib/api-client";
import { useQuery } from "@tanstack/react-query";

export interface ColumnSummary {
  column_name: string;
  column_type: string;
  min: string;
  max: string;
  approx_unique: number;
  avg: string;
  std: string;
  q25: string;
  q50: string;
  q75: string;
  count: number;
  null_percentage: number | { Scale: number; Value: number; Width: number } | null;
  description?: string;
}

export interface GetColumnDescriptionsResponse {
  data: {
    dataset_name: string;
    summary: ColumnSummary[];
  };
}

export const getColumnDescriptions = async (datasetId: string): Promise<GetColumnDescriptionsResponse> => {
  const response = await apiClient.get(`v1/api/datasets/${datasetId}/column-descriptions`);
  return response.json();
};

export const useColumnDescriptions = ({
  datasetId,
  enabled = true,
}: {
  datasetId: string;
  enabled?: boolean;
}) => {
  return useQuery({
    queryKey: ["column-descriptions", datasetId],
    queryFn: () => getColumnDescriptions(datasetId),
    enabled: enabled && !!datasetId,
  });
};
import { Dataset } from "@/lib/api-client";
import { apiClient } from "@/lib/api-client";
import { createQuery } from "react-query-kit";

interface GetDatasetParams {
  projectId: string;
  datasetId: string;
}

async function fetchDataset({
  projectId,
  datasetId,
}: GetDatasetParams): Promise<Dataset> {
  try {
    const response = await apiClient.get(
      `v1/api/projects/${projectId}/datasets/${datasetId}`,
    );
    return response.json();
  } catch (error) {
    throw new Error("Failed to fetch dataset: " + error);
  }
}

export const useDataset = createQuery({
  queryKey: ["dataset"],
  fetcher: fetchDataset,
});

import { apiClient, Dataset } from "../../api-client";

export interface UpdateDatasetBody {
  description?: string;
  alias?: string;
  updated_by: string;
  custom_prompt?: string;
}

export const updateDataset = async (
  projectId: string,
  datasetId: string,
  body: UpdateDatasetBody,
): Promise<{ data: Dataset }> => {
  const response = await apiClient.put(
    `v1/api/projects/${projectId}/datasets/${datasetId}`,
    { json: body },
  );
  return response.json();
};

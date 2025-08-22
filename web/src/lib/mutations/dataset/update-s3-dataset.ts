import { apiClient, Dataset } from "../../api-client";

export interface UpdateS3DatasetBody {
  dataset: string;
  description?: string;
  file_path?: string;
  updated_by: string;
  custom_prompt?: string;
}

export const updateS3Dataset = async (
  body: UpdateS3DatasetBody,
): Promise<{ data: Dataset }> => {
  const response = await apiClient.post("source/s3/update", { json: body });
  return response.json();
};

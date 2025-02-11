import { apiClient } from '../../api-client';

export const deleteDataset = async (projectId: string, datasetId: string) => {
  await apiClient.delete(`v1/api/projects/${projectId}/datasets/${datasetId}`);
}; 
import { apiClient } from "../../api-client";

export const deleteProject = async (projectId: string) => {
  await apiClient.delete(`v1/api/projects/${projectId}`);
};

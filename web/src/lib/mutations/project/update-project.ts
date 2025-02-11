import { apiClient, Project } from '../../api-client';

export interface UpdateProjectBody {
  name: string;
  description?: string;
}

export const updateProject = async (projectId: string, body: UpdateProjectBody): Promise<{ data: Project }> => {
  const response = await apiClient.patch(`v1/api/projects/${projectId}`, { json: body });
  return response.json();
}; 
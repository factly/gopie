import { Project } from "@/lib/api-client";
import { apiClient } from "@/lib/api-client";
import { createQuery } from "react-query-kit";

async function fetchProject({
  projectId,
}: {
  projectId: string;
}): Promise<Project> {
  try {
    const response = await apiClient.get(`v1/api/projects/${projectId}`);
    return response.json();
  } catch (error) {
    throw new Error("Failed to fetch project: " + error);
  }
}

export const useProject = createQuery({
  queryKey: ["project"],
  fetcher: fetchProject,
});

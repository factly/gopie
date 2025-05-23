import { createMutation } from "react-query-kit";
import { Project, ProjectInput } from "@/lib/api-client";
import { apiClient } from "@/lib/api-client";

async function createProject(
  project: ProjectInput
): Promise<{ data: Project }> {
  try {
    const response = await apiClient.post("v1/api/projects/", {
      json: project,
    });

    return response.json();
  } catch (error) {
    console.error("Error creating project:", error);
    throw error;
  }
}

export const useCreateProject = createMutation({
  mutationKey: ["create-project"],
  mutationFn: createProject,
});

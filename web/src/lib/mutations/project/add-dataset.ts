import { createMutation } from "react-query-kit";
import { Project } from "@/lib/api-client";
import { apiClient } from "@/lib/api-client";

export const useAddDatasetToProject = createMutation({
  mutationKey: ["add-dataset-to-project"],
  mutationFn: async ({
    projectId,
    datasetId,
  }: {
    projectId: string;
    datasetId: string;
  }): Promise<Project> => {
    const response = await apiClient.post(
      `v1/api/projects/${projectId}/datasets/`,
      {
        json: {
          dataset_id: datasetId,
        },
      },
    );

    return response.json();
  },
});

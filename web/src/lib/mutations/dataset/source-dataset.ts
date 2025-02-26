import { createMutation } from "react-query-kit";
import { apiClient } from "@/lib/api-client";

interface Response {
  message: string;
  tableName: string;
}

export const useSourceDataset = createMutation({
  mutationKey: ["source-dataset"],
  mutationFn: async ({
    datasetUrl,
    projectId,
    alias,
    createdBy,
  }: {
    datasetUrl: string;
    projectId: string;
    alias: string;
    createdBy: string;
  }) => {
    const res = await apiClient.post("source/s3/upload", {
      body: JSON.stringify({
        file_path: datasetUrl,
        description: "Uploaded from Gopie Web",
        project_id: projectId,
        alias,
        created_by: createdBy,
      }),
    });

    if (!res.ok) {
      throw new Error("Failed to source dataset");
    }

    return (await res.json()) as Response;
  },
});

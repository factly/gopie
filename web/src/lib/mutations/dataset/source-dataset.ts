import { createMutation } from "react-query-kit";
import { apiClient, Dataset } from "@/lib/api-client";

interface Response {
  data: {
    dataset: Dataset;
    summary: {
      dataset_name: string;
      summary: Record<string, string>[];
    };
  };
}

export const useSourceDataset = createMutation({
  mutationKey: ["source-dataset"],
  mutationFn: async ({
    datasetUrl,
    projectId,
    alias,
    createdBy,
    description,
    alter_column_names,
    column_descriptions,
  }: {
    datasetUrl: string;
    projectId: string;
    alias: string;
    createdBy: string;
    description?: string;
    alter_column_names?: Record<string, string>;
    column_descriptions: Record<string, string>;
  }) => {
    const res = await apiClient.post("source/s3/upload", {
      body: JSON.stringify({
        file_path: datasetUrl,
        description: description || "Uploaded from GoPie Web",
        project_id: projectId,
        alias,
        created_by: createdBy,
        alter_column_names: alter_column_names,
        column_descriptions: column_descriptions,
        ignore_errors: true,
      }),
    });

    if (!res.ok) {
      throw new Error("Failed to source dataset");
    }

    return (await res.json()) as Response;
  },
});

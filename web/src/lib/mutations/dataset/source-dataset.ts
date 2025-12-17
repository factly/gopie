import { createMutation } from "react-query-kit";
import { apiClient, Dataset } from "@/lib/api-client";
import { fetchWithSSE } from "@/lib/sse-client";
import { useAuth } from "@/hooks/use-auth";
import { SSEEvent } from "@/lib/sse-client";
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
    custom_prompt,
  }: {
    datasetUrl: string;
    projectId: string;
    alias: string;
    createdBy: string;
    description?: string;
    alter_column_names?: Record<string, string>;
    column_descriptions: Record<string, string>;
    custom_prompt?: string;
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
        custom_prompt: custom_prompt,
      }),
    });

    if (!res.ok) {
      throw new Error("Failed to source dataset");
    }

    return (await res.json()) as Response;
  },
});

export const useSourceDatasetSSE = () => {
  const { accessToken } = useAuth();
  return async ({
    datasetUrl,
    projectId,
    alias,
    createdBy,
    description,
    alter_column_names,
    column_descriptions,
    custom_prompt,
    onProgress,
  }: {
    datasetUrl: string;
    projectId: string;
    alias: string;
    createdBy: string;
    description?: string;
    alter_column_names?: Record<string, string>;
    column_descriptions: Record<string, string>;
    custom_prompt?: string;
    onProgress: (event: SSEEvent) => void
  }) => {
    const requestBody = {
      file_path: datasetUrl,
      description: description || "Uploaded from GoPie Web",
      project_id: projectId,
      alias,
      created_by: createdBy,
      alter_column_names,
      column_descriptions,
      ignore_errors: true,
      custom_prompt,
    };
    return await fetchWithSSE(
      '/source/s3/upload', // Ensure path matches your API router prefix
      {
        method: 'POST',
        body: JSON.stringify(requestBody),
      },
      onProgress,
      accessToken
    );
  };
};

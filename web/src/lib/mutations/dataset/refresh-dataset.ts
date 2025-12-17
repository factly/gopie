import { createMutation } from "react-query-kit";
import { apiClient, Dataset } from "@/lib/api-client";
import { fetchWithSSE } from "@/lib/sse-client";
import { useAuth } from "@/hooks/use-auth";
import { SSEEvent } from "@/lib/sse-client";

// Define the structure of the response based on the Go code
interface RefreshDatasetResponse {
  data: {
    dataset: Dataset;
    summary: {
      dataset_name: string;
      summary: Record<string, string>[];
    };
  };
}

// Define the variables required by the mutation function
interface RefreshDatasetVariables {
  datasetName: string;
  projectId: string;
  s3Url: string;
  ignoreErrors?: boolean;
  source?: string;
}

/**
 * React Query Mutation hook to refresh an existing dataset from a new S3 file.
 */
export const useRefreshDataset = createMutation({
  mutationKey: ["refresh-dataset"],
  mutationFn: async ({
    datasetName,
    projectId,
    s3Url,
    ignoreErrors = true,
    source,
  }: RefreshDatasetVariables) => {
    const res = await apiClient.post("source/s3/refresh", {
      body: JSON.stringify({
        dataset_name: datasetName,
        project_id: projectId,
        file_path: s3Url,
        ignore_errors: ignoreErrors,
        source: source,
      }),
    });

    if (!res.ok) {
      let errorMsg = `Failed to refresh dataset: ${res.statusText}`;
      try {
        // 👇 Explicitly type and safely extract
        const errorBody = (await res.json()) as
          | { message?: string; error?: string }
          | undefined;

        if (errorBody?.message) {
          errorMsg = errorBody.message;
        } else if (errorBody?.error) {
          errorMsg = errorBody.error;
        }
      } catch {
        // ignore parsing errors
      }

      throw new Error(errorMsg);
    }

    return (await res.json()) as RefreshDatasetResponse;
  },
});

export const useRefreshDatasetSSE = () => {
  const { accessToken } = useAuth();
  return async ({
    datasetName,
    projectId,
    s3Url,
    source,
    ignoreErrors,
    onProgress,
  }: {
    datasetName: string;
    projectId: string;
    s3Url: string;
    source?: string;
    ignoreErrors?: boolean;
    onProgress: (event: SSEEvent) => void
  }) => {
    return await fetchWithSSE(
      '/source/s3/refresh',
      {
        method: 'POST',
        body: JSON.stringify({
          dataset_name: datasetName,
          project_id: projectId,
          file_path: s3Url,
          ignore_errors: ignoreErrors ?? true,
          source: source,
        }),
      },
      onProgress,
      accessToken
    );
  };
};

import { createMutation } from "react-query-kit";
import { apiClient, Dataset } from "@/lib/api-client"; 


interface RefreshDatabaseDatasetResponse {
  data: {
    dataset: Dataset;
    summary: {
      dataset_name: string;
      summary: Record<string, string>[];
    };
  };
}


interface RefreshDatabaseDatasetVariables {
  projectId: string;
  datasetName: string;
  refreshType: "full" | "incremental";
}

/**
 * React Query Mutation hook to refresh an existing dataset from a database source.
 */
export const useRefreshDatabaseDataset = createMutation({
  mutationKey: ["refresh-database-dataset"],
  mutationFn: async ({
    projectId,
    datasetName,
    refreshType,
  }: RefreshDatabaseDatasetVariables) => {
    // Call the /source/database/refresh endpoint
    const res = await apiClient.post("source/database/refresh", {
      body: JSON.stringify({
        project_id: projectId,
        dataset_name: datasetName,
        refresh_type: refreshType,
      }),
    });

    if (!res.ok) {
      let errorMsg = `Failed to refresh dataset: ${res.statusText}`;
      try {
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

    // Return the response, typed to our new interface
    return (await res.json()) as RefreshDatabaseDatasetResponse;
  },
});
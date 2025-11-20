import { createQuery } from "react-query-kit";
import { apiClient } from "@/lib/api-client";

interface CheckTimestampResponse {
  has_timestamp_column: boolean;
}

interface CheckTimestampVariables {
  datasetId: string;
}

/**
 * React Query hook to check if a database-sourced dataset
 * has a timestamp column for incremental refresh.
 */
export const useCheckTimestampColumn = createQuery<
  boolean, // Return type
  CheckTimestampVariables // Variables type
>({
  queryKey: ["check-timestamp"],
  fetcher: async ({ datasetId }): Promise<boolean> => {
    if (!datasetId) {
      throw new Error("datasetId is required");
    }

    try {
      const res = await apiClient.get(
        `source/database/refresh/${datasetId}`
      );

      if (!res.ok) {
        throw new Error("Failed to check timestamp column");
      }

      const data = (await res.json()) as CheckTimestampResponse;
      return data.has_timestamp_column;
    } catch (error) {
      console.error("Error checking timestamp column:", error);
      return false;
    }
  },
});

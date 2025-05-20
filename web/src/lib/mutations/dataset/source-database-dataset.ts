import { createMutation } from "react-query-kit";
import { apiClient, Dataset } from "@/lib/api-client";

interface SourceDatabaseDatasetParams {
  alias: string;
  connection_string: string;
  created_by: string;
  driver: "postgres" | "mysql";
  project_id: string;
  sql_query: string;
  description?: string;
}

interface SourceDatabaseDatasetResponse {
  dataset: Dataset;
  source: {
    connection_string: string;
    created_by: string;
    id: string;
    sql_query: string;
    updated_at: string;
  };
  summary: {
    dataset_name: string;
    summary: Record<string, string>[];
  };
}

interface ApiErrorResponse {
  code?: number;
  error?: string;
  message?: string;
}

export const useSourceDatabaseDataset = createMutation({
  mutationKey: ["source-database-dataset"],
  mutationFn: async (
    params: SourceDatabaseDatasetParams
  ): Promise<SourceDatabaseDatasetResponse> => {
    const res = await apiClient.post("source/database/upload", {
      json: {
        alias: params.alias,
        connection_string: params.connection_string,
        created_by: params.created_by,
        description:
          params.description || "Dataset sourced from database via GoPie Web",
        driver: params.driver,
        project_id: params.project_id,
        sql_query: params.sql_query,
      },
    });

    if (!res.ok) {
      let errorMessage = `Failed to source dataset from database: ${res.status} ${res.statusText}`;
      try {
        const errorData = (await res.json()) as ApiErrorResponse;
        if (errorData && errorData.message) {
          errorMessage += ` - ${errorData.message}`;
        } else if (errorData && errorData.error) {
          errorMessage += ` - ${errorData.error}`;
        }
      } catch (parseError) {
        // If parsing the error response fails, log it but proceed with the original error message
        console.error("Failed to parse error response:", parseError);
      }
      throw new Error(errorMessage);
    }

    return (await res.json()) as SourceDatabaseDatasetResponse;
  },
});

import { fetchWithSSE, SSEEvent } from "@/lib/sse-client";
import { useAuth } from "@/hooks/use-auth";

interface SourceDatabaseDatasetParams {
  alias: string;
  connection_string: string;
  created_by: string;
  driver: "postgres" | "mysql";
  project_id: string;
  sql_query: string;
  description?: string;
  custom_prompt?: string;
  timestamp_column?: string;
  onProgress: (event: SSEEvent) => void;
}

export const useSourceDatabaseDatasetSSE = () => {
  const { accessToken } = useAuth();

  return async (params: SourceDatabaseDatasetParams) => {
    return await fetchWithSSE(
      '/source/database/upload',
      {
        method: 'POST',
        body: JSON.stringify({
          alias: params.alias,
          connection_string: params.connection_string,
          created_by: params.created_by,
          description: params.description || "Dataset sourced from database via GoPie Web",
          driver: params.driver,
          project_id: params.project_id,
          sql_query: params.sql_query,
          custom_prompt: params.custom_prompt,
          timestamp_column: params.timestamp_column,
        }),
      },
      params.onProgress,
      accessToken
    );
  };
};
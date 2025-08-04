import { apiClient } from "@/lib/api-client";
import { createMutation } from "react-query-kit";

export type SqlQueryParams = {
  query: string;
  limit?: number;
  offset?: number;
};

export const useDatasetSql = createMutation({
  mutationKey: ["dataset-sql"],
  mutationFn: async (params: SqlQueryParams | string) => {
    const requestBody = typeof params === 'string' 
      ? { query: params }
      : params;
    
    return (await (
      await apiClient.post("v1/api/sql", {
        body: JSON.stringify(requestBody),
      })
    ).json()) as { data: Record<string, unknown>[] | null; count: number };
  },
});

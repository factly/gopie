import { apiClient } from "@/lib/api-client";
import { createMutation } from "react-query-kit";

export const useDatasetSql = createMutation({
  mutationKey: ["dataset-sql"],
  mutationFn: async (sql: string) => {
    return (await (
      await apiClient.post("v1/api/sql", {
        body: JSON.stringify({
          query: sql,
        }),
      })
    ).json()) as { data: Record<string, unknown>[]; total: number };
  },
});

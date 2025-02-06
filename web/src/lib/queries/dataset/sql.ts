import { apiClient } from "@/lib/api-client";
import { createQuery } from "react-query-kit";

export const useDatasetSql = createQuery({
  queryKey: ["dataset-sql"],
  fetcher: async ({ sql }: { sql: string }) => {
    return await (
      await apiClient.post("v1/api/sql", {
        body: JSON.stringify({
          query: sql,
        }),
      })
    ).json();
  },
});

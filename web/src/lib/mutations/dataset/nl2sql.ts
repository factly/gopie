import { apiClient } from "@/lib/api-client";
import { createMutation } from "react-query-kit";

export const useNl2Sql = createMutation({
  mutationKey: ["nl2sql"],
  mutationFn: async ({
    query,
    datasetId,
  }: {
    query: string;
    datasetId: string;
  }) => {
    return (await (
      await apiClient.post("v1/api/nl2sql", {
        body: JSON.stringify({
          query,
          table: datasetId,
        }),
        timeout: 60000, // 60 seconds timeout
        retry: 0, // Disable retries for nl2sql
      })
    ).json()) as {
      sql: string;
    };
  },
});

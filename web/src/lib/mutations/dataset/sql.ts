import { env } from "@/lib/env";
import ky from "ky";
import { createMutation } from "react-query-kit";

export const useDatasetSql = createMutation({
  mutationKey: ["dataset-sql"],
  mutationFn: async (sql: string) => {
    return (await (
      await ky.post(`${env.NEXT_PUBLIC_GOPIE_API_URL}/v1/api/sql`, {
        body: JSON.stringify({
          query: sql,
        }),
      })
    ).json()) as Record<string, unknown>[];
  },
});

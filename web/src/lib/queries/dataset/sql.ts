import { env } from "@/lib/env";
import ky from "ky";
import { createQuery } from "react-query-kit";

export const useDatasetSql = createQuery({
  queryKey: ["dataset-sql"],
  fetcher: async ({ sql }: { sql: string }) => {
    return await (
      await ky.post(`${env.NEXT_PUBLIC_GOPIE_API_URL}/v1/api/sql`, {
        body: JSON.stringify({
          query: sql,
        }),
        headers: {
          "Content-Type": "application/json",
        }
      })
    ).json();
  },
});

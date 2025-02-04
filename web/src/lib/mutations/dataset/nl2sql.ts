import { env } from "@/lib/env";
import ky from "ky";
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
      await ky.post(`${env.NEXT_PUBLIC_GOPIE_API_URL}/v1/api/nl2sql`, {
        body: JSON.stringify({
          query,
          table_name: datasetId,
        }),
      })
    ).json()) as {
      sql: string;
    };
  },
});

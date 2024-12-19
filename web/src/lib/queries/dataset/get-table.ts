import { env } from "@/lib/env";
import ky from "ky";
import { createQuery } from "react-query-kit";

export const useGetTable = createQuery({
  queryKey: ["get-table"],
  fetcher: async ({
    datasetId,
    page,
    limit,
    columns,
    sort,
    filter,
  }: {
    datasetId: string;
    page: number;
    limit: number;
    columns: string[];
    sort: {
      column: string;
      direction: "asc" | "desc";
    }[];
    filter?: {
      column: string;
      value: string;
      operator: "=" | ">" | "<" | ">=" | "<=";
    };
  }) => {
    const res = await ky.get(
      `${env.NEXT_PUBLIC_GOPIE_API_URL}/api/tables/${datasetId}`,
      {
        searchParams: {
          page,
          limit,
          columns: columns.join(","),
          sort: sort
            .map((s) => `${s.direction === "desc" ? "-" : ""}${s.column}`)
            .join(","),
        },
      }
    );
    return (await res.json()) as Record<string, any>[];
  },
});

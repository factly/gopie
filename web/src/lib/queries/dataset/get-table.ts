import { apiClient } from "@/lib/api-client";
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
    filter: {
      column: string;
      value: string;
      operator: "e" | "gt" | "lt";
    }[];
  }) => {
    const res = await apiClient.get(
      `v1/api/tables/${datasetId}`,
      {
        searchParams: {
          page,
          limit,
          columns: columns.join(","),
          sort: sort
            .map((s) => `${s.direction === "desc" ? "-" : ""}${s.column}`)
            .join(","),
          ...Object.fromEntries(
            filter.map((f) => [
              `filter[${f.column}]${f.operator === "e" ? "" : f.operator}`,
              f.value,
            ]),
          ),
        },
      },
    );
    return (await res.json()) as {
      data: Record<string, unknown>[];
      total: number;
    };
  },
});

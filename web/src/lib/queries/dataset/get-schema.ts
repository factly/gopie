// TODO: remove `any`s from this file
/* eslint-disable @typescript-eslint/no-explicit-any */
import { apiClient } from "@/lib/api-client";
import { createQuery } from "react-query-kit";

export interface ColumnInfo {
  column_name: string;
  column_type: string;
  default: any;
  extra: any;
  key: any;
  null: "YES" | "NO";
}

const fetchSchema = async ({ datasetId }: { datasetId: string }) => {
  return (await (
    await apiClient.get(`v1/api/schemas/${datasetId}`)
  ).json()) as { schema: ColumnInfo[] };
};

export const useSchema = createQuery({
  queryKey: ["get-schema"],
  fetcher: fetchSchema,
});

// TODO: this is temporary, there should be only a single call to get schemas
// but projects API is not yet implemented
export const useSchemas = createQuery({
  queryKey: ["get-schemas"],
  fetcher: async ({ datasetIds }: { datasetIds: string[] }) => {
    return await Promise.all(
      datasetIds.map(async (datasetId) => {
        return fetchSchema({ datasetId });
      }),
    );
  },
});

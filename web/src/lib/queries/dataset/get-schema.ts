// TODO: remove `any`s from this file
/* eslint-disable @typescript-eslint/no-explicit-any */
import { env } from "@/lib/env";
import ky from "ky";
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
    await ky.get(`${env.NEXT_PUBLIC_GOPIE_API_URL}/api/schema/${datasetId}`)
  ).json()) as ColumnInfo[];
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
      })
    );
  },
});

import { env } from "@/lib/env";
import ky from "ky";
import { createQuery } from "react-query-kit";

interface ColumnInfo {
  column_name: string;
  column_type: string;
  default: any;
  extra: any;
  key: any;
  null: "YES" | "NO";
}

export const useGetSchema = createQuery({
  queryKey: ["get-schema"],
  fetcher: async ({ datasetId }: { datasetId: string }) => {
    return (await (
      await ky.get(`${env.NEXT_PUBLIC_GOPIE_API_URL}/api/schema/${datasetId}`)
    ).json()) as ColumnInfo[];
  },
});

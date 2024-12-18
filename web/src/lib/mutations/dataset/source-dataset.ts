import { createMutation } from "react-query-kit";
import { env } from "@/lib/env";
import ky from "ky";

interface Response {
  message: string;
  tableName: string;
}

export const useSourceDataset = createMutation({
  mutationKey: ["source-dataset"],
  mutationFn: async ({ datasetUrl }: { datasetUrl: string }) => {
    const res = await ky.post(`${env.NEXT_PUBLIC_GOPIE_API_URL}/source/s3`, {
      body: JSON.stringify({
        path: datasetUrl,
      }),
    });

    if (!res.ok) {
      throw new Error("Failed to source dataset");
    }

    return (await res.json()) as Response;
  },
});

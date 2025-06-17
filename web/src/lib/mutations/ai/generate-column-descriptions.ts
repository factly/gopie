import { createMutation } from "react-query-kit";
import { apiClient } from "@/lib/api-client";

interface GenerateColumnDescriptionsRequest {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  summary: Record<string, any>;
  rows: string[][];
}

interface GenerateColumnDescriptionsResponse {
  descriptions: Record<string, string>;
}

export const useGenerateColumnDescriptions = createMutation({
  mutationKey: ["generate-column-descriptions"],
  mutationFn: async ({ summary, rows }: GenerateColumnDescriptionsRequest) => {
    const res = await apiClient.post("v1/api/ai/generate-column-descriptions", {
      body: JSON.stringify({
        summary,
        rows,
      }),
    });

    if (!res.ok) {
      throw new Error("Failed to generate column descriptions");
    }

    return (await res.json()) as GenerateColumnDescriptionsResponse;
  },
});

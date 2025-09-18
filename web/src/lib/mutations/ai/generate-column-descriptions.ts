import { createMutation } from "react-query-kit";
import { apiClient } from "@/lib/api-client";
import { sanitizeForSerialization } from "@/lib/utils/serialization";

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
    // Sanitize the data to handle BigInt and other non-serializable values
    const sanitizedSummary = sanitizeForSerialization(summary);
    const sanitizedRows = sanitizeForSerialization(rows);
    
    const res = await apiClient.post("v1/api/ai/generate-column-descriptions", {
      body: JSON.stringify({
        summary: sanitizedSummary,
        rows: sanitizedRows,
      }),
    });

    if (!res.ok) {
      throw new Error("Failed to generate column descriptions");
    }

    return (await res.json()) as GenerateColumnDescriptionsResponse;
  },
});

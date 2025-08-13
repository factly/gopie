import { createMutation } from "react-query-kit";
import { apiClient } from "@/lib/api-client";
import { jsonReplacer } from "@/lib/utils/serialization";

interface GenerateDatasetDescriptionRequest {
  datasetName: string;
  columnNames: string[];
  columnDescriptions?: Record<string, string>;
  rows: string[][];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  summary?: Record<string, any>;
}

interface GenerateDatasetDescriptionResponse {
  description: string;
}

export const useGenerateDatasetDescription = createMutation({
  mutationKey: ["generate-dataset-description"],
  mutationFn: async ({
    datasetName,
    columnNames,
    columnDescriptions,
    rows,
    summary,
  }: GenerateDatasetDescriptionRequest) => {
    const res = await apiClient.post("v1/api/ai/generate-dataset-description", {
      body: JSON.stringify({
        datasetName,
        columnNames,
        columnDescriptions: columnDescriptions || {},
        rows,
        summary: summary || {},
      }, jsonReplacer),
    });

    if (!res.ok) {
      throw new Error("Failed to generate dataset description");
    }

    return (await res.json()) as GenerateDatasetDescriptionResponse;
  },
});
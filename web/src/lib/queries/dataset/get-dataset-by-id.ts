import { Dataset } from "@/lib/api-client";
import { apiClient } from "@/lib/api-client";
import { createQuery } from "react-query-kit";

interface GetDatasetByIdParams {
  datasetId: string;
}

async function fetchDatasetById({
  datasetId,
}: GetDatasetByIdParams): Promise<Dataset> {
  try {
    const response = await apiClient.get(`v1/api/datasets/${datasetId}`);
    // Assuming the response directly returns the Dataset object, similar to other GET by ID endpoints
    return response.json();
  } catch (error) {
    // It's good practice to log the actual error or handle it more specifically
    console.error("Failed to fetch dataset by ID:", error);
    throw new Error(
      "Failed to fetch dataset by ID: " +
        (error instanceof Error ? error.message : String(error))
    );
  }
}

export const useDatasetById = createQuery<Dataset, GetDatasetByIdParams, Error>(
  {
    queryKey: ["dataset-by-id"], // Unique query key
    fetcher: fetchDatasetById,
  }
);

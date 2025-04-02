import { Dataset, PaginatedResponse } from "@/lib/api-client";
import { apiClient } from "@/lib/api-client";
import { createQuery } from "react-query-kit";

interface ListDatasetsParams {
  projectId: string;
  limit?: number;
  page?: number;
  query?: string;
}

export async function fetchDatasets({
  projectId,
  limit = 10,
  page = 1,
  query,
}: ListDatasetsParams): Promise<PaginatedResponse<Dataset>> {
  if (!projectId) {
    return {
      results: [],
      offset: 0,
      limit: 0,
      total: 0,
    };
  }
  try {
    const searchParams = new URLSearchParams({
      limit: limit.toString(),
      page: page.toString(),
    });

    if (query) {
      searchParams.append("query", query);
    }

    const response = await apiClient.get(
      `v1/api/projects/${projectId}/datasets/?${searchParams}`
    );
    return response.json();
  } catch (error) {
    throw new Error("Failed to fetch datasets: " + error);
  }
}

export const useDatasets = createQuery({
  queryKey: ["datasets"],
  fetcher: fetchDatasets,
});

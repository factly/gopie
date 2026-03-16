import { Dataset, PaginatedResponse } from "@/lib/api-client";
import { apiClient } from "@/lib/api-client";
import { createQuery } from "react-query-kit";
import { useInfiniteQuery } from "@tanstack/react-query";
interface ListDatasetsParams {
  projectId: string;
  limit?: number;
  page?: number;
  query?: string;
}

export async function fetchDatasets({
  projectId,
  limit = 100,
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

export const useDatasetsInfinite = (projectId: string, limit = 12) => {
  return useInfiniteQuery<PaginatedResponse<Dataset>, Error>({
    queryKey: ["datasets", projectId, "infinite"],
    initialPageParam: 1,
    enabled: !!projectId,
    queryFn: ({ pageParam }) => 
      fetchDatasets({ 
        projectId, 
        limit, 
        page: pageParam as number 
      }),
    getNextPageParam: (lastPage, allPages) => {
      // Handle null results
      const results = lastPage.results || [];
      // If results are empty or less than limit, we are done
      if (results.length < limit) return undefined;
      
      const totalPages = Math.ceil(lastPage.total / limit);
      const nextPage = allPages.length + 1;
      return nextPage <= totalPages ? nextPage : undefined;
    },
  });
};
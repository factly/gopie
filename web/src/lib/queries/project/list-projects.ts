import { Project, PaginatedResponse } from "@/lib/api-client";
import { apiClient } from "@/lib/api-client";
import { createQuery } from "react-query-kit";
import { useInfiniteQuery } from "@tanstack/react-query";

interface ListProjectsParams {
  limit?: number;
  page?: number;
  query?: string;
}

async function fetchProjects({
  limit = 100,
  page = 1,
  query,
}: ListProjectsParams = {}): Promise<PaginatedResponse<Project>> {
  try {
    const searchParams = new URLSearchParams({
      limit: limit.toString(),
      page: page.toString(),
    });

    if (query) {
      searchParams.append("query", query);
    }

    const response = await apiClient.get(`v1/api/projects/?${searchParams}`);
    return response.json();
  } catch (error) {
    throw new Error("Failed to fetch projects: " + error);
  }
}

export const useProjects = createQuery({
  queryKey: ["projects"],
  fetcher: fetchProjects,
});

export const useProjectsInfinite = (limit = 12) => {
  return useInfiniteQuery<PaginatedResponse<Project>, Error>({
    queryKey: ["projects", "infinite"],
    initialPageParam: 1,
    queryFn: ({ pageParam }) => 
      fetchProjects({ 
        limit, 
        page: pageParam as number 
      }),
    getNextPageParam: (lastPage, allPages) => {
      // Handle null results
      const results = lastPage.results || [];
      
      if (results.length < limit) return undefined;
      const totalPages = Math.ceil(lastPage.total / limit);
      const nextPage = allPages.length + 1;
      return nextPage <= totalPages ? nextPage : undefined;
    },
  });
};

import { Project, PaginatedResponse } from "@/lib/api-client";
import { apiClient } from "@/lib/api-client";
import { createQuery } from "react-query-kit";

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

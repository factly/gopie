import { apiClient } from "@/lib/api-client";
import { createQuery } from "react-query-kit";

export interface DatabaseSource {
  id: string;
  connection_string: string;
  sql_query: string;
  created_at: string;
  updated_at: string;
}

interface ListDatabaseSourcesParams {
  limit?: number;
  page?: number;
}

interface ListDatabaseSourcesResponse {
  data: DatabaseSource[];
  total?: number;
}

async function fetchDatabaseSources({
  limit = 20,
  page = 1,
}: ListDatabaseSourcesParams = {}): Promise<ListDatabaseSourcesResponse> {
  try {
    const searchParams = new URLSearchParams({
      limit: limit.toString(),
      page: page.toString(),
    });

    const response = await apiClient.get(`source/database?${searchParams}`);
    return response.json();
  } catch (error) {
    throw new Error("Failed to fetch database sources: " + error);
  }
}

export const useDatabaseSources = createQuery({
  queryKey: ["database-sources"],
  fetcher: fetchDatabaseSources,
});

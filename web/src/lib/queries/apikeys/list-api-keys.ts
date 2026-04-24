import { apiClient } from "@/lib/api-client";
import { createQuery } from "react-query-kit";

export interface APIKey {
  id: string;
  name: string;
  description: string;
  created_by: string;
  is_revoked: boolean;
  last_used_at: string | null;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
}

interface ListAPIKeysParams {
  limit?: number;
  page?: number;
}

interface ListAPIKeysResponse {
  results: APIKey[];
  total: number;
  limit: number;
  offset: number;
}

async function fetchAPIKeys({ limit = 50, page = 1 }: ListAPIKeysParams = {}): Promise<ListAPIKeysResponse> {
  const searchParams = new URLSearchParams({
    limit: limit.toString(),
    page: page.toString(),
  });
  return apiClient.get(`apikeys?${searchParams}`).json<ListAPIKeysResponse>();
}

export const useAPIKeys = createQuery({
  queryKey: ["api-keys"],
  fetcher: fetchAPIKeys,
});

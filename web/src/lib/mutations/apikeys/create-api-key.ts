import { apiClient } from "@/lib/api-client";
import { createMutation } from "react-query-kit";
import type { APIKey } from "@/lib/queries/apikeys/list-api-keys";

interface CreateAPIKeyParams {
  name: string;
  description?: string;
}

export interface CreateAPIKeyResponse {
  apikey: APIKey;
  key: string;
}

async function createAPIKey(params: CreateAPIKeyParams): Promise<CreateAPIKeyResponse> {
  return apiClient.post("apikeys", { json: params }).json<CreateAPIKeyResponse>();
}

export const useCreateAPIKey = createMutation({
  mutationKey: ["create-api-key"],
  mutationFn: createAPIKey,
});

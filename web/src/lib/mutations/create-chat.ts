import { apiClient } from "@/lib/api-client";

export interface CreateChatParams {
  title?: string;
  dataset_ids?: string[];
  project_ids?: string[];
}

export interface CreateChatResponse {
  id: string;
  title: string;
  created_at: string;
}

export async function createChat(params: CreateChatParams): Promise<CreateChatResponse> {
  const response = await apiClient.post("v1/api/chat/create", {
    json: params,
  });

  return response.json();
}
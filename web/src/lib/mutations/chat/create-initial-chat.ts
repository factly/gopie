import { createMutation } from "react-query-kit";
import { apiClient } from "@/lib/api-client";

interface CreateInitialChatParams {
  title?: string;
  datasetIds?: string[];
  projectIds?: string[];
}

interface CreateInitialChatResponse {
  id: string;
  title: string;
  created_at: string;
}

export const useCreateInitialChat = createMutation({
  mutationKey: ["create-initial-chat"],
  mutationFn: async (
    params: CreateInitialChatParams
  ): Promise<CreateInitialChatResponse> => {
    const response = await apiClient.post("v1/api/chat/create", {
      json: {
        title: params.title,
        dataset_ids: params.datasetIds || [],
        project_ids: params.projectIds || [],
      },
    });

    return response.json();
  },
});
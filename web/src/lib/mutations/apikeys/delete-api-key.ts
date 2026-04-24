import { apiClient } from "@/lib/api-client";
import { createMutation } from "react-query-kit";

async function deleteAPIKey({ id }: { id: string }): Promise<void> {
  await apiClient.delete(`apikeys/${id}`);
}

export const useDeleteAPIKey = createMutation({
  mutationKey: ["delete-api-key"],
  mutationFn: deleteAPIKey,
});

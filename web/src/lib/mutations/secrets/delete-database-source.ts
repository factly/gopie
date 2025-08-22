import { createMutation } from "react-query-kit";
import { apiClient } from "@/lib/api-client";

interface DeleteDatabaseSourceParams {
  id: string;
}

interface ApiErrorResponse {
  code?: number;
  error?: string;
  message?: string;
}

async function deleteDatabaseSource({
  id,
}: DeleteDatabaseSourceParams): Promise<void> {
  try {
    const response = await apiClient.delete(`source/database/${id}`);

    if (!response.ok) {
      let errorMessage = `Failed to delete database source: ${response.status} ${response.statusText}`;
      try {
        const errorData = (await response.json()) as ApiErrorResponse;
        if (errorData && errorData.message) {
          errorMessage += ` - ${errorData.message}`;
        } else if (errorData && errorData.error) {
          errorMessage += ` - ${errorData.error}`;
        }
      } catch (parseError) {
        console.error("Failed to parse error response:", parseError);
      }
      throw new Error(errorMessage);
    }
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Failed to delete database source: " + error);
  }
}

export const useDeleteDatabaseSource = createMutation({
  mutationKey: ["delete-database-source"],
  mutationFn: deleteDatabaseSource,
});

import { apiClient } from "@/lib/api-client";
import { createMutation } from "react-query-kit";

export type SqlQueryParams = {
  query: string;
  limit?: number;
  offset?: number;
};

export const useDatasetSql = createMutation({
  mutationKey: ["dataset-sql"],
  mutationFn: async (params: SqlQueryParams | string) => {
    const requestBody = typeof params === 'string' 
      ? { query: params }
      : params;
    
    try {
      const response = await apiClient.post("v1/api/sql", {
        body: JSON.stringify(requestBody),
      });
      
      return (await response.json()) as { 
        data: Record<string, unknown>[] | null; 
        count: number; 
        columns?: string[]; 
        executionTime?: number 
      };
    } catch (error: any) {
      // If it's a ky HTTPError, extract the response
      if (error.name === 'HTTPError' && error.response) {
        const errorData = await error.response.json().catch(() => null);
        // Attach the parsed error data to the error object
        error.errorData = errorData;
      }
      throw error;
    }
  },
});

import ky from "ky";
import { ColumnInfo } from "@/lib/queries/dataset/get-schema";

export const apiClient = ky.create({
  prefixUrl: process.env.NEXT_PUBLIC_GOPIE_API_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: false, // Disable timeout
  // Or if you want a very long timeout instead of disabling:
  // timeout: 300000, // 5 minutes in milliseconds
});

// Project Types
export interface ProjectInput {
  name: string;
  description: string;
  created_by: string;
}

export interface Project extends ProjectInput {
  id: string;
  createdAt: string;
  updatedAt: string;
  datasetCount: number;
  createdBy: string;
  updatedBy: string;
}

// Dataset Types
export interface Dataset {
  id: string;
  name: string;
  alias: string;
  description: string;
  format: string;
  row_count: number;
  columns: ColumnInfo[];
  size: number;
  file_path: string;
  created_at: string;
  updated_at: string;
  created_by: string;
  updated_by: string;
}

// Chat Types
export interface ChatMessage {
  id: string;
  content: string;
  role: "user" | "assistant" | "intermediate" | "ai";
  created_at: string;
}

export interface Chat {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  created_by: string;
}

export interface ChatWithMessages extends Chat {
  messages: ChatMessage[];
}

// API Response Types
export interface PaginatedResponse<T> {
  results: T[];
  offset: number;
  limit: number;
  total: number;
}

export interface ApiOptions extends RequestInit {
  requireAuth?: boolean;
}

// Utility hook for making authenticated API requests
import { useAuth } from "@/hooks/use-auth";

export function useApiClient() {
  const { accessToken } = useAuth();

  const makeRequest = async (endpoint: string, options: ApiOptions = {}) => {
    const {
      requireAuth = false,
      headers: customHeaders,
      ...restOptions
    } = options;

    const headers: HeadersInit = {
      "Content-Type": "application/json",
      ...(customHeaders as Record<string, string>),
    };

    // Add authentication header if required and access token is available
    if (requireAuth && accessToken) {
      (
        headers as Record<string, string>
      ).Authorization = `Bearer ${accessToken}`;
    } else if (requireAuth && !accessToken) {
      throw new Error("Access token not available for authenticated request");
    }

    const response = await fetch(endpoint, {
      ...restOptions,
      headers,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API request failed: ${response.status} - ${errorText}`);
    }

    // Handle empty responses
    const contentType = response.headers.get("content-type");
    if (contentType && contentType.includes("application/json")) {
      return response.json();
    }

    return response.text();
  };

  return {
    get: (endpoint: string, options: ApiOptions = {}) =>
      makeRequest(endpoint, { ...options, method: "GET" }),

    post: (endpoint: string, data?: unknown, options: ApiOptions = {}) =>
      makeRequest(endpoint, {
        ...options,
        method: "POST",
        body: data ? JSON.stringify(data) : undefined,
      }),

    put: (endpoint: string, data?: unknown, options: ApiOptions = {}) =>
      makeRequest(endpoint, {
        ...options,
        method: "PUT",
        body: data ? JSON.stringify(data) : undefined,
      }),

    patch: (endpoint: string, data?: unknown, options: ApiOptions = {}) =>
      makeRequest(endpoint, {
        ...options,
        method: "PATCH",
        body: data ? JSON.stringify(data) : undefined,
      }),

    delete: (endpoint: string, options: ApiOptions = {}) =>
      makeRequest(endpoint, { ...options, method: "DELETE" }),
  };
}

import ky from "ky";
import { ColumnInfo } from "@/lib/queries/dataset/get-schema";

// Global access token management
class TokenManager {
  private token: string | null = null;
  private organizationId: string | null = null;

  setToken(token: string | null) {
    this.token = token;
  }

  getToken(): string | null {
    return this.token;
  }

  setOrganizationId(organizationId: string | null) {
    this.organizationId = organizationId;
  }

  getOrganizationId(): string | null {
    return this.organizationId;
  }
}

const tokenManager = new TokenManager();

// Functions to manage global access token
export function setGlobalAccessToken(token: string | null) {
  tokenManager.setToken(token);
}

export function getGlobalAccessToken(): string | null {
  return tokenManager.getToken();
}

// Functions to manage global organization id
export function setGlobalOrganizationId(organizationId: string | null) {
  tokenManager.setOrganizationId(organizationId);
}

export function getGlobalOrganizationId(): string | null {
  return tokenManager.getOrganizationId();
}

export const apiClient = ky.create({
  prefixUrl: process.env.NEXT_PUBLIC_GOPIE_API_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: false, // Disable timeout
  // Or if you want a very long timeout instead of disabling:
  // timeout: 300000, // 5 minutes in milliseconds
  hooks: {
    beforeRequest: [
      (request) => {
        const token = getGlobalAccessToken();
        if (token && !request.headers.get("Authorization")) {
          request.headers.set("Authorization", `Bearer ${token}`);
        }

        const orgId = getGlobalOrganizationId();
        if (orgId && !request.headers.get("x-organization-id")) {
          request.headers.set("x-organization-id", orgId);
        }
      },
    ],
  },
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
  visibility?: "public" | "private" | "organization";
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

// Legacy hook for backward compatibility - authentication is now automatic via apiClient
// @deprecated Use apiClient directly instead
export function useApiClient() {
  return {
    get: (endpoint: string, options: Record<string, unknown> = {}) =>
      apiClient.get(endpoint, options).json(),

    post: (
      endpoint: string,
      data?: unknown,
      options: Record<string, unknown> = {}
    ) => apiClient.post(endpoint, { json: data, ...options }).json(),

    put: (
      endpoint: string,
      data?: unknown,
      options: Record<string, unknown> = {}
    ) => apiClient.put(endpoint, { json: data, ...options }).json(),

    patch: (
      endpoint: string,
      data?: unknown,
      options: Record<string, unknown> = {}
    ) => apiClient.patch(endpoint, { json: data, ...options }).json(),

    delete: (endpoint: string, options: Record<string, unknown> = {}) =>
      apiClient.delete(endpoint, options).json(),
  };
}

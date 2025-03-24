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
  role: "user" | "assistant";
  created_at: string;
}

export interface Chat {
  id: string;
  name: string;
  created_by: string;
  created_at: string;
  updated_at: string;
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

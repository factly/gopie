import ky from "ky";
import { env } from "@/lib/env";
import { ColumnInfo } from "@/lib/queries/dataset/get-schema";

export const apiClient = ky.create({
  prefixUrl: env.NEXT_PUBLIC_GOPIE_API_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Project Types
export interface ProjectInput {
  name: string;
  description: string;
}

export interface Project extends ProjectInput {
  id: string;
  createdAt: string;
  updatedAt: string;
  datasetCount: number;
}

// Dataset Types
export interface Dataset {
  id: string;
  name: string;
  description: string;
  format: string;
  row_count: number;
  columns: ColumnInfo[];
  size: number;
  file_path: string;
  created_at: string;
  updated_at: string;
}

// API Response Types
export interface PaginatedResponse<T> {
  results: T[];
  offset: number;
  limit: number;
  total: number;
}

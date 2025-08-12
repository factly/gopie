import { create } from 'zustand';

export interface Download {
  id: string;
  sql: string;
  dataset_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  format: 'csv' | 'json' | 'parquet';
  pre_signed_url?: string;
  error_message?: string;
  created_at: string;
  updated_at: string;
  expires_at?: string;
  completed_at?: string;
  user_id: string;
  org_id: string;
}

export interface DownloadProgress {
  downloadId?: string;
  progress: number;
  message: string;
  status: 'idle' | 'processing' | 'completed' | 'error';
  url?: string;
}

interface DownloadStore {
  downloads: Download[];
  currentDownloadProgress: DownloadProgress | null;
  isLoading: boolean;
  error: string | null;
  
  setDownloads: (downloads: Download[]) => void;
  addDownload: (download: Download) => void;
  removeDownload: (id: string) => void;
  setCurrentDownloadProgress: (progress: DownloadProgress | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

export const useDownloadStore = create<DownloadStore>((set) => ({
  downloads: [],
  currentDownloadProgress: null,
  isLoading: false,
  error: null,
  
  setDownloads: (downloads) => set({ downloads }),
  addDownload: (download) => set((state) => ({ 
    downloads: [download, ...state.downloads] 
  })),
  removeDownload: (id) => set((state) => ({ 
    downloads: state.downloads.filter(d => d.id !== id) 
  })),
  setCurrentDownloadProgress: (progress) => set({ currentDownloadProgress: progress }),
  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error }),
  reset: () => set({ 
    downloads: [], 
    currentDownloadProgress: null, 
    isLoading: false, 
    error: null 
  }),
}));
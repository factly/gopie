import { useDownloadStore } from "@/lib/stores/download-store";
import { useAuth } from "@/hooks/use-auth";
import { getGlobalOrganizationId } from "@/lib/api-client";

export interface CreateDownloadRequest {
  dataset_id: string;
  sql: string;
  format: 'csv' | 'json' | 'parquet';
}

export interface SSEMessage {
  type: 'progress' | 'complete' | 'error';
  message?: string;
  progress?: number;
  download_id?: string;
  url?: string;
}

export const createDownloadWithSSE = async (
  params: CreateDownloadRequest,
  onProgress?: (data: SSEMessage) => void,
  accessToken?: string | null
) => {
  const baseUrl = process.env.NEXT_PUBLIC_GOPIE_API_URL || 'http://localhost:8000';
  const url = `${baseUrl}/v1/api/downloads`;
  
  const isAuthEnabled = String(process.env.NEXT_PUBLIC_ENABLE_AUTH).trim() === "true";
  const orgId = getGlobalOrganizationId();
  
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  
  // Add authentication headers
  if (accessToken) {
    headers['Authorization'] = `Bearer ${accessToken}`;
  }
  
  // Add organization header
  if (!isAuthEnabled) {
    headers['x-user-id'] = 'system';
    headers['x-organization-id'] = 'system';
  } else if (orgId) {
    headers['x-organization-id'] = orgId;
  }
  
  const response = await fetch(url, {
    method: 'POST',
    headers,
    body: JSON.stringify(params)
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.message || 'Failed to create download');
  }

  if (!response.body) {
    throw new Error('No response body');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  return new Promise<{ downloadId: string; url: string }>((resolve, reject) => {
    const processStream = async () => {
      try {
        while (true) {
          const { done, value } = await reader.read();
          
          if (done) break;
          
          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split('\n');
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const jsonStr = line.slice(6);
              if (jsonStr.trim()) {
                try {
                  const data = JSON.parse(jsonStr) as SSEMessage;
                  
                  if (onProgress) {
                    onProgress(data);
                  }
                  
                  if (data.type === 'complete' && data.download_id && data.url) {
                    resolve({ downloadId: data.download_id, url: data.url });
                    return;
                  }
                  
                  if (data.type === 'error') {
                    reject(new Error(data.message || 'Download failed'));
                    return;
                  }
                } catch (e) {
                  console.error('Failed to parse SSE message:', e);
                }
              }
            }
          }
        }
      } catch (error) {
        reject(error);
      }
    };

    processStream();
  });
};

export const useCreateDownload = () => {
  const { accessToken } = useAuth();
  const { setCurrentDownloadProgress, setError } = useDownloadStore();

  const createDownload = async (params: CreateDownloadRequest) => {
    setError(null);
    setCurrentDownloadProgress({
      progress: 0,
      message: 'Initializing download...',
      status: 'processing'
    });

    try {
      const result = await createDownloadWithSSE(
        params,
        (data) => {
          if (data.type === 'progress') {
            setCurrentDownloadProgress({
              progress: data.progress || 0,
              message: data.message || 'Processing...',
              status: 'processing'
            });
          } else if (data.type === 'complete') {
            setCurrentDownloadProgress({
              downloadId: data.download_id,
              progress: 100,
              message: 'Download complete!',
              status: 'completed',
              url: data.url
            });
          } else if (data.type === 'error') {
            setCurrentDownloadProgress({
              progress: 0,
              message: data.message || 'Download failed',
              status: 'error'
            });
            setError(data.message || 'Download failed');
          }
        },
        accessToken
      );

      return result;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Download failed';
      setError(errorMessage);
      setCurrentDownloadProgress({
        progress: 0,
        message: errorMessage,
        status: 'error'
      });
      throw error;
    }
  };

  return { createDownload };
};
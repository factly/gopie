import { getGlobalOrganizationId } from "@/lib/api-client";

export interface SSEEvent<T = unknown> {
  type: 'status_update' | 'progress' | 'complete' | 'error';
  message: string;
  data?: T;
  progress?: number;
}

export async function fetchWithSSE<T = unknown>(
  url: string,
  options: RequestInit,
  onEvent: (event: SSEEvent<T>) => void,
  accessToken?: string | null
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  // Add Auth & Org Headers (Reusing logic from api-client)
const isAuthEnabled = String(process.env.NEXT_PUBLIC_ENABLE_AUTH).trim() === "true";
  const orgId = getGlobalOrganizationId();

  // Token
  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`;
  }

  // Org / User handling
  if (!isAuthEnabled) {
    headers["x-user-id"] = "system";
    headers["x-organization-id"] = "system";
  } else if (orgId) {
    headers["x-organization-id"] = orgId;
  }

  const response = await fetch(process.env.NEXT_PUBLIC_GOPIE_API_URL + url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorMsg = 'Request failed';
    try {
        const error = await response.json();
        errorMsg = error.message || error.error || errorMsg;
    } catch {
        // ignore json parse error
    }
    throw new Error(errorMsg);
  }

  if (!response.body) throw new Error('No response body');

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let resultData: T | undefined;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value, { stream: true });
    const lines = chunk.split('\n');

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const jsonStr = line.slice(6);
          if (!jsonStr.trim()) continue;
          
          const event = JSON.parse(jsonStr);
          
          // Map backend event types to frontend expected types if necessary
          // Server sends: "status_update", "complete", "error"
          onEvent(event);

          if (event.type === 'complete') {
            resultData = event.data;
          }
          if (event.type === 'error') {
            throw new Error(event.message);
          }
        } catch (e) {
          if (e instanceof Error && e.message !== "Unexpected end of JSON input") {
             console.error("SSE Parse Error", e);
          }
          if (line.includes('"type":"error"')) throw e; // Re-throw actual errors
        }
      }
    }
  }

  return resultData as T;
}
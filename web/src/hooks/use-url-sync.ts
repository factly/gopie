import { useCallback, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ContextItem } from "@/components/chat/context-picker";

interface UseUrlSyncProps {
  selectedChatId: string | null;
  isInitialized: boolean;
}

export function useUrlSync({ selectedChatId, isInitialized }: UseUrlSyncProps) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const chatIdFromUrl = searchParams.get("chatId");

  // Helper function to update URL with chat state
  const updateUrlWithChatId = useCallback(
    (chatId: string | null) => {
      const params = new URLSearchParams(searchParams.toString());
      if (chatId) {
        params.set("chatId", chatId);
      } else {
        params.delete("chatId");
        params.delete("initialMessage");
        params.delete("contextData");
      }
      router.replace(`/chat?${params.toString()}`);
    },
    [searchParams, router]
  );

  // Helper function to update URL with context data
  const updateUrlWithContext = useCallback(
    (contexts: ContextItem[]) => {
      const params = new URLSearchParams(searchParams.toString());
      if (contexts.length > 0) {
        params.set("contexts", encodeURIComponent(JSON.stringify(contexts)));
      } else {
        params.delete("contexts");
      }
      router.replace(`/chat?${params.toString()}`);
    },
    [searchParams, router]
  );

  // Update URL when selectedChatId changes
  useEffect(() => {
    if (isInitialized && selectedChatId !== chatIdFromUrl) {
      updateUrlWithChatId(selectedChatId);
    }
  }, [selectedChatId, chatIdFromUrl, updateUrlWithChatId, isInitialized]);

  // Function to clean up URL parameters
  const cleanupUrlParams = useCallback(
    (paramsToDelete: string[]) => {
      const params = new URLSearchParams(searchParams.toString());
      paramsToDelete.forEach((param) => params.delete(param));
      router.replace(`/chat?${params.toString()}`);
    },
    [searchParams, router]
  );

  // Function to update tab parameter
  const updateTabParam = useCallback(
    (tab: string | null) => {
      const params = new URLSearchParams(searchParams.toString());
      if (tab === "history") {
        params.set("tab", "history");
      } else {
        params.delete("tab");
      }
      router.replace(`/chat?${params.toString()}`);
    },
    [searchParams, router]
  );

  return {
    updateUrlWithChatId,
    updateUrlWithContext,
    cleanupUrlParams,
    updateTabParam,
    chatIdFromUrl,
    initialMessage: searchParams.get("initialMessage"),
    contextData: searchParams.get("contextData"),
    contextsFromUrl: searchParams.get("contexts"),
    tabFromUrl: searchParams.get("tab"),
  };
}
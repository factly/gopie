import React, { useCallback } from "react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { MessageSquarePlus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { useChatStore } from "@/lib/stores/chat-store";
import { useChats } from "@/lib/queries/chat/list-chats";
import { useDeleteChat } from "@/lib/mutations/chat";
import { useSqlStore } from "@/lib/stores/sql-store";
import { useVisualizationStore } from "@/lib/stores/visualization-store";
import { useResultsPanelStore } from "@/lib/stores/results-panel-store";
import { useQueryClient } from "@tanstack/react-query";
import { ContextItem } from "./context-picker";

interface ChatHistoryListProps {
  currentUserId: string;
  onTabChange: (tab: string) => void;
  onContextChange: (contexts: ContextItem[]) => void;
  onLinkedDatasetChange: (datasetId: string | null) => void;
  onUrlUpdate: (contexts: ContextItem[]) => void;
  onScrollReset: () => void;
}

export const ChatHistoryList = React.memo(function ChatHistoryList({
  currentUserId,
  onTabChange,
  onContextChange,
  onLinkedDatasetChange,
  onUrlUpdate,
  onScrollReset,
}: ChatHistoryListProps) {
  const { selectChatForDataset, selectedChatId } = useChatStore();
  const queryClient = useQueryClient();
  const { resetExecutedQueries, setIsOpen, setResults } = useSqlStore();
  const {
    clearPaths: clearVisualizationPaths,
    setIsOpen: setVisualizationOpen,
  } = useVisualizationStore();
  const { setActiveTab: setResultsPanelActiveTab } = useResultsPanelStore();

  const deleteChat = useDeleteChat();

  // Use the infinite query hook
  const {
    data: chatsData,
    isLoading,
    error,
  } = useChats({
    variables: { userID: currentUserId, limit: 100 },
  });

  const allChats = chatsData?.pages?.flatMap((page) => page.data.results)
    .filter((chat) => chat !== null && chat !== undefined) ?? [];

  const handleChatSelect = useCallback(
    (chatId: string, chatTitle: string, linkedDatasetId?: string) => {
      // Reset stores before switching
      resetExecutedQueries();
      clearVisualizationPaths();
      // Don't close the panels - they will be opened when SQL/viz is loaded
      // Just reset the active tab to SQL as default
      setResultsPanelActiveTab("sql");

      // Reset context
      onContextChange([]);
      onLinkedDatasetChange(linkedDatasetId || null);

      // Update URL with cleared context
      onUrlUpdate([]);

      // Select the chat
      selectChatForDataset(null, chatId, chatTitle);

      // Reset scroll states
      onScrollReset();

      // Switch to chat tab
      onTabChange("chat");

      // Invalidate and refetch messages for the selected chat
      queryClient.invalidateQueries({
        queryKey: ["chat-messages", chatId],
      });
    },
    [
      resetExecutedQueries,
      clearVisualizationPaths,
      setResultsPanelActiveTab,
      onContextChange,
      onLinkedDatasetChange,
      onUrlUpdate,
      selectChatForDataset,
      onScrollReset,
      onTabChange,
      queryClient,
    ]
  );

  const handleDeleteChat = useCallback(
    async (e: React.MouseEvent, chatId: string) => {
      e.stopPropagation();
      try {
        await deleteChat.mutateAsync({
          chatId,
          userId: currentUserId,
        });

        // Invalidate and refetch the chats query to update the UI
        await queryClient.invalidateQueries({ queryKey: ["chats"] });

        toast.success("Chat deleted successfully");

        if (selectedChatId === chatId) {
          selectChatForDataset(null, null, null);
          onContextChange([]);
          onLinkedDatasetChange(null);
        }
      } catch (error) {
        console.error("Failed to delete chat:", error);
        toast.error("Failed to delete chat");
      }
    },
    [deleteChat, selectedChatId, selectChatForDataset, onContextChange, onLinkedDatasetChange, currentUserId, queryClient]
  );

  const handleNewChat = useCallback(() => {
    // Reset stores and clear results
    resetExecutedQueries();
    setResults(null);
    clearVisualizationPaths();
    setIsOpen(false);
    setVisualizationOpen(false);
    setResultsPanelActiveTab("sql");

    // Clear selection
    selectChatForDataset(null, null, null);
    onContextChange([]);
    onLinkedDatasetChange(null);

    // Update URL
    onUrlUpdate([]);

    // Reset scroll
    onScrollReset();

    // Switch to chat tab
    onTabChange("chat");
  }, [
    resetExecutedQueries,
    setResults,
    clearVisualizationPaths,
    setIsOpen,
    setVisualizationOpen,
    setResultsPanelActiveTab,
    selectChatForDataset,
    onContextChange,
    onLinkedDatasetChange,
    onUrlUpdate,
    onScrollReset,
    onTabChange,
  ]);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold">Chat History</h2>
          <Button size="sm" onClick={handleNewChat}>
            <MessageSquarePlus className="mr-2 h-4 w-4" />
            New Chat
          </Button>
        </div>
        <ScrollArea className="h-[calc(100vh-12rem)]">
          <div className="space-y-2 pr-4">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-16 w-full" />
            ))}
          </div>
        </ScrollArea>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold">Chat History</h2>
          <Button size="sm" onClick={handleNewChat}>
            <MessageSquarePlus className="mr-2 h-4 w-4" />
            New Chat
          </Button>
        </div>
        <div className="text-center py-8 text-muted-foreground">
          Failed to load chat history
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold">Chat History</h2>
        <Button size="sm" onClick={handleNewChat}>
          <MessageSquarePlus className="mr-2 h-4 w-4" />
          New Chat
        </Button>
      </div>

      <ScrollArea className="h-[calc(100vh-12rem)]">
        <div className="space-y-2 pr-4">
          {allChats.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No previous chats. Start a new conversation!
            </div>
          ) : (
            allChats.map((chat) => {
              // Safety check for null/undefined chats
              if (!chat || !chat.id) return null;
              
              return (
                <div
                  key={chat.id}
                  className={cn(
                    "group relative flex items-center justify-between p-3 rounded-lg cursor-pointer transition-colors",
                    "hover:bg-muted/50",
                    selectedChatId === chat.id && "bg-muted"
                  )}
                  onClick={() =>
                    handleChatSelect(
                      chat.id,
                      chat.title || "Untitled Chat"
                      // Note: linked_dataset_id would need to be fetched from chat messages if needed
                    )
                  }
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">
                      {chat.title || "Untitled Chat"}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {new Date(chat.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="opacity-0 group-hover:opacity-100 transition-opacity"
                    onClick={(e) => handleDeleteChat(e, chat.id)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              );
            })
          )}
        </div>
      </ScrollArea>
    </div>
  );
});
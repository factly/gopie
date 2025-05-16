import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { History, MessageSquarePlus, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { useChatStore } from "@/lib/stores/chat-store";
import { useChats } from "@/lib/queries/chat";
import { useDeleteChat } from "@/lib/mutations/chat";
import { toast } from "sonner";

interface ChatHistoryProps {
  datasetId: string;
  variant?: "default" | "outline" | "ghost";
  className?: string;
}

export function ChatHistory({
  datasetId,
  variant = "outline",
  className = "",
}: ChatHistoryProps) {
  const { selectChatForDataset, getSelectedChatForDataset } = useChatStore();
  const selectedChat = getSelectedChatForDataset(datasetId);
  const selectedChatId = selectedChat.id;

  const {
    data: chatsData,
    isLoading: isLoadingChats,
    fetchNextPage: fetchNextChats,
    hasNextPage: hasNextChatsPage,
    isFetchingNextPage: isFetchingNextChats,
    refetch: refetchChats,
  } = useChats({
    variables: {
      datasetId,
      limit: 10,
    },
  });

  const deleteChat = useDeleteChat();

  const allChats = chatsData?.pages.flatMap((page) => page.data.results) ?? [];

  const handleStartNewChat = () => {
    selectChatForDataset(datasetId, null, null);
  };

  const handleDeleteChat = async (chatId: string) => {
    try {
      await deleteChat.mutateAsync(chatId);
      if (chatId === selectedChatId) {
        selectChatForDataset(datasetId, null, null);
      }
      await refetchChats();
      toast.success("Chat deleted successfully");
    } catch {
      toast.error("Failed to delete chat");
    }
  };

  const handleSelectChat = (chatId: string, chatName: string) => {
    selectChatForDataset(datasetId, chatId, chatName || "New Chat");
  };

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          variant={variant}
          size="icon"
          className={`h-9 w-9 rounded-full shadow-sm ${className}`}
        >
          <History className="h-5 w-5" />
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-96 p-0">
        <div className="space-y-2 p-4">
          <div className="flex items-center justify-between pb-2 border-b">
            <h4 className="font-medium">Chat History</h4>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleStartNewChat}
              className="h-8 px-2 text-xs"
            >
              <MessageSquarePlus className="h-4 w-4 mr-1" />
              New Chat
            </Button>
          </div>
          {isLoadingChats ? (
            <div className="space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-8 w-full" />
              ))}
            </div>
          ) : allChats.length > 0 ? (
            <ScrollArea className="h-[300px]">
              <div className="space-y-1 pr-2">
                {allChats.map((chat) => {
                  const date = new Date(chat.updated_at);
                  const today = new Date();
                  const yesterday = new Date(today);
                  yesterday.setDate(yesterday.getDate() - 1);

                  let dateString;
                  if (date.toDateString() === today.toDateString()) {
                    dateString = date.toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    });
                  } else if (date.toDateString() === yesterday.toDateString()) {
                    dateString = "Yesterday";
                  } else if (date.getFullYear() === today.getFullYear()) {
                    dateString = date.toLocaleDateString([], {
                      month: "short",
                      day: "numeric",
                    });
                  } else {
                    dateString = date.toLocaleDateString([], {
                      year: "2-digit",
                      month: "short",
                      day: "numeric",
                    });
                  }

                  return (
                    <div
                      key={chat.id}
                      className={cn(
                        "group relative flex items-center justify-between rounded-md px-2 py-2 text-sm hover:bg-muted/50 cursor-pointer gap-2",
                        selectedChatId === chat.id && "bg-muted"
                      )}
                      onClick={() =>
                        handleSelectChat(chat.id, chat.name || "New Chat")
                      }
                    >
                      <div className="flex-1 min-w-0">
                        <div className="break-words font-medium">
                          {chat.name || "New Chat"}
                        </div>
                      </div>
                      <div className="flex items-center shrink-0">
                        <span className="text-xs text-muted-foreground whitespace-nowrap pr-1 group-hover:opacity-0 transition-opacity">
                          {dateString}
                        </span>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7 opacity-0 group-hover:opacity-100 absolute right-1"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteChat(chat.id);
                          }}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </ScrollArea>
          ) : (
            <div className="py-3 text-center text-sm text-muted-foreground">
              No chat history yet
            </div>
          )}
        </div>
        {hasNextChatsPage && (
          <div className="border-t p-2">
            <Button
              variant="ghost"
              size="sm"
              className="w-full h-8 text-xs"
              onClick={() => fetchNextChats()}
              disabled={isFetchingNextChats}
            >
              {isFetchingNextChats ? (
                <span className="h-3 w-3 animate-spin rounded-full border-2 border-primary border-t-transparent" />
              ) : (
                "Load More"
              )}
            </Button>
          </div>
        )}
      </PopoverContent>
    </Popover>
  );
}

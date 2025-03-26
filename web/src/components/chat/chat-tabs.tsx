import * as React from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { Trash2, Clock } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { useChatStore } from "@/lib/stores/chat-store";
import { useChats } from "@/lib/queries/chat";
import { useDeleteChat } from "@/lib/mutations/chat";
import { toast } from "sonner";

interface ChatTabsProps {
  datasetId: string;
  children: React.ReactNode;
  defaultTab?: string;
}

export function ChatTabs({
  datasetId,
  children,
  defaultTab = "chat",
}: ChatTabsProps) {
  const { selectedChatId, selectChat } = useChatStore();
  const [activeTab, setActiveTab] = React.useState(defaultTab);

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

  const handleDeleteChat = async (chatId: string) => {
    try {
      await deleteChat.mutateAsync(chatId);
      if (chatId === selectedChatId) {
        selectChat(null, null);
      }
      await refetchChats();
      toast.success("Chat deleted successfully");
    } catch {
      toast.error("Failed to delete chat");
    }
  };

  const handleSelectChat = (chatId: string, chatName: string) => {
    selectChat(chatId, chatName || "New Chat");
    setActiveTab("chat"); // Switch to chat tab when a chat is selected
  };

  return (
    <Tabs
      value={activeTab}
      onValueChange={setActiveTab}
      className="w-full h-full flex flex-col"
    >
      <div className="flex w-full">
        <TabsList className="w-full h-10 grid grid-cols-2 rounded-none bg-background">
          <TabsTrigger
            value="chat"
            className="data-[state=active]:border-b-2 data-[state=active]:border-primary data-[state=active]:bg-background data-[state=active]:shadow-none data-[state=active]:font-medium rounded-none px-4 py-2 text-sm transition-all"
          >
            Chat
          </TabsTrigger>
          <TabsTrigger
            value="history"
            className="data-[state=active]:border-b-2 data-[state=active]:border-primary data-[state=active]:bg-background data-[state=active]:shadow-none data-[state=active]:font-medium rounded-none px-4 py-2 text-sm transition-all"
          >
            History
          </TabsTrigger>
        </TabsList>
      </div>

      <TabsContent
        value="chat"
        className="flex-1 overflow-hidden flex flex-col data-[state=inactive]:hidden p-0 border-none"
      >
        {children}
      </TabsContent>

      <TabsContent
        value="history"
        className="flex-1 overflow-hidden p-4 flex flex-col data-[state=inactive]:hidden border-none"
      >
        <div className="mb-3">
          <h4 className="font-medium text-foreground text-sm mb-4">
            Recent Conversations
          </h4>

          {isLoadingChats ? (
            <div className="space-y-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-14 w-full rounded-lg" />
              ))}
            </div>
          ) : allChats.length > 0 ? (
            <ScrollArea className="flex-1 pr-2">
              <div className="space-y-2">
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
                        "group relative flex flex-col rounded-lg px-4 py-3 hover:bg-muted cursor-pointer transition-colors",
                        selectedChatId === chat.id &&
                          "bg-muted/80 border border-border/10"
                      )}
                      onClick={() =>
                        handleSelectChat(chat.id, chat.name || "New Chat")
                      }
                    >
                      <div className="flex items-center justify-between mb-1">
                        <div className="font-medium text-foreground/90 text-sm truncate max-w-[80%]">
                          {chat.name || "New Chat"}
                        </div>
                        <div className="flex items-center gap-1.5">
                          <span className="text-xs text-muted-foreground whitespace-nowrap flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {dateString}
                          </span>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity ml-1"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteChat(chat.id);
                            }}
                          >
                            <Trash2 className="h-3.5 w-3.5 text-muted-foreground hover:text-destructive" />
                          </Button>
                        </div>
                      </div>
                      <div className="text-xs text-muted-foreground line-clamp-1">
                        Last updated {dateString}
                      </div>
                    </div>
                  );
                })}
              </div>
            </ScrollArea>
          ) : (
            <div className="py-8 text-center text-sm text-muted-foreground">
              No chat history yet
            </div>
          )}

          {hasNextChatsPage && (
            <div className="border-t pt-3 mt-3">
              <Button
                variant="ghost"
                size="sm"
                className="w-full h-9 text-xs font-medium"
                onClick={() => fetchNextChats()}
                disabled={isFetchingNextChats}
              >
                {isFetchingNextChats ? (
                  <span className="h-3 w-3 animate-spin rounded-full border-2 border-primary border-t-transparent mr-1" />
                ) : (
                  "Load More"
                )}
              </Button>
            </div>
          )}
        </div>
      </TabsContent>
    </Tabs>
  );
}

import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { MessageSquarePlus, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { useChatStore } from "@/lib/stores/chat-store";
import { useDeleteChat } from "@/lib/mutations/chat";
import { toast } from "sonner";
import { useEffect, useState } from "react";
import { useProjects } from "@/lib/queries/project/list-projects";
import { useDatasets } from "@/lib/queries/dataset/list-datasets";
import { fetchChats } from "@/lib/queries/chat/list-chats";
import { useQueryClient } from "@tanstack/react-query";
import { Chat } from "@/lib/api-client";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { AlertCircle } from "lucide-react";

interface ChatItem extends Chat {
  datasetId: string;
  datasetName: string;
  projectId: string;
  projectName: string;
}

export function GlobalChatHistory() {
  const { selectedChatId, selectChat } = useChatStore();
  const queryClient = useQueryClient();
  const [isLoading, setIsLoading] = useState(true);
  const [allChats, setAllChats] = useState<ChatItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Fetch all projects
  const { data: projectsData, error: projectsError } = useProjects({
    variables: { limit: 100 },
  });

  // Delete chat mutation
  const deleteChat = useDeleteChat();

  // Fetch all chats across all datasets and projects
  useEffect(() => {
    async function fetchAllChats() {
      if (!projectsData?.results?.length) {
        if (!projectsError && !isLoading) {
          // Only show no projects error if we're not loading and there's no project error
          // (which would be shown separately)
          setError("No projects available.");
        }
        return;
      }

      setIsLoading(true);
      setError(null); // Reset error when fetching
      const projects = projectsData.results;
      const allChatsArray: ChatItem[] = [];

      try {
        // Collect all dataset queries and run them in parallel
        const datasetPromises = projects.map(async (project) => {
          try {
            const queryKey = [
              "datasets",
              { projectId: project.id, limit: 100 },
            ];
            // Check cache first
            const cachedData = queryClient.getQueryData(queryKey);

            // Safely handle cached data with type assertion
            if (
              cachedData &&
              typeof cachedData === "object" &&
              "results" in cachedData
            ) {
              return { project, data: cachedData };
            }

            // If not in cache, fetch it
            const data = await queryClient.fetchQuery({
              queryKey,
              queryFn: async () => {
                const result = await useDatasets.fetcher({
                  projectId: project.id,
                  limit: 100,
                });
                return result;
              },
            });

            return { project, data };
          } catch (error) {
            console.error(
              `Failed to fetch datasets for project ${project.id}:`,
              error
            );
            return { project, data: { results: [] } };
          }
        });

        const datasetResults = await Promise.all(datasetPromises);

        // For each dataset, fetch its chats
        for (const result of datasetResults) {
          const project = result.project;
          const data = result.data;

          // Properly type guard for data.results
          if (
            !data ||
            typeof data !== "object" ||
            !("results" in data) ||
            !Array.isArray(data.results)
          ) {
            continue;
          }

          for (const dataset of data.results) {
            try {
              const chatsResponse = await fetchChats(
                { datasetId: dataset.id, limit: 50 },
                { pageParam: 1 }
              );

              if (chatsResponse.data.results) {
                // Add project and dataset info to each chat
                const chatsWithContext = chatsResponse.data.results.map(
                  (chat: Chat) => ({
                    ...chat,
                    datasetId: dataset.id,
                    datasetName: dataset.alias,
                    projectId: project.id,
                    projectName: project.name,
                  })
                );
                allChatsArray.push(...chatsWithContext);
              }
            } catch (error) {
              console.error(
                `Failed to fetch chats for dataset ${dataset.id}:`,
                error
              );
            }
          }
        }

        // Sort chats by updated_at date (newest first)
        allChatsArray.sort((a, b) => {
          return (
            new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
          );
        });

        setAllChats(allChatsArray);
      } catch (error) {
        console.error("Error fetching all chats:", error);
        setError("Failed to load chat history. Please try again later.");
      } finally {
        setIsLoading(false);
      }
    }

    fetchAllChats();
  }, [projectsData?.results, queryClient, projectsError, isLoading]);

  const handleStartNewChat = () => {
    selectChat(null, null);
  };

  const handleDeleteChat = async (chatId: string) => {
    try {
      await deleteChat.mutateAsync(chatId);
      if (chatId === selectedChatId) {
        selectChat(null, null);
      }

      // Update the local state
      setAllChats((prev) => prev.filter((chat) => chat.id !== chatId));

      // Invalidate queries to refresh data
      await queryClient.invalidateQueries({ queryKey: ["chats"] });

      toast.success("Chat deleted successfully");
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Unknown error";
      toast.error(`Failed to delete chat: ${errorMessage}`);
      console.error("Error deleting chat:", err);
    }
  };

  const handleSelectChat = (chatId: string, chatName: string) => {
    selectChat(chatId, chatName || "New Chat");
  };

  if (projectsError) {
    return (
      <Alert variant="destructive" className="m-2">
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>Error</AlertTitle>
        <AlertDescription>
          Failed to load projects: {projectsError.message}
        </AlertDescription>
      </Alert>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive" className="m-2">
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>Error</AlertTitle>
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }

  if (isLoading) {
    return (
      <div className="p-4 space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-8 w-full" />
        ))}
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between p-4">
        <Button
          variant="ghost"
          size="sm"
          onClick={handleStartNewChat}
          className="h-8 px-2 text-xs w-full justify-start"
        >
          <MessageSquarePlus className="h-4 w-4 mr-2" />
          New Chat
        </Button>
      </div>

      {allChats.length > 0 ? (
        <ScrollArea className="flex-1 px-4">
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
                    "group relative flex flex-col rounded-md px-2 py-2 text-sm hover:bg-muted/50 cursor-pointer",
                    selectedChatId === chat.id && "bg-muted"
                  )}
                  onClick={() =>
                    handleSelectChat(chat.id, chat.name || "New Chat")
                  }
                >
                  <div className="flex items-center justify-between gap-2">
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
                  <div className="flex items-center mt-1">
                    <span className="text-xs text-muted-foreground truncate">
                      {chat.projectName} / {chat.datasetName}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </ScrollArea>
      ) : (
        <div className="p-4 text-center text-sm text-muted-foreground">
          No chat history yet
        </div>
      )}
    </div>
  );
}

"use client";

import React from "react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { ChevronDown } from "lucide-react";
import { ChatMessage } from "@/components/chat/message";
import { ChatViewProps } from "@/types/chat";

export const ChatView = React.memo(
  ({
    scrollRef,
    isLoading,
    messages,
    selectedChatId,
    isLoadingChatMessages = false,
    hasNextPage = false,
    fetchNextPage,
    isFetchingNextPage = false,
    showScrollButton,
    onScrollToBottom,
    isWaitingForChatId = false,
  }: ChatViewProps) => (
    <div className="flex-1 overflow-hidden relative min-h-0">
      <div
        className={`z-10 absolute inset-x-0 top-0 h-8 bg-gradient-to-b from-background via-background to-transparent pointer-events-none ${
          messages.length > 0 ? "opacity-100" : "opacity-0"
        } transition-opacity duration-300`}
      />
      <ScrollArea ref={scrollRef} className="h-full w-full [&>div>div]:!block [&>div>div]:!min-w-0">
        <div className="px-4 pb-32 pt-8">
          {/* Load more button for pagination */}
          {hasNextPage && selectedChatId && (
            <div className="flex justify-center mb-4">
              <Button
                variant="outline"
                size="sm"
                onClick={fetchNextPage}
                disabled={isFetchingNextPage}
              >
                {isFetchingNextPage ? (
                  <>
                    <div className="h-4 w-4 animate-spin border-2 border-current border-t-transparent mr-2" />
                    Loading...
                  </>
                ) : (
                  "Load more messages"
                )}
              </Button>
            </div>
          )}

          {/* Show creating chat message when waiting for chat ID */}
          {isWaitingForChatId && !selectedChatId ? (
            <div className="flex items-center justify-center py-8">
              <div className="flex items-center space-x-2 text-muted-foreground">
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                <span>Creating new chat...</span>
              </div>
            </div>
          ) : (isLoading || isLoadingChatMessages) && messages.length === 0 ? (
            <div className="space-y-4">
              <Skeleton className="h-16 w-3/4" />
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-16 w-2/3" />
            </div>
          ) : !selectedChatId && messages.length === 0 ? null : (
            <div className="space-y-6">
              {messages.map((message) => (
                <ChatMessage
                  key={message.id}
                  id={message.id}
                  content={message.parts?.find((part) => part.type === 'text')?.text || ''}
                  message={message}
                  role={
                    message.role === "system"
                      ? "assistant"
                      : (message.role as
                          | "user"
                          | "assistant"
                          | "intermediate"
                          | "ai")
                  }
                  createdAt={
                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                    typeof (message as any).createdAt === "string"
                      // eslint-disable-next-line @typescript-eslint/no-explicit-any
                      ? (message as any).createdAt
                      // eslint-disable-next-line @typescript-eslint/no-explicit-any
                      : (message as any).createdAt instanceof Date
                      // eslint-disable-next-line @typescript-eslint/no-explicit-any
                      ? (message as any).createdAt.toISOString()
                      : new Date().toISOString()
                  }
                  chatId={selectedChatId || undefined}
                  isLatest={
                    message === messages[messages.length - 1] &&
                    message.role !== "user"
                  }
                  isLoading={
                    message.role === "assistant" && 
                    (!message.parts?.find((part) => part.type === 'text')?.text || 
                     message.parts?.find((part) => part.type === 'text')?.text === "")
                  }
                  isStreaming={
                    isLoading &&
                    message === messages[messages.length - 1] &&
                    message.role === "assistant"
                  }
                />
              ))}
            </div>
          )}
        </div>
      </ScrollArea>
      {showScrollButton && (
        <Button
          onClick={onScrollToBottom}
          className="absolute bottom-24 right-4 z-50 rounded-full h-10 w-10 p-0 shadow-lg bg-background border-2 border-border hover:bg-accent hover:border-accent transition-all"
          variant="outline"
          size="icon"
          aria-label="Scroll to bottom"
        >
          <ChevronDown className="h-5 w-5" />
        </Button>
      )}
      <div
        className={`z-10 absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-background to-transparent pointer-events-none`}
      />
    </div>
  )
);

ChatView.displayName = "ChatView";
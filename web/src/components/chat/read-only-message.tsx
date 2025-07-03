"use client";

import React from "react";
import { Lock, Eye } from "lucide-react";
import { ChatVisibilityIndicator } from "./chat-visibility-indicator";
import { ChatVisibility } from "@/lib/mutations/chat";
import { usePublicUser } from "@/lib/queries/user/get-public-user";

interface ReadOnlyMessageProps {
  chatOwner?: string;
  chatVisibility?: ChatVisibility;
  chatTitle?: string;
}

export function ReadOnlyMessage({
  chatOwner,
  chatVisibility = "private",
  chatTitle,
}: ReadOnlyMessageProps) {
  // Fetch user information if we have a user ID
  const { data: userData, isLoading: isLoadingUser } = usePublicUser({
    variables: { userId: chatOwner || "" },
    enabled: !!chatOwner,
  });

  const ownerDisplayName =
    userData?.data?.displayName || chatOwner || "the owner";
  return (
    <div className="border-t bg-muted/30 p-4">
      <div className="flex items-center gap-3 max-w-4xl mx-auto">
        <div className="flex items-center justify-center w-10 h-10 rounded-full bg-muted">
          <Eye className="h-5 w-5 text-muted-foreground" />
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="font-medium text-sm">Viewing chat</h3>
            <ChatVisibilityIndicator visibility={chatVisibility} />
          </div>
          <p className="text-sm text-muted-foreground">
            You&apos;re viewing {chatTitle ? `"${chatTitle}"` : "this chat"} in
            read-only mode. Only{" "}
            {isLoadingUser ? "the chat owner" : ownerDisplayName} can send
            messages.
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Lock className="h-4 w-4" />
          <span>Read-only</span>
        </div>
      </div>
    </div>
  );
}

"use client";

import React, { useCallback } from "react";
import { ContextPicker } from "@/components/chat/context-picker";
import { MentionInput } from "@/components/chat/mention-input";
import { ChatInputProps } from "@/types/chat";

export const ChatInput = React.memo(
  ({
    onStop,
    isStreaming,
    selectedContexts,
    onSelectContext,
    onRemoveContext,
    lockableContextIds = [],
    hasContext,
    input,
    handleInputChange,
    handleSubmit,
    isLoading,
  }: ChatInputProps) => {
    // Handle input change from MentionInput
    const handleMentionInputChange = useCallback(
      (value: string) => {
        handleInputChange(value);
      },
      [handleInputChange]
    );

    return (
      <div className="border-t bg-background/80 backdrop-blur-md p-2">
        <div className="flex items-start gap-2 w-full pr-2">
          <ContextPicker
            selectedContexts={selectedContexts}
            onSelectContext={onSelectContext}
            onRemoveContext={onRemoveContext}
            triggerClassName="h-10 w-10 bg-transparent text-foreground hover:bg-black/5 dark:hover:bg-white/5"
            lockableContextIds={lockableContextIds}
          />
          <MentionInput
            value={input}
            onChange={handleMentionInputChange}
            onSubmit={handleSubmit}
            disabled={isLoading}
            placeholder="Ask questions about your data..."
            selectedContexts={selectedContexts}
            onSelectContext={onSelectContext}
            onRemoveContext={onRemoveContext}
            className="flex-1"
            showSendButton={true}
            isSending={isLoading}
            isStreaming={isStreaming}
            stopMessageStream={onStop}
            lockableContextIds={lockableContextIds}
            hasContext={hasContext}
          />
        </div>
      </div>
    );
  }
);

ChatInput.displayName = "ChatInput";
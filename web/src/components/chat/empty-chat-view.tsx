"use client";

import React from "react";
import { ContextPicker } from "@/components/chat/context-picker";
import { MentionInput } from "@/components/chat/mention-input";
import { ContextSelectionHelper } from "@/components/chat/context-selection-helper";
import { EmptyChatViewProps } from "@/types/chat";

export const EmptyChatView = React.memo(
  ({
    selectedContexts,
    onSelectContext,
    onRemoveContext,
    input,
    handleInputChange,
    handleSubmit,
    isLoading,
    isStreaming,
    handleStop,
    isInputFocused,
    setIsInputFocused,
  }: EmptyChatViewProps) => (
    <div className="absolute inset-0 flex items-center justify-center px-4 pointer-events-none">
      <div className="w-full max-w-2xl pointer-events-auto">
        <div className="mb-6 text-center">
          <div className="flex justify-center mb-3">
            <div className="flex items-center gap-2 px-3 py-1.5 bg-background/30 backdrop-blur-sm max-w-md">
              <a
                href="/chat?tab=history"
                className="text-sm text-muted-foreground hover:text-primary flex items-center gap-1 transition-colors"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  className="h-4 w-4"
                >
                  <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
                  <path d="M3 3v5h5" />
                  <path d="M12 7v5l4 2" />
                </svg>
                Previous Chats
              </a>
            </div>
          </div>
          <h1 className="text-4xl md:text-5xl font-bold text-foreground mb-2">
            Chat with your data
          </h1>
        </div>
        <div
          className="bg-card dark:bg-card/90 border border-border shadow-lg 
          ring-[1.5px] ring-foreground/10 
          hover:ring-foreground/20 hover:shadow-xl hover:border-foreground/20
          focus-within:ring-primary/30 focus-within:border-primary/50 focus-within:shadow-primary/10
          transition-all duration-200"
        >
          <div className="flex items-center">
            <div className="flex items-center justify-center h-12 w-12">
              <ContextPicker
                selectedContexts={selectedContexts}
                onSelectContext={onSelectContext}
                onRemoveContext={onRemoveContext}
                triggerClassName={`flex items-center justify-center h-9 w-9 text-muted-foreground hover:bg-muted hover:text-foreground transition-all duration-200 ${
                  isInputFocused &&
                  selectedContexts.length === 0
                    ? "animate-slow-pulse bg-muted/90"
                    : "bg-muted/70"
                }`}
                shouldFlash={
                  isInputFocused &&
                  selectedContexts.length === 0
                }
              />
            </div>
            <MentionInput
              value={input}
              onChange={handleInputChange}
              onSubmit={handleSubmit}
              disabled={isLoading}
              placeholder="Ask questions about your data..."
              selectedContexts={selectedContexts}
              onSelectContext={onSelectContext}
              onRemoveContext={onRemoveContext}
              className="flex-1 dark-input"
              showSendButton={true}
              isSending={isLoading}
              isStreaming={isStreaming}
              stopMessageStream={handleStop}
              lockableContextIds={[]}
              hasContext={selectedContexts.length > 0}
              onFocus={() => setIsInputFocused(true)}
              onBlur={() => setIsInputFocused(false)}
            />
          </div>
        </div>
        <ContextSelectionHelper
          isVisible={
            isInputFocused && selectedContexts.length === 0
          }
        />
      </div>
    </div>
  )
);

EmptyChatView.displayName = "EmptyChatView";
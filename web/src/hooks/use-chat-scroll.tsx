import { useEffect, useLayoutEffect, useRef, useState, useCallback } from "react";
import { debounce } from "@/lib/utils/debounce";
import { UIMessage } from "ai";

interface ChatMessage {
  id: string;
  role: string;
  content?: string;
  createdAt?: string | Date;
}

interface UseChatScrollOptions {
  messages: (ChatMessage | UIMessage)[];
  streamingMessages?: (ChatMessage | UIMessage)[];
  isStreaming: boolean;
  showLoadingMessage?: boolean;
  activeTab: string;
}

export function useChatScroll({
  messages,
  streamingMessages = [],
  isStreaming,
  showLoadingMessage = false,
  activeTab,
}: UseChatScrollOptions) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [userHasScrolled, setUserHasScrolled] = useState(false);
  const [showScrollButton, setShowScrollButton] = useState(false);
  const previousMessageCountRef = useRef(0);
  const observerRef = useRef<MutationObserver | null>(null);

  // Reset scroll state when switching chats
  const resetScrollState = useCallback(() => {
    setUserHasScrolled(false);
    setShowScrollButton(false);
    previousMessageCountRef.current = 0;
  }, []);

  // Handle manual scroll events
  const handleScroll = useCallback(() => {
    if (activeTab !== "chat") return;
    
    const viewport = scrollRef.current?.querySelector(
      "[data-radix-scroll-area-viewport]"
    ) as HTMLElement;

    if (viewport) {
      const isNearBottom =
        viewport.scrollHeight -
          viewport.scrollTop -
          viewport.clientHeight <
        100;

      setShowScrollButton(!isNearBottom);
      
      // If user scrolled up, mark as having scrolled
      if (!isNearBottom && messages.length > 0) {
        setUserHasScrolled(true);
      } else if (isNearBottom) {
        setUserHasScrolled(false);
      }
    }
  }, [activeTab, messages.length]);

  // Scroll to bottom function
  const scrollToBottom = useCallback((behavior: ScrollBehavior = "smooth") => {
    const viewport = scrollRef.current?.querySelector(
      "[data-radix-scroll-area-viewport]"
    ) as HTMLElement;

    if (viewport) {
      viewport.scrollTo({
        top: viewport.scrollHeight - viewport.clientHeight,
        behavior,
      });
      setUserHasScrolled(false);
      setShowScrollButton(false);
    }
  }, []);

  // Setup scroll listener
  useEffect(() => {
    if (activeTab !== "chat") return;

    const viewport = scrollRef.current?.querySelector(
      "[data-radix-scroll-area-viewport]"
    ) as HTMLElement;

    if (viewport) {
      viewport.addEventListener("scroll", handleScroll);
      return () => viewport.removeEventListener("scroll", handleScroll);
    }
  }, [handleScroll, activeTab]);

  // Auto-scroll logic
  useLayoutEffect(() => {
    if (activeTab !== "chat") return;

    const viewport = scrollRef.current?.querySelector(
      "[data-radix-scroll-area-viewport]"
    ) as HTMLElement;

    if (viewport && messages.length > 0) {
      const lastMessage = messages[messages.length - 1];
      const isNewMessage = messages.length > previousMessageCountRef.current;

      // Check if we should auto-scroll
      const isInitialLoad =
        previousMessageCountRef.current === 0 && messages.length > 0;
      const isUserSending =
        lastMessage?.role === "user" && (isStreaming || showLoadingMessage);
      const isAssistantResponding =
        lastMessage?.role === "assistant" && isStreaming;

      const shouldAutoScroll =
        isInitialLoad ||
        isUserSending ||
        isAssistantResponding ||
        (isNewMessage && !userHasScrolled);

      if (shouldAutoScroll) {
        requestAnimationFrame(() => {
          if (viewport && viewport.scrollHeight > 0) {
            const currentScrollTop = viewport.scrollTop;
            const targetScrollTop = viewport.scrollHeight - viewport.clientHeight;
            
            // Only scroll if we're not already at the bottom
            if (Math.abs(targetScrollTop - currentScrollTop) > 5) {
              viewport.scrollTo({
                top: targetScrollTop,
                behavior: isInitialLoad ? "instant" : "smooth",
              });
            }
            
            // Update scroll button visibility after scroll
            const isNearBottom =
              viewport.scrollHeight -
                viewport.scrollTop -
                viewport.clientHeight <
              100;
            setShowScrollButton(!isNearBottom);
          }
        });
      }

      // Update the message count after processing
      previousMessageCountRef.current = messages.length;
    }
  }, [
    messages,
    streamingMessages,
    isStreaming,
    userHasScrolled,
    showLoadingMessage,
    activeTab,
  ]);

  // MutationObserver for continuous scrolling during streaming
  useEffect(() => {
    if (isStreaming && !userHasScrolled && activeTab === "chat") {
      const viewport = scrollRef.current?.querySelector(
        "[data-radix-scroll-area-viewport]"
      ) as HTMLElement;

      if (viewport) {
        // Disconnect previous observer if exists
        if (observerRef.current) {
          observerRef.current.disconnect();
        }

        // Create debounced scroll function for 60fps (16ms)
        const debouncedScroll = debounce(() => {
          if (!userHasScrolled) {
            requestAnimationFrame(() => {
              const targetScrollTop = viewport.scrollHeight - viewport.clientHeight;
              if (viewport.scrollTop < targetScrollTop - 100) {
                viewport.scrollTo({
                  top: targetScrollTop,
                  behavior: "smooth",
                });
              }
            });
          }
        }, 16);

        // Create new observer
        observerRef.current = new MutationObserver(debouncedScroll);

        // Start observing
        observerRef.current.observe(viewport, {
          childList: true,
          subtree: true,
          characterData: true,
        });
      }
    }

    // Cleanup
    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect();
        observerRef.current = null;
      }
    };
  }, [isStreaming, userHasScrolled, activeTab]);

  return {
    scrollRef,
    showScrollButton,
    scrollToBottom,
    resetScrollState,
    userHasScrolled,
  };
}
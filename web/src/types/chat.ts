import { UIMessage } from "ai";
import { ContextItem } from "@/components/chat/context-picker";

// Type for the messages from AI SDK
export interface ChatMessage {
  id: string;
  role: string;
  content: string;
  createdAt?: string | Date;
}

export interface ChatInputProps {
  onStop: () => void;
  isStreaming: boolean;
  selectedContexts: ContextItem[];
  onSelectContext: (context: ContextItem) => void;
  onRemoveContext: (contextId: string) => void;
  lockableContextIds?: string[];
  hasContext: boolean;
  input: string;
  handleInputChange: (value: string) => void;
  handleSubmit: (e: React.FormEvent) => void;
  isLoading: boolean;
}

export interface ChatViewProps {
  scrollRef: React.RefObject<HTMLDivElement | null>;
  isLoading: boolean;
  messages: UIMessage[];
  selectedChatId: string | null;
  isLoadingChatMessages?: boolean;
  hasNextPage?: boolean;
  fetchNextPage?: () => void;
  isFetchingNextPage?: boolean;
  showScrollButton: boolean;
  onScrollToBottom: () => void;
  isWaitingForChatId?: boolean;
}

export interface EmptyChatViewProps {
  selectedContexts: ContextItem[];
  onSelectContext: (context: ContextItem) => void;
  onRemoveContext: (contextId: string) => void;
  input: string;
  handleInputChange: (value: string) => void;
  handleSubmit: (e: React.FormEvent) => void;
  isLoading: boolean;
  isStreaming: boolean;
  handleStop: () => void;
  isInputFocused: boolean;
  setIsInputFocused: (focused: boolean) => void;
}
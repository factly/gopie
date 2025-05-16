import { create } from "zustand";

interface ChatStore {
  selectedChats: Record<string, { id: string; title: string }>;
  selectedChatId: string | null;
  selectedChatTitle: string | null;

  // Methods for backward compatibility
  setSelectedChatId: (id: string | null) => void;
  setSelectedChatTitle: (title: string | null) => void;
  selectChat: (id: string | null, title: string | null) => void;

  // New methods with dataset context
  selectChatForDataset: (
    datasetId: string | null,
    chatId: string | null,
    chatTitle: string | null
  ) => void;
  getSelectedChatForDataset: (datasetId: string) => {
    id: string | null;
    title: string | null;
  };
}

export const useChatStore = create<ChatStore>((set, get) => ({
  selectedChats: {},
  selectedChatId: null,
  selectedChatTitle: null,

  setSelectedChatId: (id) => set({ selectedChatId: id }),

  setSelectedChatTitle: (title) => set({ selectedChatTitle: title }),

  selectChat: (id, title) =>
    set({ selectedChatId: id, selectedChatTitle: title }),

  selectChatForDataset: (datasetId, chatId, chatTitle) => {
    const state = get();
    const newSelectedChats = { ...state.selectedChats };

    if (datasetId && chatId && chatTitle) {
      newSelectedChats[datasetId] = { id: chatId, title: chatTitle };
    } else if (datasetId) {
      // Clear selection for this dataset
      delete newSelectedChats[datasetId];
    }

    // Also update the global selectedChatId for backward compatibility
    set({
      selectedChats: newSelectedChats,
      selectedChatId: chatId,
      selectedChatTitle: chatTitle,
    });
  },

  getSelectedChatForDataset: (datasetId) => {
    const { selectedChats } = get();
    const selectedChat = selectedChats[datasetId];
    return selectedChat
      ? { id: selectedChat.id, title: selectedChat.title }
      : { id: null, title: null };
  },
}));

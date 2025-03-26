import { create } from "zustand";

interface ChatStore {
  selectedChatId: string | null;
  selectedChatTitle: string | null;
  setSelectedChatId: (id: string | null) => void;
  setSelectedChatTitle: (title: string | null) => void;
  selectChat: (id: string | null, title: string | null) => void;
}

export const useChatStore = create<ChatStore>((set) => ({
  selectedChatId: null,
  selectedChatTitle: null,
  setSelectedChatId: (id) => set({ selectedChatId: id }),
  setSelectedChatTitle: (title) => set({ selectedChatTitle: title }),
  selectChat: (id, title) =>
    set({ selectedChatId: id, selectedChatTitle: title }),
}));

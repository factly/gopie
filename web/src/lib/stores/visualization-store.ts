import { create } from "zustand";

interface VisualizationState {
  paths: string[];
  isOpen: boolean;
  chatId?: string;
}

interface VisualizationActions {
  setPaths: (paths: string[], chatId?: string) => void;
  setIsOpen: (isOpen: boolean) => void;
  clearPaths: () => void;
}

type VisualizationStore = VisualizationState & VisualizationActions;

export const useVisualizationStore = create<VisualizationStore>((set) => ({
  paths: [],
  isOpen: false,
  chatId: undefined,

  setPaths: (paths: string[], chatId?: string) =>
    set({ paths, chatId, isOpen: paths.length > 0 }),

  setIsOpen: (isOpen: boolean) => set({ isOpen }),

  clearPaths: () => set({ paths: [], isOpen: false, chatId: undefined }),
}));

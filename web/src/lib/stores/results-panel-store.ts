import { create } from "zustand";

interface ResultsPanelState {
  activeTab: 'sql' | 'visualizations';
}

interface ResultsPanelActions {
  setActiveTab: (tab: 'sql' | 'visualizations') => void;
}

type ResultsPanelStore = ResultsPanelState & ResultsPanelActions;

export const useResultsPanelStore = create<ResultsPanelStore>((set) => ({
  activeTab: 'sql',
  
  setActiveTab: (tab: 'sql' | 'visualizations') => set({ activeTab: tab }),
}));
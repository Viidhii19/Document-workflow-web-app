import { create } from 'zustand';
import type { Document, ChatMessage, Citation } from '../types';

interface AppState {
  documents: Document[];
  activeDocument: Document | null;
  chatHistory: ChatMessage[];
  activeCitation: Citation | null;
  isLoading: boolean;
  
  setDocuments: (docs: Document[]) => void;
  setActiveDocument: (doc: Document | null) => void;
  setChatHistory: (history: ChatMessage[]) => void;
  addChatMessage: (message: ChatMessage) => void;
  setActiveCitation: (citation: Citation | null) => void;
  setIsLoading: (loading: boolean) => void;
}

export const useAppStore = create<AppState>((set) => ({
  documents: [],
  activeDocument: null,
  chatHistory: [],
  activeCitation: null,
  isLoading: false,
  
  setDocuments: (docs) => set({ documents: docs }),
  setActiveDocument: (doc) => set({ activeDocument: doc, chatHistory: [], activeCitation: null }),
  setChatHistory: (history) => set({ chatHistory: history }),
  addChatMessage: (message) => set((state) => ({ chatHistory: [...state.chatHistory, message] })),
  setActiveCitation: (citation) => set({ activeCitation: citation }),
  setIsLoading: (loading) => set({ isLoading: loading }),
}));

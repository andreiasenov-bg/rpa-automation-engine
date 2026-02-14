import { create } from 'zustand';
import { chatApi } from '../api/chat';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  error?: boolean;
}

interface ChatState {
  isOpen: boolean;
  messages: ChatMessage[];
  isLoading: boolean;
  conversationId: string;
  pageContext: string;
  toggleChat: () => void;
  openChat: () => void;
  closeChat: () => void;
  sendMessage: (content: string) => Promise<void>;
  clearConversation: () => void;
  setPageContext: (page: string) => void;
}

const genId = () => Math.random().toString(36).slice(2, 10);

export const useChatStore = create<ChatState>((set, get) => ({
  isOpen: false,
  messages: [],
  isLoading: false,
  conversationId: genId(),
  pageContext: '/',

  toggleChat: () => set((s) => ({ isOpen: !s.isOpen })),
  openChat: () => set({ isOpen: true }),
  closeChat: () => set({ isOpen: false }),

  setPageContext: (page: string) => set({ pageContext: page }),

  sendMessage: async (content: string) => {
    const userMsg: ChatMessage = {
      id: genId(),
      role: 'user',
      content,
      timestamp: new Date(),
    };
    set((s) => ({ messages: [...s.messages, userMsg], isLoading: true }));

    try {
      const { conversationId, pageContext, messages } = get();
      const res = await chatApi.sendMessage(content, conversationId, pageContext);
      const assistantMsg: ChatMessage = {
        id: genId(),
        role: 'assistant',
        content: res.response,
        timestamp: new Date(),
      };
      set((s) => ({
        messages: [...s.messages, assistantMsg],
        isLoading: false,
        conversationId: res.conversationId || s.conversationId,
      }));
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: genId(),
        role: 'assistant',
        content: err.response?.data?.detail || 'Sorry, I could not process your request. Please try again.',
        timestamp: new Date(),
        error: true,
      };
      set((s) => ({ messages: [...s.messages, errorMsg], isLoading: false }));
    }
  },

  clearConversation: () => {
    set({ messages: [], conversationId: genId() });
  },
}));

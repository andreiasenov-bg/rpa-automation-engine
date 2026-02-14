import { create } from 'zustand';
import { chatApi } from '../api/chat';

export interface ChatAction {
  type: string;
  label: string;
  icon: string;
  params: Record<string, any>;
  confirm?: boolean;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  error?: boolean;
  actions?: ChatAction[];
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
  addSystemMessage: (content: string, isError?: boolean) => void;
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

  addSystemMessage: (content: string, isError: boolean = false) => {
    const msg: ChatMessage = {
      id: genId(),
      role: 'system',
      content,
      timestamp: new Date(),
      error: isError,
    };
    set((s) => ({ messages: [...s.messages, msg] }));
  },

  sendMessage: async (content: string) => {
    const userMsg: ChatMessage = {
      id: genId(),
      role: 'user',
      content,
      timestamp: new Date(),
    };
    set((s) => ({ messages: [...s.messages, userMsg], isLoading: true }));

    try {
      const { conversationId, pageContext } = get();
      const res = await chatApi.sendMessage(content, conversationId, pageContext);
      const assistantMsg: ChatMessage = {
        id: genId(),
        role: 'assistant',
        content: res.response,
        timestamp: new Date(),
        actions: res.actions || [],
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

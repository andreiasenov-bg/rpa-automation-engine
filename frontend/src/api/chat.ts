import client from './client';
import type { ChatAction } from '../stores/chatStore';

interface ChatActionResponse {
  type: string;
  label: string;
  icon: string;
  params: Record<string, any>;
  confirm?: boolean;
}

interface ChatResponse {
  response: string;
  conversationId: string;
  actions?: ChatActionResponse[];
}

interface SuggestionsResponse {
  suggestions: string[];
}

interface ExecuteActionResponse {
  success: boolean;
  message: string;
  execution_id?: string;
  redirect?: string;
}

export const chatApi = {
  async sendMessage(message: string, conversationId?: string, pageContext?: string): Promise<ChatResponse> {
    const { data } = await client.post<ChatResponse>('/chat/message', {
      message,
      conversation_id: conversationId,
      page_context: pageContext,
    });
    return data;
  },

  async executeAction(conversationId: string, action: ChatAction): Promise<ExecuteActionResponse> {
    const { data } = await client.post<ExecuteActionResponse>('/chat/execute-action', {
      conversation_id: conversationId,
      action,
    });
    return data;
  },

  async clearConversation(conversationId: string): Promise<void> {
    await client.post('/chat/clear', { conversation_id: conversationId });
  },

  async getSuggestions(pageContext: string): Promise<SuggestionsResponse> {
    const { data } = await client.get<SuggestionsResponse>('/chat/suggestions', {
      params: { page_context: pageContext },
    });
    return data;
  },
};

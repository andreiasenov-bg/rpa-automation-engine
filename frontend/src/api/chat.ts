import client from './client';

interface ChatResponse {
  response: string;
  conversationId: string;
}

interface SuggestionsResponse {
  suggestions: string[];
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

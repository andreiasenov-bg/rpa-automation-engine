import client from './client';

export interface TemplateSummary {
  id: string;
  name: string;
  description: string;
  category: string;
  icon: string;
  tags: string[];
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  estimated_duration: string;
  step_count: number;
}

export interface TemplateDetail extends TemplateSummary {
  steps: Array<{
    id: string;
    name: string;
    type: string;
    config: Record<string, unknown>;
    depends_on?: string[];
  }>;
}

export const templatesApi = {
  list: async (filters: { category?: string; difficulty?: string; search?: string } = {}): Promise<{
    templates: TemplateSummary[];
    total: number;
  }> => {
    const params: Record<string, string> = {};
    if (filters.category) params.category = filters.category;
    if (filters.difficulty) params.difficulty = filters.difficulty;
    if (filters.search) params.search = filters.search;
    const { data } = await client.get('/templates', { params });
    return data;
  },

  get: async (id: string): Promise<TemplateDetail> => {
    const { data } = await client.get(`/templates/${id}`);
    return data;
  },

  categories: async (): Promise<string[]> => {
    const { data } = await client.get('/templates/categories');
    return Array.isArray(data) ? data : data?.categories ?? [];
  },

  instantiate: async (
    templateId: string,
    name: string,
    description?: string,
  ): Promise<{ workflow_id: string; name: string; message: string }> => {
    const { data } = await client.post(`/templates/${templateId}/instantiate`, {
      template_id: templateId,
      name,
      description,
    });
    return data;
  },
};

import client from './client';

export interface TemplateParameter {
  key: string;
  label: string;
  type: 'url' | 'string' | 'number' | 'email' | 'select' | 'boolean' | 'credential' | 'textarea';
  required: boolean;
  placeholder?: string;
  description?: string;
  default?: unknown;
  maps_to?: string;
  credential_type?: string;
  options?: Array<{ label: string; value: string }>;
  auto_fillable?: boolean;
  ai_hint?: string;
}

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
  required_parameters: TemplateParameter[];
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

export interface ValidationResult {
  valid: boolean;
  errors: Array<{ key: string; message: string }>;
  warnings: Array<{ key: string; message: string }>;
  fields: Record<string, { status: 'ok' | 'error' | 'warning'; message: string }>;
}

export interface AIFieldAnalysis {
  key: string;
  action: 'fill' | 'modify' | 'keep' | 'add_warning';
  suggested_value: string | null;
  confidence: number;
  reason: string;
}

export interface AIReviewResult {
  suggested_parameters: Record<string, string>;
  field_analysis: AIFieldAnalysis[];
  warnings: string[];
  overall_confidence: number;
  explanation: string;
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

  aiReview: async (templateId: string, instruction: string, parameters?: Record<string, string>): Promise<AIReviewResult> => {
    const { data } = await client.post(`/templates/${templateId}/ai-review`, {
      instruction,
      parameters: parameters ?? {},
    });
    return data;
  },

  validate: async (templateId: string, parameters: Record<string, unknown>): Promise<ValidationResult> => {
    const { data } = await client.post(`/templates/${templateId}/validate`, { parameters });
    return data;
  },

  instantiate: async ({ templateId, name, description, parameters, instruction }: {
    templateId: string;
    name: string;
    description?: string;
    parameters?: Record<string, unknown>;
    instruction?: string;
  }): Promise<{ workflow_id: string; name: string }> => {
    const { data } = await client.post(`/templates/${templateId}/instantiate`, {
      name,
      description,
      template_id: templateId,
      parameters,
      instruction,
    });
    return data;
  },
};

import client from './client';

export type VarType = 'string' | 'number' | 'boolean' | 'json' | 'list' | 'secret';

export interface VariableDefinition {
  name: string;
  type: VarType;
  default_value?: unknown;
  description: string;
  required: boolean;
  scope: 'workflow' | 'step';
  sensitive: boolean;
}

export interface StepMapping {
  step_id: string;
  input_mapping: Record<string, string>;
  output_mapping: Record<string, string>;
}

export interface VariablesResponse {
  workflow_id: string;
  variables: VariableDefinition[];
  step_mappings: StepMapping[];
}

export interface ValidationResult {
  valid: boolean;
  errors: Array<{ variable: string; error: string }>;
  resolved: Record<string, unknown>;
}

export const workflowVariablesApi = {
  get: async (workflowId: string): Promise<VariablesResponse> => {
    const { data } = await client.get(`/workflow-variables/${workflowId}/variables`);
    return data;
  },

  update: async (workflowId: string, variables: VariableDefinition[]): Promise<void> => {
    await client.put(`/workflow-variables/${workflowId}/variables`, { variables });
  },

  updateMappings: async (workflowId: string, mappings: StepMapping[]): Promise<void> => {
    await client.put(`/workflow-variables/${workflowId}/variables/mappings`, { mappings });
  },

  validate: async (workflowId: string, variables: Record<string, unknown>): Promise<ValidationResult> => {
    const { data } = await client.post(`/workflow-variables/${workflowId}/variables/validate`, { variables });
    return data;
  },
};

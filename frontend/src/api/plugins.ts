import client from './client';

export interface PluginInfo {
  name: string;
  version: string;
  description: string;
  author: string;
  source: 'builtin' | 'entrypoint' | 'local';
  enabled: boolean;
  task_types: string[];
  config_schema?: Record<string, unknown>;
  errors: string[];
}

export const pluginsApi = {
  list: () => client.get<{ plugins: PluginInfo[] }>('/api/v1/plugins').then((r) => r.data),
  get: (name: string) => client.get<PluginInfo>(`/api/v1/plugins/${name}`).then((r) => r.data),
  toggle: (name: string, enabled: boolean) =>
    client.put(`/api/v1/plugins/${name}`, { enabled }).then((r) => r.data),
  reload: () =>
    client.post<{ plugins_loaded: number; task_types: number }>('/api/v1/plugins/reload').then((r) => r.data),
};

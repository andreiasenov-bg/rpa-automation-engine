import { api } from './client';

export const apiHealthApi = {
  getStatus: () => api.get('/api-health/status').then(r => r.data),
  getHistory: (limit = 60) =>
    api.get(`/api-health/history?limit=${limit}`).then(r => r.data),
  getAlerts: (limit = 50) =>
    api.get(`/api-health/alerts?limit=${limit}`).then(r => r.data),
  triggerCheck: () => api.post('/api-health/check').then(r => r.data),
};

import client from './client';

export const apiHealthApi = {
  getStatus: () => client.get('/api-health/status').then(r => r.data),
  getHistory: (limit = 60) =>
    client.get(`/api-health/history?limit=${limit}`).then(r => r.data),
  getAlerts: (limit = 50) =>
    client.get(`/api-health/alerts?limit=${limit}`).then(r => r.data),
  triggerCheck: () => client.post('/api-health/check').then(r => r.data),
};

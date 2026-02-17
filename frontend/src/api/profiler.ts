import { api } from './client';

export const profilerApi = {
  getSummary: () => api.get('/profiler/summary').then(r => r.data),
  getRequests: (limit = 50, offset = 0) =>
    api.get(`/profiler/requests?limit=${limit}&offset=${offset}`).then(r => r.data),
  getConfig: () => api.get('/profiler/config').then(r => r.data),
  setConfig: (enabled: boolean) =>
    api.post(`/profiler/config?enabled=${enabled}`).then(r => r.data),
  reset: () => api.post('/profiler/reset').then(r => r.data),
};

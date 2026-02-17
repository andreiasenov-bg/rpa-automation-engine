import client from './client';

export const profilerApi = {
  getSummary: () => client.get('/profiler/summary').then(r => r.data),
  getRequests: (limit = 50, offset = 0) =>
    client.get(`/profiler/requests?limit=${limit}&offset=${offset}`).then(r => r.data),
  getConfig: () => client.get('/profiler/config').then(r => r.data),
  setConfig: (enabled: boolean) =>
    client.post(`/profiler/config?enabled=${enabled}`).then(r => r.data),
  reset: () => client.post('/profiler/reset').then(r => r.data),
};

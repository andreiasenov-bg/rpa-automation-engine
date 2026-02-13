import client from './client';

export const exportApi = {
  executions: (format: 'csv' | 'json' = 'csv', params?: Record<string, string>) =>
    client
      .get('/api/v1/export/executions', {
        params: { format, ...params },
        responseType: 'blob',
      })
      .then((r) => {
        const ext = format === 'json' ? 'json' : 'csv';
        const blob = new Blob([r.data], {
          type: format === 'json' ? 'application/json' : 'text/csv',
        });
        _download(blob, `executions.${ext}`);
      }),

  auditLogs: (format: 'csv' | 'json' = 'csv', params?: Record<string, string>) =>
    client
      .get('/api/v1/export/audit-logs', {
        params: { format, ...params },
        responseType: 'blob',
      })
      .then((r) => {
        const ext = format === 'json' ? 'json' : 'csv';
        const blob = new Blob([r.data], {
          type: format === 'json' ? 'application/json' : 'text/csv',
        });
        _download(blob, `audit_logs.${ext}`);
      }),

  analytics: (format: 'csv' | 'json' = 'csv', params?: Record<string, string>) =>
    client
      .get('/api/v1/export/analytics', {
        params: { format, ...params },
        responseType: 'blob',
      })
      .then((r) => {
        const ext = format === 'json' ? 'json' : 'csv';
        const blob = new Blob([r.data], {
          type: format === 'json' ? 'application/json' : 'text/csv',
        });
        _download(blob, `analytics.${ext}`);
      }),
};

function _download(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

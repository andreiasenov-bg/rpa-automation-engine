/**
 * Storage API client — manage workflow files and detail dashboard.
 */
import client from './client';

export const storageApi = {
  /** List all files in a workflow's storage folder */
  listFiles: (workflowId: string) =>
    client.get(`/storage/workflows/${workflowId}/files`),

  /** Get full workflow detail for dashboard page */
  getWorkflowDetail: (workflowId: string) =>
    client.get(`/storage/workflows/${workflowId}/detail`),

  /** Get latest execution results */
  getLatestResults: (workflowId: string) =>
    client.get(`/storage/workflows/${workflowId}/latest-results`),

  /** Download latest results as JSON file */
  downloadLatestResults: async (workflowId: string, workflowName: string) => {
    const response = await client.get(
      `/storage/workflows/${workflowId}/latest-results/download`,
      { responseType: 'blob' },
    );
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `${workflowName.replace(/\s+/g, '_')}_results.json`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },

  /** Initialize folder structure for a workflow */
  initFolder: (workflowId: string) =>
    client.post(`/storage/workflows/${workflowId}/init`),

  /** Upload a file to a workflow subfolder */
  uploadFile: (workflowId: string, subfolder: string, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return client.post(`/storage/workflows/${workflowId}/upload/${subfolder}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  /** Download a file with authentication (returns blob) */
  downloadFile: async (filePath: string, filename: string) => {
    const response = await client.get(`/storage/files/${filePath}`, {
      responseType: 'blob',
    });
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },

  /** Get overall storage statistics */
  stats: () =>
    client.get('/storage/stats'),
};

export default storageApi;

/**
 * Storage API client — manage workflow files.
 */
import client from './client';

export const storageApi = {
  /** List all files in a workflow's storage folder */
  listFiles: (workflowId: string) =>
    client.get(`/storage/workflows/${workflowId}/files`),

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

  /** Get download URL for a file (unauthenticated — for reference only) */
  getFileUrl: (filePath: string) =>
    `/api/v1/storage/files/${filePath}`,

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

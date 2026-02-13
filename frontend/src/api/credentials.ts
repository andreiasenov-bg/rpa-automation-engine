/**
 * Credentials API module — credential vault CRUD.
 */

import client from './client';

export interface Credential {
  id: string;
  name: string;
  credential_type: string;
  extra_data?: Record<string, unknown> | null;
  created_by_id?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  value?: string | null; // only when include_value=true
}

export interface CredentialListResponse {
  items: Credential[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface CredentialCreate {
  name: string;
  credential_type: string;
  value: string;
  extra_data?: Record<string, unknown>;
}

export interface CredentialUpdate {
  name?: string;
  credential_type?: string;
  value?: string;
  extra_data?: Record<string, unknown>;
}

export async function listCredentials(params?: {
  page?: number;
  per_page?: number;
  search?: string;
  credential_type?: string;
}): Promise<CredentialListResponse> {
  const { data } = await client.get<CredentialListResponse>('/credentials', { params });
  return data;
}

export async function getCredential(id: string, includeValue = false): Promise<Credential> {
  const { data } = await client.get<Credential>(`/credentials/${id}`, {
    params: { include_value: includeValue },
  });
  return data;
}

export async function createCredential(body: CredentialCreate): Promise<Credential> {
  const { data } = await client.post<Credential>('/credentials', body);
  return data;
}

export async function updateCredential(id: string, body: CredentialUpdate): Promise<Credential> {
  const { data } = await client.put<Credential>(`/credentials/${id}`, body);
  return data;
}

export async function deleteCredential(id: string): Promise<void> {
  await client.delete(`/credentials/${id}`);
}

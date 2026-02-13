import client from './client';
import type { User } from '@/types';

export interface UserUpdateRequest {
  first_name?: string;
  last_name?: string;
  is_active?: boolean;
}

export const userApi = {
  list: (page = 1, perPage = 20) =>
    client.get<{ users: User[]; total: number; page: number; per_page: number }>(
      '/users/', { params: { page, per_page: perPage } }
    ).then((r) => r.data),

  get: (id: string) =>
    client.get<User>(`/users/${id}`).then((r) => r.data),

  update: (id: string, data: UserUpdateRequest) =>
    client.put<User>(`/users/${id}`, data).then((r) => r.data),

  deactivate: (id: string) =>
    client.delete(`/users/${id}`),
};

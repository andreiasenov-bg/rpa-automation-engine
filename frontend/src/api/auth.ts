import client from './client';
import type { AuthTokens, LoginRequest, RegisterRequest, User } from '@/types';

export const authApi = {
  login: (data: LoginRequest) =>
    client.post<AuthTokens>('/auth/login', data).then((r) => r.data),

  register: (data: RegisterRequest) =>
    client.post<AuthTokens>('/auth/register', data).then((r) => r.data),

  me: () =>
    client.get<User>('/auth/me').then((r) => r.data),

  refresh: (refreshToken: string) =>
    client.post<AuthTokens>('/auth/refresh', { refresh_token: refreshToken }).then((r) => r.data),
};

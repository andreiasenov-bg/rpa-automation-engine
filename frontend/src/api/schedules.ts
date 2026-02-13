/**
 * Schedules API module — workflow scheduling CRUD.
 */

import client from './client';

export interface Schedule {
  id: string;
  workflow_id: string;
  workflow_name?: string | null;
  name: string;
  cron_expression: string;
  timezone: string;
  is_enabled: boolean;
  next_run_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface ScheduleListResponse {
  items: Schedule[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface ScheduleCreate {
  workflow_id: string;
  name: string;
  cron_expression: string;
  timezone?: string;
  is_enabled?: boolean;
}

export interface ScheduleUpdate {
  name?: string;
  cron_expression?: string;
  timezone?: string;
  is_enabled?: boolean;
}

export async function listSchedules(params?: {
  page?: number;
  per_page?: number;
  workflow_id?: string;
  is_enabled?: boolean;
}): Promise<ScheduleListResponse> {
  const { data } = await client.get<ScheduleListResponse>('/schedules', { params });
  return data;
}

export async function getSchedule(id: string): Promise<Schedule> {
  const { data } = await client.get<Schedule>(`/schedules/${id}`);
  return data;
}

export async function createSchedule(body: ScheduleCreate): Promise<Schedule> {
  const { data } = await client.post<Schedule>('/schedules', body);
  return data;
}

export async function updateSchedule(id: string, body: ScheduleUpdate): Promise<Schedule> {
  const { data } = await client.put<Schedule>(`/schedules/${id}`, body);
  return data;
}

export async function deleteSchedule(id: string): Promise<void> {
  await client.delete(`/schedules/${id}`);
}

export async function toggleSchedule(id: string): Promise<Schedule> {
  const { data } = await client.post<Schedule>(`/schedules/${id}/toggle`);
  return data;
}

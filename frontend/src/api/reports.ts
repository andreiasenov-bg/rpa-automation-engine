/**
 * Reports API — export endpoints, Sheets sync, Looker Studio integration.
 */

import client from './client';

/* ─── Types ─── */

export interface ExportRow {
  id: string;
  workflow_name: string;
  status: string;
  started_at: string;
  completed_at: string;
  duration_ms: number;
  trigger_type: string;
  error_message: string;
}

export interface ExportResult {
  columns: string[];
  rows: ExportRow[];
  total: number;
  period_days: number;
}

export interface SummaryRow {
  date: string;
  total: number;
  completed: number;
  failed: number;
  running: number;
  avg_duration_ms: number;
  success_rate: number;
}

export interface SummaryResult {
  columns: string[];
  rows: SummaryRow[];
  total: number;
  period_days: number;
}

export interface SheetsSyncResult {
  ok: boolean;
  rows_written: number;
  sheet_name: string;
  spreadsheet_id: string;
  message: string;
}

/* ─── API calls ─── */

export async function fetchExportExecutions(days = 30): Promise<ExportResult> {
  const { data } = await client.get<ExportResult>('/analytics/export/executions', {
    params: { days, format: 'json' },
  });
  return data;
}

export async function fetchDailySummary(days = 30): Promise<SummaryResult> {
  const { data } = await client.get<SummaryResult>('/analytics/export/summary', {
    params: { days, format: 'json' },
  });
  return data;
}

export function getExportCsvUrl(type: 'executions' | 'summary', days = 30): string {
  return `/api/v1/analytics/export/${type}?days=${days}&format=csv`;
}

export async function syncToGoogleSheets(
  spreadsheetId: string,
  sheetName = 'RPA Analytics',
): Promise<SheetsSyncResult> {
  const { data } = await client.post<SheetsSyncResult>('/analytics/sheets-sync', {
    spreadsheet_id: spreadsheetId,
    sheet_name: sheetName,
  });
  return data;
}

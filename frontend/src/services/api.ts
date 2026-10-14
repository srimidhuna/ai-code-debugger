import { HealthStatus, DebugResponse } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export async function fetchHealth(): Promise<HealthStatus> {
  const response = await fetch(`${API_BASE_URL}/api/health`);
  if (!response.ok) throw new Error(`Health check failed with status ${response.status}`);
  return response.json();
}

export async function debugCode(code: string, language: string): Promise<DebugResponse> {
  const response = await fetch(`${API_BASE_URL}/api/debug`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code, language }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || `Analysis failed with status ${response.status}`);
  return data as DebugResponse;
}

export async function updateDecision(
  sessionId: string,
  decision: 'Accepted' | 'Rejected'
): Promise<DebugResponse> {
  const response = await fetch(`${API_BASE_URL}/api/history/${sessionId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ decision }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || `Decision update failed with status ${response.status}`);
  return data as DebugResponse;
}

// ── Phase 4 ─────────────────────────────────────────────────────────────────

export interface HistoryListParams {
  q?: string;
  language?: string;
  decision?: string;
  sort?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
}

export interface HistoryListResponse {
  total: number;
  page: number;
  page_size: number;
  sessions: DebugResponse[];
}

export interface ModelSettings {
  model: string;
  timeout_seconds: number;
  max_tokens: number;
  api_key_configured: boolean;
  provider_order: string | null;
  max_source_bytes: number;
  max_source_lines: number;
}

export interface RecentSession {
  id: string;
  timestamp: string;
  language: string;
  summary: string;
  decision: string;
  issues_count: number;
}

export interface DashboardStats {
  total_sessions: number;
  total_issues: number;
  accepted_fixes: number;
  rejected_fixes: number;
  recent_sessions: RecentSession[];
}

export async function fetchHistory(params: HistoryListParams = {}): Promise<HistoryListResponse> {
  const qs = new URLSearchParams();
  if (params.q)         qs.set('q', params.q);
  if (params.language)  qs.set('language', params.language);
  if (params.decision)  qs.set('decision', params.decision);
  if (params.sort)      qs.set('sort', params.sort);
  if (params.page)      qs.set('page', String(params.page));
  if (params.page_size) qs.set('page_size', String(params.page_size));
  const queryString = qs.toString();
  const url = `${API_BASE_URL}/api/history${queryString ? `?${queryString}` : ''}`;
  const r = await fetch(url);
  if (!r.ok) throw new Error(`History fetch failed: ${r.status}`);
  return r.json();
}

export async function fetchSession(sessionId: string): Promise<DebugResponse> {
  const r = await fetch(`${API_BASE_URL}/api/history/${sessionId}`);
  if (!r.ok) throw new Error(`Session fetch failed: ${r.status}`);
  return r.json();
}

export async function deleteSession(sessionId: string): Promise<void> {
  const r = await fetch(`${API_BASE_URL}/api/history/${sessionId}`, { method: 'DELETE' });
  if (!r.ok) {
    const data = await r.json().catch(() => ({}));
    throw new Error((data as { detail?: string }).detail || `Delete failed: ${r.status}`);
  }
}

export async function fetchDashboardStats(): Promise<DashboardStats> {
  const r = await fetch(`${API_BASE_URL}/api/dashboard/stats`);
  if (!r.ok) throw new Error(`Dashboard stats failed: ${r.status}`);
  return r.json();
}

export async function fetchModelSettings(): Promise<ModelSettings> {
  const r = await fetch(`${API_BASE_URL}/api/settings/model`);
  if (!r.ok) throw new Error(`Settings fetch failed: ${r.status}`);
  return r.json();
}

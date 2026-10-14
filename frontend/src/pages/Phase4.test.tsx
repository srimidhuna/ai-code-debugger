/**
 * Phase 4 frontend tests:
 * - HistoryPage renders empty state, table rows, search, pagination controls
 * - DashboardPage shows real stats from API
 * - SettingsPage shows model settings from /api/settings/model
 */
import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';

// ── mock api module ──────────────────────────────────────────────────────────
vi.mock('../services/api', () => ({
  fetchHistory: vi.fn(),
  deleteSession: vi.fn(),
  fetchDashboardStats: vi.fn(),
  fetchModelSettings: vi.fn(),
  fetchHealth: vi.fn(),
}));

import * as api from '../services/api';
import { HistoryPage }   from '../pages/HistoryPage';
import { DashboardPage } from '../pages/DashboardPage';
import { SettingsPage }  from '../pages/SettingsPage';

// ── helpers ──────────────────────────────────────────────────────────────────
const ISO = new Date().toISOString();

function makeSession(overrides = {}) {
  return {
    id: 'ses-1',
    timestamp: ISO,
    language: 'python',
    original_code: 'x = 1',
    fixed_code: 'x = 2',
    summary: 'Null pointer bug fixed',
    issues: [
      { title: 'Bug', severity: 'High', category: 'Logic',
        line: 1, line_end: 1, explanation: 'bad', suggestion: 'fix' },
    ],
    changes: [],
    remaining_concerns: [],
    decision: 'Pending',
    model_name: 'test-model',
    ...overrides,
  };
}

function renderWithRouter(ui: React.ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

// ── HistoryPage ───────────────────────────────────────────────────────────────
describe('HistoryPage', () => {
  const fetchHistory = api.fetchHistory as ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.clearAllMocks();
    window.confirm = vi.fn(() => false);
  });

  it('shows empty state when no sessions', async () => {
    fetchHistory.mockResolvedValue({ total: 0, page: 1, page_size: 10, sessions: [] });
    renderWithRouter(<HistoryPage />);
    await waitFor(() => expect(screen.getByTestId('history-empty')).toBeInTheDocument());
  });

  it('renders session rows', async () => {
    const session = makeSession();
    fetchHistory.mockResolvedValue({ total: 1, page: 1, page_size: 10, sessions: [session] });
    renderWithRouter(<HistoryPage />);
    await waitFor(() =>
      expect(screen.getByTestId(`history-row-${session.id}`)).toBeInTheDocument()
    );
    expect(screen.getByText('Null pointer bug fixed')).toBeInTheDocument();
  });

  it('shows loading state initially', () => {
    fetchHistory.mockReturnValue(new Promise(() => {})); // never resolves
    renderWithRouter(<HistoryPage />);
    expect(screen.getByTestId('history-loading')).toBeInTheDocument();
  });

  it('shows error state on fetch failure', async () => {
    fetchHistory.mockRejectedValue(new Error('Network error'));
    renderWithRouter(<HistoryPage />);
    await waitFor(() => expect(screen.getByTestId('history-error')).toBeInTheDocument());
    expect(screen.getByText(/Network error/)).toBeInTheDocument();
  });

  it('renders search input and language filter', async () => {
    fetchHistory.mockResolvedValue({ total: 0, page: 1, page_size: 10, sessions: [] });
    renderWithRouter(<HistoryPage />);
    expect(screen.getByTestId('history-search-input')).toBeInTheDocument();
    expect(screen.getByTestId('history-language-filter')).toBeInTheDocument();
    expect(screen.getByTestId('history-decision-filter')).toBeInTheDocument();
  });

  it('shows pagination when total > page_size', async () => {
    const sessions = Array.from({ length: 10 }, (_, i) => makeSession({ id: `ses-${i}` }));
    fetchHistory.mockResolvedValue({ total: 25, page: 1, page_size: 10, sessions });
    renderWithRouter(<HistoryPage />);
    await waitFor(() => expect(screen.getByTestId('history-pagination')).toBeInTheDocument());
    expect(screen.getByTestId('history-prev-btn')).toBeDisabled();
    expect(screen.getByTestId('history-next-btn')).not.toBeDisabled();
  });

  it('does not show pagination when total <= page_size', async () => {
    fetchHistory.mockResolvedValue({ total: 2, page: 1, page_size: 10, sessions: [makeSession(), makeSession({ id: 'ses-2' })] });
    renderWithRouter(<HistoryPage />);
    await waitFor(() => expect(screen.getByTestId('history-table')).toBeInTheDocument());
    expect(screen.queryByTestId('history-pagination')).not.toBeInTheDocument();
  });
});

// ── DashboardPage ─────────────────────────────────────────────────────────────
describe('DashboardPage', () => {
  const fetchDashboardStats = api.fetchDashboardStats as ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows metrics from API', async () => {
    fetchDashboardStats.mockResolvedValue({
      total_sessions: 7,
      total_issues: 14,
      accepted_fixes: 3,
      rejected_fixes: 2,
      recent_sessions: [],
    });
    renderWithRouter(<DashboardPage />);
    await waitFor(() =>
      expect(screen.getByTestId('metric-total-sessions')).toHaveTextContent('7')
    );
    expect(screen.getByTestId('metric-issues-detected')).toHaveTextContent('14');
    expect(screen.getByTestId('metric-accepted-fixes')).toHaveTextContent('3');
    expect(screen.getByTestId('metric-rejected-fixes')).toHaveTextContent('2');
  });

  it('shows empty recent activity section when no sessions', async () => {
    fetchDashboardStats.mockResolvedValue({
      total_sessions: 0, total_issues: 0, accepted_fixes: 0, rejected_fixes: 0,
      recent_sessions: [],
    });
    renderWithRouter(<DashboardPage />);
    await waitFor(() =>
      expect(screen.getByTestId('dashboard-no-sessions')).toBeInTheDocument()
    );
  });

  it('shows recent sessions list', async () => {
    fetchDashboardStats.mockResolvedValue({
      total_sessions: 1, total_issues: 2, accepted_fixes: 0, rejected_fixes: 0,
      recent_sessions: [{
        id: 'r1', timestamp: ISO, language: 'python',
        summary: 'Fixed off-by-one', decision: 'Accepted', issues_count: 2,
      }],
    });
    renderWithRouter(<DashboardPage />);
    await waitFor(() =>
      expect(screen.getByTestId('recent-activity-list')).toBeInTheDocument()
    );
    expect(screen.getByText('Fixed off-by-one')).toBeInTheDocument();
  });

  it('shows error banner when stats fetch fails', async () => {
    fetchDashboardStats.mockRejectedValue(new Error('DB error'));
    renderWithRouter(<DashboardPage />);
    await waitFor(() =>
      expect(screen.getByTestId('dashboard-error')).toBeInTheDocument()
    );
  });
});

// ── SettingsPage ──────────────────────────────────────────────────────────────
describe('SettingsPage', () => {
  const fetchModelSettings = api.fetchModelSettings as ReturnType<typeof vi.fn>;
  const fetchHealth        = api.fetchHealth        as ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders settings page container', async () => {
    fetchHealth.mockResolvedValue({ status: 'healthy' });
    fetchModelSettings.mockResolvedValue({
      model: 'qwen/qwen-2.5-coder-32b-instruct',
      timeout_seconds: 60,
      max_tokens: 4096,
      api_key_configured: true,
      provider_order: null,
      max_source_bytes: 102400,
      max_source_lines: 3000,
    });
    renderWithRouter(<SettingsPage />);
    await waitFor(() => expect(screen.getByTestId('settings-page')).toBeInTheDocument());
  });

  it('shows api key configured badge when key is present', async () => {
    fetchHealth.mockResolvedValue({ status: 'healthy' });
    fetchModelSettings.mockResolvedValue({
      model: 'qwen/qwen-2.5-coder-32b-instruct', timeout_seconds: 60,
      max_tokens: 4096, api_key_configured: true, provider_order: null,
      max_source_bytes: 102400, max_source_lines: 3000,
    });
    renderWithRouter(<SettingsPage />);
    await waitFor(() => expect(screen.getByTestId('settings-apikey-ok')).toBeInTheDocument());
  });

  it('shows api key missing badge when key is absent', async () => {
    fetchHealth.mockResolvedValue({ status: 'healthy' });
    fetchModelSettings.mockResolvedValue({
      model: 'qwen/qwen-2.5-coder-32b-instruct', timeout_seconds: 60,
      max_tokens: 4096, api_key_configured: false, provider_order: null,
      max_source_bytes: 102400, max_source_lines: 3000,
    });
    renderWithRouter(<SettingsPage />);
    await waitFor(() => expect(screen.getByTestId('settings-apikey-missing')).toBeInTheDocument());
  });

  it('shows backend operational badge when healthy', async () => {
    fetchHealth.mockResolvedValue({ status: 'healthy' });
    fetchModelSettings.mockResolvedValue({
      model: 'qwen/qwen-2.5-coder-32b-instruct', timeout_seconds: 60,
      max_tokens: 4096, api_key_configured: true, provider_order: null,
      max_source_bytes: 102400, max_source_lines: 3000,
    });
    renderWithRouter(<SettingsPage />);
    await waitFor(() => expect(screen.getByTestId('settings-health-ok')).toBeInTheDocument());
  });

  it('persists theme selection to localStorage and updates root element class', async () => {
    fetchHealth.mockResolvedValue({ status: 'healthy' });
    fetchModelSettings.mockResolvedValue({
      model: 'qwen/qwen-2.5-coder-32b-instruct', timeout_seconds: 60,
      max_tokens: 4096, api_key_configured: true, provider_order: null,
      max_source_bytes: 102400, max_source_lines: 3000,
    });
    renderWithRouter(<SettingsPage />);
    await waitFor(() => expect(screen.getByTestId('settings-theme-select')).toBeInTheDocument());

    const themeSelect = screen.getByTestId('settings-theme-select') as HTMLSelectElement;
    fireEvent.change(themeSelect, { target: { value: 'light' } });
    expect(themeSelect.value).toBe('light');
    expect(localStorage.getItem('app_theme')).toBe('light');
    expect(document.documentElement.classList.contains('light')).toBe(true);
    expect(document.documentElement.getAttribute('data-theme')).toBe('light');

    fireEvent.change(themeSelect, { target: { value: 'vs-dark' } });
    expect(localStorage.getItem('app_theme')).toBe('vs-dark');
    expect(document.documentElement.classList.contains('light')).toBe(false);
    expect(document.documentElement.getAttribute('data-theme')).toBe('vs-dark');
  });

  it('persists default language selection to localStorage', async () => {
    fetchHealth.mockResolvedValue({ status: 'healthy' });
    fetchModelSettings.mockResolvedValue({
      model: 'qwen/qwen-2.5-coder-32b-instruct', timeout_seconds: 60,
      max_tokens: 4096, api_key_configured: true, provider_order: null,
      max_source_bytes: 102400, max_source_lines: 3000,
    });
    renderWithRouter(<SettingsPage />);
    await waitFor(() => expect(screen.getByTestId('settings-default-lang-select')).toBeInTheDocument());

    const langSelect = screen.getByTestId('settings-default-lang-select') as HTMLSelectElement;
    fireEvent.change(langSelect, { target: { value: 'cpp' } });
    expect(langSelect.value).toBe('cpp');
    expect(localStorage.getItem('app_default_language')).toBe('cpp');
  });
});

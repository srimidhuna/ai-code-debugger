import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { AppRoutes } from './App';

// Mock global fetch for health check, stats, and history
beforeEach(() => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockImplementation((url: string) => {
      const u = String(url);
      if (u.includes('/api/health')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            status: 'healthy',
            timestamp: new Date().toISOString(),
            version: '1.0.0',
            service: 'ai-code-debugger-backend',
          }),
        });
      }
      if (u.includes('/api/dashboard/stats')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            total_sessions: 0,
            total_issues: 0,
            accepted_fixes: 0,
            rejected_fixes: 0,
            recent_sessions: [],
          }),
        });
      }
      if (u.includes('/api/settings/model')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            model: 'qwen/qwen-2.5-coder-32b-instruct',
            timeout_seconds: 60,
            max_tokens: 4096,
            api_key_configured: true,
            provider_order: null,
            max_source_bytes: 102400,
            max_source_lines: 3000,
          }),
        });
      }
      if (u.includes('/api/history')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            total: 0,
            page: 1,
            page_size: 10,
            sessions: [],
          }),
        });
      }
      return Promise.resolve({
        ok: true,
        json: async () => ({}),
      });
    })
  );
});

describe('AI Code Debugger Frontend Smoke Tests', () => {
  it('renders application shell and dashboard overview', async () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <AppRoutes />
      </MemoryRouter>
    );

    // Verify brand header in Sidebar
    expect(screen.getByText('AI Code Debugger')).toBeInTheDocument();
    expect(screen.getByText('Qwen2.5-Coder-32B')).toBeInTheDocument();

    // Verify navigation links
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Code Debugger')).toBeInTheDocument();
    expect(screen.getByText('History')).toBeInTheDocument();
    expect(screen.getByText('Settings')).toBeInTheDocument();

    // Verify Dashboard page content
    expect(screen.getByText('Welcome to AI Code Debugger')).toBeInTheDocument();
    expect(screen.getByText('Total Sessions')).toBeInTheDocument();
    expect(screen.getByText('Start Debugging')).toBeInTheDocument();

    // Verify backend connectivity badge updates
    await waitFor(() => {
      expect(screen.getByText('Backend API Connected')).toBeInTheDocument();
    });
  });

  it('navigates to Code Debugger route', () => {
    render(
      <MemoryRouter initialEntries={['/debugger']}>
        <AppRoutes />
      </MemoryRouter>
    );

    expect(screen.getByText('Source Code')).toBeInTheDocument();
    expect(screen.getByText('Analyze Code')).toBeInTheDocument();
    expect(screen.getByText('Load Example')).toBeInTheDocument();
  });

  it('navigates to History route', async () => {
    render(
      <MemoryRouter initialEntries={['/history']}>
        <AppRoutes />
      </MemoryRouter>
    );

    expect(screen.getByText('Debugging Session History')).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText('No sessions found')).toBeInTheDocument();
    });
  });

  it('navigates to Settings route', () => {
    render(
      <MemoryRouter initialEntries={['/settings']}>
        <AppRoutes />
      </MemoryRouter>
    );

    expect(screen.getByText('Settings & Configuration')).toBeInTheDocument();
    expect(screen.getByText('FastAPI Backend Endpoint')).toBeInTheDocument();
  });
});

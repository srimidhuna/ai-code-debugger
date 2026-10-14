import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Bug, CheckCircle, XCircle, Code, PlusCircle, ArrowRight,
  Loader2, AlertTriangle, Clock, History,
} from 'lucide-react';
import { fetchDashboardStats, DashboardStats, RecentSession } from '../services/api';

const LANGUAGE_LABELS: Record<string, string> = {
  python: 'Python', java: 'Java', c: 'C', cpp: 'C++', javascript: 'JavaScript',
};

const DECISION_COLORS: Record<string, string> = {
  Pending:  'text-yellow-400 bg-yellow-500/10 border-yellow-500/20',
  Accepted: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
  Rejected: 'text-rose-400 bg-rose-500/10 border-rose-500/20',
};

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const [stats, setStats]     = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);

  useEffect(() => {
    fetchDashboardStats()
      .then(setStats)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load stats'))
      .finally(() => setLoading(false));
  }, []);

  const metrics = stats
    ? [
        { key: 'total-sessions', label: 'Total Sessions', value: stats.total_sessions,   icon: Code,         desc: 'Logged debugging runs' },
        { key: 'issues-detected', label: 'Issues Detected',  value: stats.total_issues,    icon: Bug,          desc: 'Syntax, logic & runtime' },
        { key: 'accepted-fixes', label: 'Accepted Fixes',   value: stats.accepted_fixes,  icon: CheckCircle,  desc: 'Applied to codebase' },
        { key: 'rejected-fixes', label: 'Rejected Fixes',   value: stats.rejected_fixes,  icon: XCircle,      desc: 'Discarded proposals' },
      ]
    : [
        { key: 'total-sessions', label: 'Total Sessions', value: 0, icon: Code,        desc: 'Logged debugging runs' },
        { key: 'issues-detected', label: 'Issues Detected', value: 0, icon: Bug,        desc: 'Syntax, logic & runtime' },
        { key: 'accepted-fixes', label: 'Accepted Fixes',  value: 0, icon: CheckCircle, desc: 'Applied to codebase' },
        { key: 'rejected-fixes', label: 'Rejected Fixes',  value: 0, icon: XCircle,    desc: 'Discarded proposals' },
      ];

  return (
    <div className="space-y-6" data-testid="dashboard-page">
      {/* Hero */}
      <div className="p-6 rounded-2xl bg-gradient-to-r from-zinc-900 to-zinc-900/50 border border-zinc-800 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="space-y-1">
          <h2 className="text-xl font-bold tracking-tight text-zinc-100">
            Welcome to AI Code Debugger
          </h2>
          <p className="text-sm text-zinc-400 max-w-2xl leading-relaxed">
            AI-powered code debugging powered by{' '}
            <span className="text-emerald-400 font-medium">Qwen2.5 Coder 32B Instruct</span>.
            Detect syntax, logic, and runtime issues with side-by-side diffs.
          </p>
        </div>
        <button
          id="dashboard-start-btn"
          data-testid="dashboard-start-btn"
          onClick={() => navigate('/debugger')}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-zinc-950 font-semibold text-sm transition-colors shrink-0"
        >
          <PlusCircle className="w-4 h-4" />
          Start Debugging
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-3 p-3 rounded-lg bg-rose-950/40 border border-rose-800/60 text-rose-300 text-sm" data-testid="dashboard-error">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {error} — stats may be stale.
        </div>
      )}

      {/* Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"
           data-testid="dashboard-metrics">
        {metrics.map((item) => {
          const Icon = item.icon;
          return (
            <div key={item.label}
                 className="p-5 rounded-xl bg-zinc-900/80 border border-zinc-800 flex flex-col justify-between">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium uppercase tracking-wider text-zinc-500">
                  {item.label}
                </span>
                <Icon className="w-4 h-4 text-zinc-400" />
              </div>
              <div className="mt-4">
                {loading
                  ? <div className="h-8 w-12 bg-zinc-800 rounded animate-pulse" />
                  : <span className="text-3xl font-bold text-zinc-100 font-mono"
                           data-testid={`metric-${item.key}`}>
                      {item.value}
                    </span>
                }
                <p className="text-xs text-zinc-500 mt-1">{item.desc}</p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Recent Activity */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 overflow-hidden">
        <div className="px-5 py-3 border-b border-zinc-800 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-zinc-200 flex items-center gap-2">
            <History className="w-4 h-4 text-emerald-400" />
            Recent Activity
          </h3>
          {stats && stats.total_sessions > 5 && (
            <button onClick={() => navigate('/history')}
              className="text-xs text-emerald-400 hover:text-emerald-300 font-medium">
              View all →
            </button>
          )}
        </div>

        {loading && (
          <div className="flex items-center justify-center py-10 gap-2 text-zinc-400">
            <Loader2 className="w-4 h-4 animate-spin" />
            Loading activity…
          </div>
        )}

        {!loading && stats && (stats.recent_sessions?.length ?? 0) === 0 && (
          <div className="py-12 text-center space-y-2" data-testid="dashboard-no-sessions">
            <p className="text-sm text-zinc-500">No debugging sessions yet.</p>
            <button onClick={() => navigate('/debugger')}
              className="text-sm text-emerald-400 hover:text-emerald-300 font-medium">
              Start your first session →
            </button>
          </div>
        )}

        {!loading && stats && (stats.recent_sessions?.length ?? 0) > 0 && (
          <ul className="divide-y divide-zinc-800/60" data-testid="recent-activity-list">
            {(stats.recent_sessions || []).map((s: RecentSession) => (
              <li key={s.id}
                  className="flex items-center gap-4 px-5 py-3 hover:bg-zinc-800/30 transition-colors cursor-pointer"
                  onClick={() => navigate(`/history/${s.id}`)}>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-zinc-200 truncate">{s.summary}</p>
                  <p className="text-xs text-zinc-500 mt-0.5">
                    {LANGUAGE_LABELS[s.language] ?? s.language} &nbsp;·&nbsp;
                    {new Date(s.timestamp).toLocaleString(undefined, {
                      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
                    })}
                    {s.issues_count > 0 && ` · ${s.issues_count} issue${s.issues_count === 1 ? '' : 's'}`}
                  </p>
                </div>
                <span className={`shrink-0 inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${
                  DECISION_COLORS[s.decision] ?? 'text-zinc-400 bg-zinc-800 border-zinc-700'
                }`}>
                  {s.decision === 'Accepted' && <CheckCircle className="w-3 h-3" />}
                  {s.decision === 'Rejected' && <XCircle className="w-3 h-3" />}
                  {s.decision === 'Pending'  && <Clock className="w-3 h-3" />}
                  {s.decision}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};

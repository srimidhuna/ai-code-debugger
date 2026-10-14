import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  History, Search, Trash2, ChevronLeft, ChevronRight,
  Inbox, Loader2, AlertTriangle, ArrowUpDown, ExternalLink,
  CheckCircle, XCircle, Clock, X,
} from 'lucide-react';
import { fetchHistory, deleteSession, HistoryListResponse } from '../services/api';

const LANGUAGE_LABELS: Record<string, string> = {
  python: 'Python', java: 'Java', c: 'C', cpp: 'C++', javascript: 'JavaScript',
};

const DECISION_COLORS: Record<string, string> = {
  Pending: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20',
  Accepted: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
  Rejected: 'text-rose-400 bg-rose-500/10 border-rose-500/20',
};

const DECISION_ICONS: Record<string, React.ReactNode> = {
  Accepted: <CheckCircle className="w-3 h-3" />,
  Rejected: <XCircle className="w-3 h-3" />,
  Pending:  <Clock className="w-3 h-3" />,
};

type SortOrder = 'asc' | 'desc';
const PAGE_SIZE = 10;

export const HistoryPage: React.FC = () => {
  const navigate = useNavigate();

  const [data, setData]         = useState<HistoryListResponse | null>(null);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState<string | null>(null);
  const [q, setQ]               = useState('');
  const [draftQ, setDraftQ]     = useState('');
  const [language, setLanguage] = useState('');
  const [decision, setDecision] = useState('');
  const [sort, setSort]         = useState<SortOrder>('desc');
  const [page, setPage]         = useState(1);
  const [deleting, setDeleting] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    fetchHistory({ q: q || undefined, language: language || undefined,
                   decision: decision || undefined, sort, page, page_size: PAGE_SIZE })
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load history'))
      .finally(() => setLoading(false));
  }, [q, language, decision, sort, page]);

  useEffect(() => { load(); }, [load]);

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    setQ(draftQ);
    setPage(1);
  }

  function clearSearch() {
    setDraftQ('');
    setQ('');
    setPage(1);
  }

  async function handleDelete(id: string) {
    if (!confirm('Delete this debugging session? This cannot be undone.')) return;
    setDeleting(id);
    try {
      await deleteSession(id);
      load();
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Delete failed');
    } finally {
      setDeleting(null);
    }
  }

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  return (
    <div className="space-y-5" data-testid="history-page">
      {/* Header */}
      <div className="border-b border-zinc-800 pb-4 flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-xl font-bold text-zinc-100 flex items-center gap-2">
            <History className="w-5 h-5 text-emerald-400" />
            Debugging Session History
          </h2>
          <p className="text-sm text-zinc-400 mt-1">
            {data ? `${data.total} session${data.total === 1 ? '' : 's'}` : 'Loading…'}
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <form onSubmit={handleSearch} className="relative flex items-center gap-2 flex-1 min-w-48">
          <Search className="absolute left-3 w-4 h-4 text-zinc-400 pointer-events-none" />
          <input
            id="history-search-input"
            data-testid="history-search-input"
            type="text"
            value={draftQ}
            onChange={(e) => setDraftQ(e.target.value)}
            placeholder="Search summaries…"
            className="w-full pl-9 pr-8 py-2 rounded-lg bg-zinc-900 border border-zinc-700 text-sm text-zinc-100
                       placeholder-zinc-500 focus:outline-none focus:border-emerald-500/50"
          />
          {draftQ && (
            <button type="button" onClick={clearSearch}
              className="absolute right-2 text-zinc-400 hover:text-zinc-200">
              <X className="w-4 h-4" />
            </button>
          )}
        </form>

        <select
          id="history-language-filter"
          data-testid="history-language-filter"
          value={language}
          onChange={(e) => { setLanguage(e.target.value); setPage(1); }}
          className="px-3 py-2 rounded-lg bg-zinc-900 border border-zinc-700 text-sm text-zinc-100
                     focus:outline-none focus:border-emerald-500/50"
        >
          <option value="">All languages</option>
          {Object.entries(LANGUAGE_LABELS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>

        <select
          id="history-decision-filter"
          data-testid="history-decision-filter"
          value={decision}
          onChange={(e) => { setDecision(e.target.value); setPage(1); }}
          className="px-3 py-2 rounded-lg bg-zinc-900 border border-zinc-700 text-sm text-zinc-100
                     focus:outline-none focus:border-emerald-500/50"
        >
          <option value="">All decisions</option>
          <option value="Pending">Pending</option>
          <option value="Accepted">Accepted</option>
          <option value="Rejected">Rejected</option>
        </select>

        <button
          id="history-sort-btn"
          data-testid="history-sort-btn"
          onClick={() => { setSort(s => s === 'desc' ? 'asc' : 'desc'); setPage(1); }}
          className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-zinc-900 border border-zinc-700
                     text-sm text-zinc-300 hover:text-zinc-100 hover:border-zinc-600 transition-colors"
          title={sort === 'desc' ? 'Newest first' : 'Oldest first'}
        >
          <ArrowUpDown className="w-3.5 h-3.5" />
          {sort === 'desc' ? 'Newest' : 'Oldest'}
        </button>
      </div>

      {/* State: loading */}
      {loading && (
        <div className="flex items-center justify-center py-16 gap-3 text-zinc-400"
             data-testid="history-loading">
          <Loader2 className="w-5 h-5 animate-spin" />
          Loading sessions…
        </div>
      )}

      {/* State: error */}
      {!loading && error && (
        <div className="flex items-center gap-3 p-4 rounded-lg bg-rose-950/40 border border-rose-800/60
                        text-rose-300 text-sm" data-testid="history-error">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {error}
          <button onClick={load} className="ml-auto underline hover:no-underline text-rose-200">Retry</button>
        </div>
      )}

      {/* State: empty */}
      {!loading && !error && data && data.total === 0 && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-12 text-center space-y-3"
             data-testid="history-empty">
          <div className="w-12 h-12 mx-auto rounded-full bg-zinc-800/80 border border-zinc-700/60
                          flex items-center justify-center">
            <Inbox className="w-6 h-6 text-zinc-400" />
          </div>
          <h3 className="text-base font-semibold text-zinc-200">No sessions found</h3>
          <p className="text-sm text-zinc-500 max-w-sm mx-auto">
            {q || language || decision
              ? 'No sessions match your filters. Try clearing them.'
              : 'Start your first debugging session and it will appear here.'}
          </p>
        </div>
      )}

      {/* Table */}
      {!loading && !error && data && data.sessions.length > 0 && (
        <div className="rounded-xl border border-zinc-800 overflow-hidden" data-testid="history-table">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-zinc-900/80 border-b border-zinc-800 text-xs text-zinc-400 uppercase tracking-wide">
                <th className="text-left px-4 py-3 font-medium">Date</th>
                <th className="text-left px-4 py-3 font-medium">Language</th>
                <th className="text-left px-4 py-3 font-medium">Summary</th>
                <th className="text-center px-4 py-3 font-medium">Issues</th>
                <th className="text-center px-4 py-3 font-medium">Decision</th>
                <th className="text-right px-4 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {data.sessions.map((s, i) => (
                <tr key={s.id}
                    className={`border-b border-zinc-800/50 hover:bg-zinc-800/30 transition-colors ${
                      i % 2 === 0 ? 'bg-zinc-900/20' : 'bg-transparent'
                    }`}
                    data-testid={`history-row-${s.id}`}>
                  <td className="px-4 py-3 text-zinc-400 whitespace-nowrap font-mono text-xs">
                    {new Date(s.timestamp).toLocaleString(undefined, {
                      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
                    })}
                  </td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-0.5 rounded text-xs font-medium bg-zinc-800 text-zinc-300">
                      {LANGUAGE_LABELS[s.language] ?? s.language}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-zinc-200 max-w-xs truncate" title={s.summary}>
                    {s.summary}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className="font-mono text-zinc-300">{s.issues.length}</span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${
                      DECISION_COLORS[s.decision] ?? 'text-zinc-400 bg-zinc-800 border-zinc-700'
                    }`}>
                      {DECISION_ICONS[s.decision]}
                      {s.decision}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        id={`view-session-${s.id}`}
                        data-testid={`view-session-${s.id}`}
                        onClick={() => navigate(`/history/${s.id}`)}
                        className="p-1.5 rounded text-zinc-400 hover:text-zinc-100 hover:bg-zinc-700/50 transition-colors"
                        title="View session details"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                      </button>
                      <button
                        id={`delete-session-${s.id}`}
                        data-testid={`delete-session-${s.id}`}
                        onClick={() => handleDelete(s.id)}
                        disabled={deleting === s.id}
                        className="p-1.5 rounded text-zinc-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Delete session"
                      >
                        {deleting === s.id
                          ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          : <Trash2 className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {!loading && !error && totalPages > 1 && (
        <div className="flex items-center justify-between text-sm text-zinc-400"
             data-testid="history-pagination">
          <span>
            Page {page} of {totalPages} &nbsp;·&nbsp; {data?.total} sessions
          </span>
          <div className="flex items-center gap-2">
            <button
              id="history-prev-btn"
              data-testid="history-prev-btn"
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="p-1.5 rounded border border-zinc-700 disabled:opacity-40 hover:bg-zinc-800 transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              id="history-next-btn"
              data-testid="history-next-btn"
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="p-1.5 rounded border border-zinc-700 disabled:opacity-40 hover:bg-zinc-800 transition-colors"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

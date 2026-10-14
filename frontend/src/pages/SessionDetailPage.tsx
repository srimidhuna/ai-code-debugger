import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, CheckCircle, XCircle, Clock, AlertTriangle,
  Loader2, Bug, Code2, Lightbulb,
} from 'lucide-react';
import { fetchSession } from '../services/api';
import { DebugResponse } from '../types';
import { DiffViewer } from '../components/DiffViewer';

const LANGUAGE_LABELS: Record<string, string> = {
  python: 'Python', java: 'Java', c: 'C', cpp: 'C++', javascript: 'JavaScript',
};
const SEVERITY_COLORS: Record<string, string> = {
  Critical: 'border-red-500/40 bg-red-500/5 text-red-400',
  High:     'border-orange-500/40 bg-orange-500/5 text-orange-400',
  Medium:   'border-yellow-500/40 bg-yellow-500/5 text-yellow-400',
  Low:      'border-zinc-600 bg-zinc-800/40 text-zinc-300',
};
const DECISION_META: Record<string, { color: string; Icon: React.ElementType }> = {
  Accepted: { color: 'text-emerald-400', Icon: CheckCircle },
  Rejected: { color: 'text-rose-400',    Icon: XCircle },
  Pending:  { color: 'text-yellow-400',  Icon: Clock },
};

export const SessionDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [session, setSession] = useState<DebugResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);
  const [showDiff, setShowDiff] = useState(false);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    fetchSession(id)
      .then(setSession)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load session'))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return (
    <div className="flex items-center justify-center py-24 gap-3 text-zinc-400"
         data-testid="session-detail-loading">
      <Loader2 className="w-5 h-5 animate-spin" />
      Loading session…
    </div>
  );

  if (error || !session) return (
    <div className="space-y-4" data-testid="session-detail-error">
      <button onClick={() => navigate('/history')}
        className="flex items-center gap-1.5 text-sm text-zinc-400 hover:text-zinc-200">
        <ArrowLeft className="w-4 h-4" /> Back to History
      </button>
      <div className="flex items-center gap-3 p-4 rounded-lg bg-rose-950/40 border border-rose-800/60 text-rose-300 text-sm">
        <AlertTriangle className="w-4 h-4 shrink-0" />
        {error ?? 'Session not found.'}
      </div>
    </div>
  );

  const dm = DECISION_META[session.decision] ?? DECISION_META.Pending;
  const DecisionIcon = dm.Icon;

  return (
    <div className="space-y-6 max-w-4xl" data-testid="session-detail-page">
      {/* Back + Header */}
      <div className="space-y-3">
        <button id="session-detail-back-btn" onClick={() => navigate('/history')}
          className="flex items-center gap-1.5 text-sm text-zinc-400 hover:text-zinc-200 transition-colors">
          <ArrowLeft className="w-4 h-4" /> Back to History
        </button>
        <div className="flex items-center gap-3 flex-wrap">
          <span className="px-2.5 py-1 rounded text-xs font-medium bg-zinc-800 text-zinc-300">
            {LANGUAGE_LABELS[session.language] ?? session.language}
          </span>
          <span className={`inline-flex items-center gap-1.5 text-sm font-medium ${dm.color}`}>
            <DecisionIcon className="w-4 h-4" />
            {session.decision}
          </span>
          <span className="text-xs text-zinc-500 font-mono">
            {new Date(session.timestamp).toLocaleString()}
          </span>
        </div>
        <h2 className="text-base font-semibold text-zinc-100">{session.summary}</h2>
      </div>

      {/* Diff toggle */}
      <div className="flex gap-3">
        <button
          id="session-detail-toggle-diff-btn"
          data-testid="session-detail-toggle-diff-btn"
          onClick={() => setShowDiff(v => !v)}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-zinc-800 border border-zinc-700 text-sm text-zinc-200 hover:bg-zinc-700 transition-colors"
        >
          <Code2 className="w-4 h-4 text-emerald-400" />
          {showDiff ? 'Hide Diff' : 'View Code Diff'}
        </button>
      </div>

      {showDiff && (
        <div className="rounded-xl border border-zinc-800 overflow-hidden"
             data-testid="session-detail-diff">
          <DiffViewer
            originalCode={session.original_code}
            fixedCode={session.fixed_code}
            language={session.language as any}
            decision={session.decision}
            onApply={async () => { setShowDiff(false); }}
            onReject={async () => { setShowDiff(false); }}
            onRestore={() => { setShowDiff(false); }}
          />
        </div>
      )}

      {/* Issues */}
      {session.issues.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-zinc-200 flex items-center gap-2">
            <Bug className="w-4 h-4 text-rose-400" />
            Detected Issues ({session.issues.length})
          </h3>
          {session.issues.map((issue, i) => (
            <div key={i}
                 className={`p-4 rounded-xl border ${SEVERITY_COLORS[issue.severity] ?? 'border-zinc-700 bg-zinc-900/40 text-zinc-300'}`}>
              <div className="flex items-start justify-between gap-3 flex-wrap">
                <span className="font-medium text-sm">{issue.title}</span>
                <div className="flex items-center gap-2 shrink-0">
                  <span className="text-xs px-1.5 py-0.5 rounded bg-zinc-800/80 text-zinc-400">
                    {issue.category}
                  </span>
                  <span className="text-xs font-medium">{issue.severity}</span>
                  {issue.line && (
                    <span className="text-xs text-zinc-500 font-mono">
                      L{issue.line}{issue.line_end && issue.line_end !== issue.line ? `–${issue.line_end}` : ''}
                    </span>
                  )}
                </div>
              </div>
              <p className="text-sm text-zinc-300 mt-2 leading-relaxed">{issue.explanation}</p>
              {issue.suggestion && (
                <div className="mt-2 flex gap-2 text-xs text-zinc-400">
                  <Lightbulb className="w-3.5 h-3.5 shrink-0 mt-0.5 text-yellow-400" />
                  <span>{issue.suggestion}</span>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Changes */}
      {session.changes.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-zinc-200">Applied Changes</h3>
          <ul className="space-y-2">
            {session.changes.map((c, i) => (
              <li key={i} className="text-sm text-zinc-300 p-3 rounded-lg bg-zinc-900/60 border border-zinc-800">
                <span className="text-emerald-400 font-medium">{c.description}</span>
                {c.reason && <span className="text-zinc-500"> — {c.reason}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Remaining Concerns */}
      {session.remaining_concerns.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-zinc-200">Remaining Concerns</h3>
          <ul className="space-y-1">
            {session.remaining_concerns.map((c, i) => (
              <li key={i} className="text-sm text-yellow-300/80 flex gap-2">
                <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5 text-yellow-400" />
                {c}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

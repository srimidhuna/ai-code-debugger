import React, { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { Activity, CheckCircle2, AlertCircle, RefreshCw } from 'lucide-react';
import { fetchHealth } from '../services/api';
import { HealthStatus } from '../types';

export const Navbar: React.FC = () => {
  const location = useLocation();
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const checkStatus = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchHealth();
      setHealth(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Backend unreachable');
      setHealth(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkStatus();
    const interval = setInterval(checkStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const getPageTitle = () => {
    switch (location.pathname) {
      case '/':
        return 'Dashboard Overview';
      case '/debugger':
        return 'Code Debugger Workspace';
      case '/history':
        return 'Debugging History';
      case '/settings':
        return 'Application Settings';
      default:
        return 'AI Code Debugger';
    }
  };

  return (
    <header className="h-16 border-b border-zinc-800 bg-zinc-900/60 backdrop-blur px-6 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <h1 className="text-base font-semibold text-zinc-100">{getPageTitle()}</h1>
        <span className="text-xs px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-400 font-mono">
          Phase 1 Skeleton
        </span>
      </div>

      <div className="flex items-center gap-3">
        {/* Backend Connectivity Status Pill */}
        <div
          data-testid="backend-status-badge"
          title={error ? `Error: ${error}` : 'Backend connection healthy'}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
            loading
              ? 'bg-zinc-800/80 border-zinc-700 text-zinc-400'
              : health?.status === 'healthy'
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
              : 'bg-rose-500/10 border-rose-500/30 text-rose-400'
          }`}
        >
          {loading ? (
            <Activity className="w-3.5 h-3.5 animate-spin text-zinc-400" />
          ) : health?.status === 'healthy' ? (
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
          ) : (
            <AlertCircle className="w-3.5 h-3.5 text-rose-400" />
          )}

          <span>
            {loading
              ? 'Checking API...'
              : health?.status === 'healthy'
              ? 'Backend API Connected'
              : 'Backend Disconnected'}
          </span>

          <button
            onClick={checkStatus}
            title="Refresh connection status"
            className="p-0.5 hover:text-zinc-200 transition-colors ml-0.5"
            aria-label="Refresh status"
          >
            <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {/* Model Tag */}
        <div className="hidden sm:flex items-center gap-1.5 text-xs text-zinc-400 bg-zinc-800/80 border border-zinc-700/60 px-3 py-1.5 rounded-full font-mono">
          <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
          <span>qwen-2.5-coder-32b</span>
        </div>
      </div>
    </header>
  );
};

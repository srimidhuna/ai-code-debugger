import React, { useEffect, useState } from 'react';
import {
  Settings as SettingsIcon, Server, Cpu, Database, FileText,
  CheckCircle, AlertTriangle, Key, Palette, Globe,
} from 'lucide-react';
import { fetchHealth, fetchModelSettings, ModelSettings } from '../services/api';
import { HealthStatus, SupportedLanguage } from '../types';

export const SettingsPage: React.FC = () => {
  const [health, setHealth]       = useState<HealthStatus | null>(null);
  const [model, setModel]         = useState<ModelSettings | null>(null);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState<string | null>(null);

  // User preferences (persisted in localStorage)
  const [theme, setTheme] = useState<string>(() => {
    return localStorage.getItem('app_theme') || 'vs-dark';
  });

  const [defaultLang, setDefaultLang] = useState<SupportedLanguage>(() => {
    return (localStorage.getItem('app_default_language') as SupportedLanguage) || 'python';
  });

  const handleThemeChange = (newTheme: string) => {
    setTheme(newTheme);
    localStorage.setItem('app_theme', newTheme);
    document.documentElement.setAttribute('data-theme', newTheme);
    if (newTheme === 'light') {
      document.documentElement.classList.add('light');
    } else {
      document.documentElement.classList.remove('light');
    }
  };

  const handleDefaultLangChange = (lang: SupportedLanguage) => {
    setDefaultLang(lang);
    localStorage.setItem('app_default_language', lang);
  };

  useEffect(() => {
    Promise.allSettled([fetchHealth(), fetchModelSettings()])
      .then(([healthResult, modelResult]) => {
        if (healthResult.status === 'fulfilled') setHealth(healthResult.value);
        if (modelResult.status === 'fulfilled')  setModel(modelResult.value);
        if (healthResult.status === 'rejected' && modelResult.status === 'rejected') {
          setError('Cannot reach backend.');
        }
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6 max-w-4xl" data-testid="settings-page">
      <div className="border-b border-zinc-800 pb-4">
        <h2 className="text-xl font-bold text-zinc-100 flex items-center gap-2">
          <SettingsIcon className="w-5 h-5 text-emerald-400" />
          Settings &amp; Configuration
        </h2>
        <p className="text-sm text-zinc-400 mt-1">
          Review application parameters, resource limits, and customize user preferences.
        </p>
      </div>

      {error && (
        <div className="flex items-center gap-3 p-3 rounded-lg bg-rose-950/40 border border-rose-800/60 text-rose-300 text-sm" data-testid="settings-error">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-6">
        {/* User Preferences */}
        <div className="p-6 rounded-xl bg-zinc-900/70 border border-zinc-800 space-y-4" data-testid="settings-preferences">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-zinc-400 flex items-center gap-2">
            <Palette className="w-4 h-4 text-emerald-400" />
            User Preferences
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="p-4 rounded-lg bg-zinc-950 border border-zinc-800/80 space-y-2">
              <label htmlFor="settings-theme-select" className="text-sm font-medium text-zinc-200 flex items-center gap-1.5">
                <Palette className="w-3.5 h-3.5 text-zinc-400" />
                Editor &amp; UI Theme
              </label>
              <select
                id="settings-theme-select"
                data-testid="settings-theme-select"
                value={theme}
                onChange={(e) => handleThemeChange(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-zinc-900 border border-zinc-700 text-sm text-zinc-100 focus:outline-none focus:border-emerald-500/50"
              >
                <option value="vs-dark">Dark (VS Dark)</option>
                <option value="light">Light (VS Light)</option>
              </select>
              <p className="text-xs text-zinc-500">Persists in local storage across sessions.</p>
            </div>

            <div className="p-4 rounded-lg bg-zinc-950 border border-zinc-800/80 space-y-2">
              <label htmlFor="settings-default-lang-select" className="text-sm font-medium text-zinc-200 flex items-center gap-1.5">
                <Globe className="w-3.5 h-3.5 text-zinc-400" />
                Default Language
              </label>
              <select
                id="settings-default-lang-select"
                data-testid="settings-default-lang-select"
                value={defaultLang}
                onChange={(e) => handleDefaultLangChange(e.target.value as SupportedLanguage)}
                className="w-full px-3 py-2 rounded-lg bg-zinc-900 border border-zinc-700 text-sm text-zinc-100 focus:outline-none focus:border-emerald-500/50"
              >
                <option value="python">Python</option>
                <option value="java">Java</option>
                <option value="c">C</option>
                <option value="cpp">C++</option>
                <option value="javascript">JavaScript</option>
              </select>
              <p className="text-xs text-zinc-500">Initial language selected in the Code Debugger.</p>
            </div>
          </div>
        </div>

        {/* Backend Status */}
        <div className="p-6 rounded-xl bg-zinc-900/70 border border-zinc-800 space-y-4">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-zinc-400 flex items-center gap-2">
            <Server className="w-4 h-4 text-emerald-400" />
            Backend Service Status
          </h3>
          <div className="flex items-center justify-between p-4 rounded-lg bg-zinc-950 border border-zinc-800/80">
            <div>
              <div className="text-sm font-medium text-zinc-200">FastAPI Backend Endpoint</div>
              <div className="text-xs text-zinc-500 font-mono mt-0.5">http://localhost:8000/api/health</div>
            </div>
            {loading ? (
              <span className="text-xs text-zinc-400">Checking…</span>
            ) : health?.status === 'healthy' ? (
              <span className="inline-flex items-center gap-1.5 text-xs text-emerald-400 font-medium px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20"
                    data-testid="settings-health-ok">
                <CheckCircle className="w-3.5 h-3.5" />
                Operational
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 text-xs text-rose-400 font-medium px-2.5 py-1 rounded-full bg-rose-500/10 border border-rose-500/20"
                    data-testid="settings-health-fail">
                <AlertTriangle className="w-3.5 h-3.5" />
                Offline
              </span>
            )}
          </div>

          {/* API key status (no key shown) */}
          <div className="flex items-center justify-between p-4 rounded-lg bg-zinc-950 border border-zinc-800/80">
            <div>
              <div className="text-sm font-medium text-zinc-200 flex items-center gap-1.5">
                <Key className="w-3.5 h-3.5 text-zinc-400" />
                OpenRouter API Key
              </div>
              <div className="text-xs text-zinc-500 mt-0.5">
                Configured via OPENROUTER_API_KEY env variable (never exposed here)
              </div>
            </div>
            {model && (
              model.api_key_configured ? (
                <span className="inline-flex items-center gap-1.5 text-xs text-emerald-400 font-medium px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20"
                      data-testid="settings-apikey-ok">
                  <CheckCircle className="w-3.5 h-3.5" />
                  Configured
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 text-xs text-rose-400 font-medium px-2.5 py-1 rounded-full bg-rose-500/10 border border-rose-500/20"
                      data-testid="settings-apikey-missing">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  Not set
                </span>
              )
            )}
          </div>
        </div>

        {/* AI Model */}
        <div className="p-6 rounded-xl bg-zinc-900/70 border border-zinc-800 space-y-4">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-zinc-400 flex items-center gap-2">
            <Cpu className="w-4 h-4 text-emerald-400" />
            AI Reasoning Engine
          </h3>
          <div className="space-y-3">
            {[
              { label: 'Provider',          value: 'OpenRouter REST API' },
              { label: 'Configured Model',  value: model?.model ?? 'qwen/qwen-2.5-coder-32b-instruct', mono: true },
              { label: 'Request Timeout',   value: model ? `${model.timeout_seconds}s` : '60s' },
              { label: 'Max Output Tokens', value: model?.max_tokens?.toString() ?? '4096' },
              { label: 'Provider Routing',  value: model?.provider_order ?? 'default (automatic)' },
            ].map(({ label, value, mono }) => (
              <div key={label}
                   className="flex items-center justify-between py-2 border-b border-zinc-800/60 text-sm last:border-0">
                <span className="text-zinc-400">{label}</span>
                <span className={mono ? 'text-zinc-200 font-mono text-xs' : 'text-zinc-200'}>
                  {value}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Resource Limits */}
        <div className="p-6 rounded-xl bg-zinc-900/70 border border-zinc-800 space-y-4">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-zinc-400 flex items-center gap-2">
            <FileText className="w-4 h-4 text-emerald-400" />
            Fixed Resource Limits
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="p-4 rounded-lg bg-zinc-950 border border-zinc-800/80">
              <div className="text-xs text-zinc-500">Maximum Source Size</div>
              <div className="text-lg font-bold text-zinc-200 mt-1 font-mono">
                {model ? `${model.max_source_bytes.toLocaleString()} bytes` : '102,400 bytes'}
              </div>
              <div className="text-xs text-zinc-500 mt-0.5">100 KiB UTF-8 byte limit</div>
            </div>
            <div className="p-4 rounded-lg bg-zinc-950 border border-zinc-800/80">
              <div className="text-xs text-zinc-500">Maximum Source Lines</div>
              <div className="text-lg font-bold text-zinc-200 mt-1 font-mono">
                {model ? `${model.max_source_lines.toLocaleString()} lines` : '3,000 lines'}
              </div>
              <div className="text-xs text-zinc-500 mt-0.5">Enforced across all languages</div>
            </div>
          </div>
        </div>

        {/* Storage */}
        <div className="p-6 rounded-xl bg-zinc-900/70 border border-zinc-800 space-y-4">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-zinc-400 flex items-center gap-2">
            <Database className="w-4 h-4 text-emerald-400" />
            Storage Engine
          </h3>
          <div className="flex items-center justify-between text-sm py-2">
            <span className="text-zinc-400">Database Driver</span>
            <span className="text-zinc-200 font-mono">SQLite via SQLAlchemy ORM</span>
          </div>
          <p className="text-xs text-zinc-500 leading-relaxed">
            Debugging sessions, issue lists, fix proposals, and decisions are stored
            locally in <code className="font-mono text-zinc-400">debugger.db</code>.
            Source code is stored as-is; the database is local-only and never transmitted.
          </p>
        </div>
      </div>
    </div>
  );
};

import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Bug, History, Settings, Sparkles, Terminal } from 'lucide-react';

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Code Debugger', href: '/debugger', icon: Bug },
  { name: 'History', href: '/history', icon: History },
  { name: 'Settings', href: '/settings', icon: Settings },
];

export const Sidebar: React.FC = () => {
  return (
    <aside className="w-64 bg-zinc-900/90 border-r border-zinc-800 flex flex-col shrink-0 select-none">
      {/* Brand Header */}
      <div className="h-16 flex items-center px-5 border-b border-zinc-800 gap-3">
        <div className="w-9 h-9 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 shadow-sm shadow-emerald-950">
          <Terminal className="w-5 h-5" />
        </div>
        <div>
          <span className="font-semibold text-sm tracking-tight text-zinc-100 flex items-center gap-1.5">
            AI Code Debugger
          </span>
          <span className="text-[11px] block text-zinc-500 font-mono">Qwen2.5-Coder-32B</span>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {navigation.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.name}
              to={item.href}
              end={item.href === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                    : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/60'
                }`
              }
            >
              <Icon className="w-4 h-4" />
              <span>{item.name}</span>
            </NavLink>
          );
        })}
      </nav>

      {/* Engine Status / Info Footer */}
      <div className="p-4 m-3 rounded-xl bg-zinc-950/60 border border-zinc-800/80">
        <div className="flex items-center gap-2 text-xs font-medium text-emerald-400 mb-1.5">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Qwen2.5 Coder Engine</span>
        </div>
        <p className="text-[11px] text-zinc-500 leading-relaxed">
          OpenRouter AI reasoning engine configured for syntax, logic &amp; runtime analysis.
        </p>
      </div>
    </aside>
  );
};

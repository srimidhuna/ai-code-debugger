import React, { useState } from 'react';
import { Issue } from '../types';
import {
  AlertTriangle,
  AlertCircle,
  Info,
  CheckCircle,
  ChevronDown,
  ChevronRight,
  MapPin,
} from 'lucide-react';

const SEVERITY_CONFIG = {
  Critical: { icon: AlertCircle, className: 'severity-critical', label: 'Critical' },
  High:     { icon: AlertTriangle, className: 'severity-high',    label: 'High'     },
  Medium:   { icon: Info,         className: 'severity-medium',  label: 'Medium'   },
  Low:      { icon: CheckCircle,  className: 'severity-low',     label: 'Low'      },
};

const CATEGORY_CLASS: Record<string, string> = {
  Syntax:         'category-syntax',
  Logic:          'category-logic',
  Runtime:        'category-runtime',
  'Code Quality': 'category-quality',
};

interface IssueCardProps {
  issue: Issue;
  index: number;
}

const IssueCard: React.FC<IssueCardProps> = ({ issue, index }) => {
  const [expanded, setExpanded] = useState(false);
  const cfg = SEVERITY_CONFIG[issue.severity];
  const Icon = cfg.icon;

  const lineLabel =
    issue.line != null
      ? issue.line_end != null && issue.line_end !== issue.line
        ? `Lines ${issue.line}–${issue.line_end}`
        : `Line ${issue.line}`
      : null;

  return (
    <div
      className={`issue-card ${cfg.className}`}
      data-testid={`issue-card-${index}`}
    >
      <button
        className="issue-card-header"
        onClick={() => setExpanded((p) => !p)}
        aria-expanded={expanded}
        aria-controls={`issue-body-${index}`}
      >
        <div className="issue-card-title-row">
          <Icon size={15} className="issue-severity-icon" aria-hidden="true" />
          <span className="issue-title" data-testid={`issue-title-${index}`}>
            {issue.title}
          </span>
        </div>
        <div className="issue-card-meta">
          <span className={`category-badge ${CATEGORY_CLASS[issue.category] ?? ''}`}>
            {issue.category}
          </span>
          <span className={`severity-badge ${cfg.className}`}>{cfg.label}</span>
          {lineLabel && (
            <span className="line-badge" data-testid={`issue-line-${index}`}>
              <MapPin size={11} aria-hidden="true" />
              {lineLabel}
            </span>
          )}
          {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </div>
      </button>

      {expanded && (
        <div id={`issue-body-${index}`} className="issue-card-body">
          <div className="issue-section">
            <span className="issue-section-label">Explanation</span>
            <p className="issue-section-text">{issue.explanation}</p>
          </div>
          <div className="issue-section">
            <span className="issue-section-label">Suggestion</span>
            <p className="issue-section-text suggestion-text">{issue.suggestion}</p>
          </div>
        </div>
      )}
    </div>
  );
};

interface Props {
  issues: Issue[];
  remaining_concerns: string[];
}

export const IssuesPanel: React.FC<Props> = ({ issues, remaining_concerns }) => {
  const criticalCount = issues.filter((i) => i.severity === 'Critical').length;
  const highCount     = issues.filter((i) => i.severity === 'High').length;

  return (
    <div className="issues-panel" data-testid="issues-panel">
      <div className="issues-panel-header">
        <h3 className="issues-panel-title">
          Detected Issues
          <span className="issues-count-badge">{issues.length}</span>
        </h3>
        <div className="severity-summary">
          {criticalCount > 0 && (
            <span className="summary-pill severity-critical">{criticalCount} Critical</span>
          )}
          {highCount > 0 && (
            <span className="summary-pill severity-high">{highCount} High</span>
          )}
        </div>
      </div>

      {issues.length === 0 ? (
        <div className="issues-empty" data-testid="no-issues-message">
          <CheckCircle size={32} className="issues-empty-icon" />
          <p>No issues detected — the code looks clean.</p>
        </div>
      ) : (
        <div className="issues-list" data-testid="issues-list">
          {issues.map((issue, i) => (
            <IssueCard key={i} issue={issue} index={i} />
          ))}
        </div>
      )}

      {remaining_concerns.length > 0 && (
        <div className="remaining-concerns" data-testid="remaining-concerns">
          <h4 className="remaining-concerns-title">
            <Info size={14} aria-hidden="true" />
            Remaining Concerns
          </h4>
          <ul className="remaining-concerns-list">
            {remaining_concerns.map((c, i) => (
              <li key={i}>{c}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

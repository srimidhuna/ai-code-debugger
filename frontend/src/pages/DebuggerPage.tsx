import React, { useRef, useState, useCallback } from 'react';
import Editor from '@monaco-editor/react';
import {
  Bug,
  Loader2,
  Upload,
  Trash2,
  BookOpen,
  ChevronDown,
  AlertCircle,
  X,
  RotateCcw,
} from 'lucide-react';

import { LanguageSelector } from '../components/LanguageSelector';
import { IssuesPanel } from '../components/IssuesPanel';
import { DiffViewer } from '../components/DiffViewer';
import { debugCode, updateDecision } from '../services/api';
import { DebugResponse, SupportedLanguage, EXTENSION_TO_LANGUAGE } from '../types';
import { EXAMPLE_PROGRAMS, ExampleProgram } from '../data/examples';

// ── State machine ──────────────────────────────────────────────────────────
type PageState = 'idle' | 'analyzing' | 'analyzed' | 'error';

const ACCEPTED_EXTENSIONS = Object.keys(EXTENSION_TO_LANGUAGE);

export const DebuggerPage: React.FC = () => {
  const [language, setLanguage]         = useState<SupportedLanguage>(() => {
    return (localStorage.getItem('app_default_language') as SupportedLanguage) || 'python';
  });
  const [theme]                         = useState<string>(() => {
    return localStorage.getItem('app_theme') || 'vs-dark';
  });
  const [code, setCode]                 = useState('');
  const [pageState, setPageState]       = useState<PageState>('idle');
  const [errorMessage, setErrorMessage] = useState('');
  const [result, setResult]             = useState<DebugResponse | null>(null);
  const [showDiff, setShowDiff]         = useState(false);
  const [showExamples, setShowExamples] = useState(false);

  const fileInputRef    = useRef<HTMLInputElement>(null);
  const examplesMenuRef = useRef<HTMLDivElement>(null);

  // ── File upload ────────────────────────────────────────────────────────
  const handleFileUpload = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;

      const ext = '.' + file.name.split('.').pop()!.toLowerCase();
      const detectedLang = EXTENSION_TO_LANGUAGE[ext];

      if (!detectedLang) {
        setErrorMessage(
          `Unsupported file type "${ext}". Accepted: ${ACCEPTED_EXTENSIONS.join(', ')}`
        );
        setPageState('error');
        e.target.value = '';
        return;
      }

      const reader = new FileReader();
      reader.onload = (ev) => {
        const content = ev.target?.result as string;
        setLanguage(detectedLang);
        setCode(content);
        setPageState('idle');
        setResult(null);
        setShowDiff(false);
        setErrorMessage('');
      };
      reader.readAsText(file);
      e.target.value = '';
    },
    []
  );

  // ── Load example ──────────────────────────────────────────────────────
  const handleLoadExample = useCallback((example: ExampleProgram) => {
    setLanguage(example.language);
    setCode(example.code);
    setPageState('idle');
    setResult(null);
    setShowDiff(false);
    setErrorMessage('');
    setShowExamples(false);
  }, []);

  // ── Clear code ────────────────────────────────────────────────────────
  const handleClear = useCallback(() => {
    setCode('');
    setPageState('idle');
    setResult(null);
    setShowDiff(false);
    setErrorMessage('');
  }, []);

  // ── Analyze ───────────────────────────────────────────────────────────
  const handleAnalyze = useCallback(async () => {
    if (!code.trim() || pageState === 'analyzing') return;
    setPageState('analyzing');
    setErrorMessage('');
    setResult(null);
    setShowDiff(false);
    try {
      const response = await debugCode(code, language);
      setResult(response);
      setPageState('analyzed');
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'An unexpected error occurred.');
      setPageState('error');
    }
  }, [code, language, pageState]);

  // ── Apply fix ─────────────────────────────────────────────────────────
  const handleApply = useCallback(async () => {
    if (!result) return;
    const updated = await updateDecision(result.id, 'Accepted');
    setResult(updated);
    setCode(updated.fixed_code);
    // Hide the diff so the editor (now showing the fixed code) is front and center.
    setShowDiff(false);
  }, [result]);

  // ── Reject fix ────────────────────────────────────────────────────────
  const handleReject = useCallback(async () => {
    if (!result) return;
    const updated = await updateDecision(result.id, 'Rejected');
    setResult(updated);
  }, [result]);

  // ── Restore original ──────────────────────────────────────────────────
  const handleRestore = useCallback(() => {
    if (!result) return;
    setCode(result.original_code);
  }, [result]);

  // ── Start over / New analysis ──────────────────────────────────────────
  const handleStartOver = useCallback(() => {
    setResult(null);
    setShowDiff(false);
    setPageState('idle');
    setErrorMessage('');
  }, []);

  // ── Dismiss error ─────────────────────────────────────────────────────
  const dismissError = useCallback(() => {
    setPageState(result ? 'analyzed' : 'idle');
    setErrorMessage('');
  }, [result]);

  const isAnalyzing = pageState === 'analyzing';
  const isAnalyzed  = pageState === 'analyzed' && result !== null;
  const hasError    = pageState === 'error';

  return (
    <div className="debugger-page">
      {/* ── Top toolbar ───────────────────────────────────────────────── */}
      <div className="debugger-toolbar">
        <div className="toolbar-left">
          <LanguageSelector
            value={language}
            onChange={setLanguage}
            disabled={isAnalyzing}
          />

          {/* File upload */}
          <input
            ref={fileInputRef}
            type="file"
            id="file-upload-input"
            data-testid="file-upload-input"
            accept={ACCEPTED_EXTENSIONS.join(',')}
            onChange={handleFileUpload}
            className="hidden-file-input"
            aria-label="Upload source file"
          />
          <button
            id="upload-btn"
            data-testid="upload-btn"
            className="btn btn-ghost toolbar-btn"
            onClick={() => fileInputRef.current?.click()}
            disabled={isAnalyzing}
            title="Upload a source file"
          >
            <Upload size={14} />
            Upload File
          </button>

          {/* Load example */}
          <div className="examples-dropdown-container" ref={examplesMenuRef}>
            <button
              id="load-example-btn"
              data-testid="load-example-btn"
              className="btn btn-ghost toolbar-btn"
              onClick={() => setShowExamples((p) => !p)}
              disabled={isAnalyzing}
              aria-haspopup="listbox"
              aria-expanded={showExamples}
            >
              <BookOpen size={14} />
              Load Example
              <ChevronDown size={12} />
            </button>
            {showExamples && (
              <div
                className="examples-menu"
                role="listbox"
                aria-label="Example programs"
                data-testid="examples-menu"
              >
                {EXAMPLE_PROGRAMS.map((ex) => (
                  <button
                    key={ex.filename}
                    className="examples-menu-item"
                    role="option"
                    data-testid={`example-${ex.language}`}
                    onClick={() => handleLoadExample(ex)}
                  >
                    <span className="example-lang-pill">{ex.language.toUpperCase()}</span>
                    <span className="example-filename">{ex.filename}</span>
                    <span className="example-description">{ex.description}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Clear */}
          <button
            id="clear-btn"
            data-testid="clear-btn"
            className="btn btn-ghost toolbar-btn"
            onClick={handleClear}
            disabled={isAnalyzing}
            title="Clear the editor"
          >
            <Trash2 size={14} />
            Clear
          </button>
        </div>

        <div className="toolbar-right">
          {result && (
            <button
              id="start-over-btn"
              data-testid="start-over-btn"
              className="btn btn-ghost toolbar-btn"
              onClick={handleStartOver}
              disabled={isAnalyzing}
              title="Clear analysis results and start fresh"
            >
              <RotateCcw size={14} />
              New Analysis
            </button>
          )}

          <button
            id="analyze-btn"
            data-testid="analyze-btn"
            className="btn btn-primary analyze-btn"
            onClick={handleAnalyze}
            disabled={isAnalyzing || !code.trim()}
          >
            {isAnalyzing ? (
              <>
                <Loader2 size={15} className="spin" />
                Analyzing…
              </>
            ) : (
              <>
                <Bug size={15} />
                Analyze Code
              </>
            )}
          </button>
        </div>
      </div>

      {/* ── Error banner ──────────────────────────────────────────────── */}
      {hasError && errorMessage && (
        <div className="error-banner" data-testid="error-banner" role="alert">
          <AlertCircle size={16} aria-hidden="true" />
          <span className="error-banner-text">{errorMessage}</span>
          <button
            className="error-banner-close"
            onClick={dismissError}
            aria-label="Dismiss error"
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* ── Main workspace ────────────────────────────────────────────── */}
      <div className="debugger-workspace">
        {/* Monaco editor panel */}
        <div className="editor-panel">
          <div className="editor-panel-header">
            <span className="editor-panel-title">Source Code</span>
            {isAnalyzing && (
              <span className="editor-status analyzing" data-testid="analyzing-indicator">
                <Loader2 size={12} className="spin" aria-hidden="true" />
                Analyzing…
              </span>
            )}
            {isAnalyzed && !showDiff && (
              <button
                id="view-diff-btn"
                data-testid="view-diff-btn"
                className="btn btn-sm btn-outline"
                onClick={() => setShowDiff(true)}
              >
                View Fix →
              </button>
            )}
          </div>

          <div className="monaco-wrapper" data-testid="monaco-editor-wrapper">
            <Editor
              height="520px"
              language={language === 'cpp' ? 'cpp' : language}
              value={code}
              onChange={(val) => setCode(val ?? '')}
              theme={theme}
              onMount={(editor) => {
                // Force Monaco to measure its container after first paint.
                editor.layout();
              }}
              options={{
                minimap: { enabled: false },
                fontSize: 13,
                lineHeight: 20,
                scrollBeyondLastLine: false,
                wordWrap: 'on',
                readOnly: isAnalyzing,
                renderLineHighlight: 'all',
              }}
            />
          </div>

          {/* Empty state overlay */}
          {!code.trim() && !isAnalyzing && (
            <div className="editor-empty-state" data-testid="editor-empty-state">
              <Bug size={40} className="empty-state-icon" aria-hidden="true" />
              <p className="empty-state-heading">Paste, upload, or load an example</p>
              <p className="empty-state-sub">
                Supports Python, Java, C, C++, and JavaScript
              </p>
            </div>
          )}
        </div>

        {/* Results panel */}
        {isAnalyzed && result && (
          <div className="results-panel" data-testid="results-panel">
            {/* Summary */}
            <div className="summary-card" data-testid="summary-card">
              <h3 className="summary-title">Summary</h3>
              <p className="summary-text" data-testid="summary-text">
                {result.summary}
              </p>
              <div className="summary-meta">
                <span className="meta-chip">Model: {result.model_name}</span>
                <span
                  className={`decision-chip decision-${result.decision.toLowerCase()}`}
                  data-testid="decision-chip"
                >
                  {result.decision}
                </span>
              </div>
            </div>

            {/* Issues panel */}
            <IssuesPanel
              issues={result.issues}
              remaining_concerns={result.remaining_concerns}
            />

            {/* Diff viewer (shown when user clicks "View Fix →") */}
            {showDiff && (
              <DiffViewer
                originalCode={result.original_code}
                fixedCode={result.fixed_code}
                language={language}
                decision={result.decision}
                onApply={handleApply}
                onReject={handleReject}
                onRestore={handleRestore}
              />
            )}

            {/* Prompt to open diff viewer */}
            {!showDiff && (
              <div className="open-diff-prompt">
                <button
                  id="view-diff-prompt-btn"
                  data-testid="view-diff-prompt-btn"
                  className="btn btn-outline btn-full"
                  onClick={() => setShowDiff(true)}
                >
                  View & Apply Fix →
                </button>
              </div>
            )}
          </div>
        )}

        {/* Loading skeleton while analyzing */}
        {isAnalyzing && (
          <div className="results-panel skeleton-panel" data-testid="loading-skeleton">
            <div className="skeleton skeleton-title" />
            <div className="skeleton skeleton-line" />
            <div className="skeleton skeleton-line short" />
            <div className="skeleton skeleton-card" />
            <div className="skeleton skeleton-card tall" />
          </div>
        )}
      </div>
    </div>
  );
};

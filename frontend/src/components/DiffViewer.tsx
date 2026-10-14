import React, { useState } from 'react';
import { DiffEditor } from '@monaco-editor/react';
import { SupportedLanguage, LANGUAGE_TO_MONACO, LANGUAGE_EXTENSIONS } from '../types';
import {
  CheckCheck,
  XCircle,
  RotateCcw,
  Copy,
  Download,
  Loader2,
} from 'lucide-react';

interface Props {
  originalCode: string;
  fixedCode: string;
  language: SupportedLanguage;
  decision: 'Pending' | 'Accepted' | 'Rejected';
  onApply: () => Promise<void>;
  onReject: () => Promise<void>;
  onRestore: () => void;
}

export const DiffViewer: React.FC<Props> = ({
  originalCode,
  fixedCode,
  language,
  decision,
  onApply,
  onReject,
  onRestore,
}) => {
  const [applyBusy, setApplyBusy] = useState(false);
  const [rejectBusy, setRejectBusy] = useState(false);
  const [copyLabel, setCopyLabel] = useState<'Copy' | 'Copied!'>('Copy');

  const monacoLang = LANGUAGE_TO_MONACO[language];
  const isSettled = decision === 'Accepted' || decision === 'Rejected';

  async function handleApply() {
    if (applyBusy || isSettled) return;
    setApplyBusy(true);
    try { await onApply(); }
    finally { setApplyBusy(false); }
  }

  async function handleReject() {
    if (rejectBusy || isSettled) return;
    setRejectBusy(true);
    try { await onReject(); }
    finally { setRejectBusy(false); }
  }

  function handleCopy() {
    navigator.clipboard.writeText(fixedCode).then(() => {
      setCopyLabel('Copied!');
      setTimeout(() => setCopyLabel('Copy'), 2000);
    });
  }

  function handleDownload() {
    const ext = LANGUAGE_EXTENSIONS[language];
    const blob = new Blob([fixedCode], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `fixed_code${ext}`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="diff-viewer" data-testid="diff-viewer">
      <div className="diff-viewer-header">
        <h3 className="diff-viewer-title">Code Comparison</h3>
        <div className="diff-column-labels">
          <span className="diff-label diff-label-original">Original</span>
          <span className="diff-label diff-label-fixed">Fixed</span>
        </div>
      </div>

      <div className="diff-editor-wrapper">
        <DiffEditor
          original={originalCode}
          modified={fixedCode}
          language={monacoLang}
          theme="vs-dark"
          options={{
            readOnly: true,
            renderSideBySide: true,
            minimap: { enabled: false },
            fontSize: 13,
            lineHeight: 20,
            scrollBeyondLastLine: false,
            wordWrap: 'on',
            diffWordWrap: 'on',
            renderOverviewRuler: false,
          }}
          height="420px"
        />
      </div>

      {decision === 'Accepted' && (
        <div className="decision-banner decision-accepted" data-testid="decision-accepted-banner">
          <CheckCheck size={16} /> Fix applied and accepted.
        </div>
      )}
      {decision === 'Rejected' && (
        <div className="decision-banner decision-rejected" data-testid="decision-rejected-banner">
          <XCircle size={16} /> Fix rejected. Original code preserved.
        </div>
      )}

      <div className="diff-actions">
        {/* Apply and Reject: only active when Pending */}
        <button
          id="apply-fix-btn"
          data-testid="apply-fix-btn"
          className={`btn btn-apply ${isSettled ? 'btn-disabled' : ''}`}
          onClick={handleApply}
          disabled={isSettled || applyBusy}
          title={isSettled ? 'Decision already recorded' : 'Apply and accept the corrected code'}
        >
          {applyBusy
            ? <><Loader2 size={14} className="spin" /> Applying…</>
            : <><CheckCheck size={14} /> Apply Fix</>}
        </button>

        <button
          id="reject-fix-btn"
          data-testid="reject-fix-btn"
          className={`btn btn-reject ${isSettled ? 'btn-disabled' : ''}`}
          onClick={handleReject}
          disabled={isSettled || rejectBusy}
          title={isSettled ? 'Decision already recorded' : 'Reject and keep the original code'}
        >
          {rejectBusy
            ? <><Loader2 size={14} className="spin" /> Rejecting…</>
            : <><XCircle size={14} /> Reject Fix</>}
        </button>

        <div className="diff-actions-right">
          <button
            id="restore-original-btn"
            data-testid="restore-original-btn"
            className="btn btn-ghost"
            onClick={onRestore}
            title="Restore original code to the editor"
          >
            <RotateCcw size={14} /> Restore Original
          </button>

          <button
            id="copy-corrected-btn"
            data-testid="copy-corrected-btn"
            className="btn btn-ghost"
            onClick={handleCopy}
          >
            <Copy size={14} /> {copyLabel}
          </button>

          <button
            id="download-corrected-btn"
            data-testid="download-corrected-btn"
            className="btn btn-ghost"
            onClick={handleDownload}
            title={`Download corrected file as fixed_code${LANGUAGE_EXTENSIONS[language]}`}
          >
            <Download size={14} /> Download
          </button>
        </div>
      </div>
    </div>
  );
};

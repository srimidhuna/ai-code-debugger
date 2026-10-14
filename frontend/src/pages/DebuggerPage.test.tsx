import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { DebuggerPage } from '../pages/DebuggerPage';
import { IssuesPanel } from '../components/IssuesPanel';
import { DiffViewer } from '../components/DiffViewer';
import * as api from '../services/api';
import { DebugResponse, Issue } from '../types';
import { EXAMPLE_PROGRAMS } from '../data/examples';

// ── Monaco Mock ─────────────────────────────────────────────────────────────
vi.mock('@monaco-editor/react', () => ({
  default: ({
    value,
    onChange,
    onMount,
  }: {
    value?: string;
    onChange?: (val: string) => void;
    onMount?: (e: unknown) => void;
  }) => {
    const fakeEditor = { layout: vi.fn() };
    if (onMount) onMount(fakeEditor);
    return (
      <textarea
        data-testid="mock-monaco-editor"
        value={value ?? ''}
        onChange={(e) => onChange?.(e.target.value)}
      />
    );
  },
  DiffEditor: ({ original, modified }: { original: string; modified: string }) => (
    <div data-testid="mock-diff-editor">
      <div data-testid="mock-diff-original">{original}</div>
      <div data-testid="mock-diff-modified">{modified}</div>
    </div>
  ),
}));

// ── Test Data ───────────────────────────────────────────────────────────────
const sampleIssues: Issue[] = [
  {
    line: 17,
    line_end: 17,
    category: 'Logic',
    severity: 'High',
    title: 'max_val initialised to 0',
    explanation: 'Initialising max_val to 0 fails when all numbers are negative.',
    suggestion: 'max_val = numbers[0]',
  },
];

const mockDebugResponse: DebugResponse = {
  id: 'test-session-123',
  timestamp: new Date().toISOString(),
  model_name: 'qwen/qwen-2.5-coder-32b-instruct',
  language: 'python',
  original_code: 'def find_max(numbers):\n    max_val = 0\n    return max_val\n',
  fixed_code: 'def find_max(numbers):\n    if not numbers: return None\n    max_val = numbers[0]\n    return max_val\n',
  summary: 'Fixed initialisation bug for negative numbers.',
  issues: sampleIssues,
  changes: [],
  remaining_concerns: ['Consider empty list input.'],
  decision: 'Pending',
};

const acceptedResult: DebugResponse = {
  ...mockDebugResponse,
  decision: 'Accepted',
};

const rejectedResult: DebugResponse = {
  ...mockDebugResponse,
  decision: 'Rejected',
};

function renderPage() {
  return render(
    <MemoryRouter>
      <DebuggerPage />
    </MemoryRouter>
  );
}

// ── Tests ───────────────────────────────────────────────────────────────────
describe('Phase 3 — DebuggerPage & Components Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('uses default language from localStorage if configured', () => {
    localStorage.setItem('app_default_language', 'javascript');
    renderPage();
    const select = screen.getByTestId('language-select') as HTMLSelectElement;
    expect(select.value).toBe('javascript');
  });

  it('renders editor, toolbar controls, language selector, and empty state', () => {
    renderPage();

    expect(screen.getByText('Source Code')).toBeInTheDocument();
    expect(screen.getByTestId('language-select')).toBeInTheDocument();
    expect(screen.getByTestId('upload-btn')).toBeInTheDocument();
    expect(screen.getByTestId('load-example-btn')).toBeInTheDocument();
    expect(screen.getByTestId('clear-btn')).toBeInTheDocument();
    expect(screen.getByTestId('analyze-btn')).toBeInTheDocument();
    expect(screen.getByText('Paste, upload, or load an example')).toBeInTheDocument();
  });

  it('allows language selection', () => {
    renderPage();
    const select = screen.getByTestId('language-select') as HTMLSelectElement;
    expect(select.value).toBe('python');

    fireEvent.change(select, { target: { value: 'java' } });
    expect(select.value).toBe('java');
  });

  it('populates editor when an example is loaded for each of the 5 supported languages', () => {
    renderPage();

    const loadExampleBtn = screen.getByTestId('load-example-btn');
    fireEvent.click(loadExampleBtn);

    expect(screen.getByTestId('examples-menu')).toBeInTheDocument();

    const languages = ['python', 'java', 'c', 'cpp', 'javascript'] as const;
    languages.forEach((lang) => {
      expect(screen.getByTestId(`example-${lang}`)).toBeInTheDocument();
    });

    // Click python example
    fireEvent.click(screen.getByTestId('example-python'));
    const editor = screen.getByTestId('mock-monaco-editor') as HTMLTextAreaElement;
    expect(editor.value).toContain('def find_max(numbers):');

    // Language dropdown automatically matches example language
    const select = screen.getByTestId('language-select') as HTMLSelectElement;
    expect(select.value).toBe('python');
  });

  it('verifies all 5 required sample programs exist in data with intentional bugs', () => {
    const langSet = new Set(EXAMPLE_PROGRAMS.map((e) => e.language));
    expect(langSet.has('python')).toBe(true);
    expect(langSet.has('java')).toBe(true);
    expect(langSet.has('c')).toBe(true);
    expect(langSet.has('cpp')).toBe(true);
    expect(langSet.has('javascript')).toBe(true);
    expect(EXAMPLE_PROGRAMS.length).toBeGreaterThanOrEqual(5);
  });

  it('validates file upload extensions and rejects invalid files with error banner', async () => {
    renderPage();
    const fileInput = screen.getByTestId('file-upload-input');

    // Upload unsupported file (.txt)
    const badFile = new File(['hello world'], 'notes.txt', { type: 'text/plain' });
    fireEvent.change(fileInput, { target: { files: [badFile] } });

    expect(await screen.findByTestId('error-banner')).toBeInTheDocument();
    expect(screen.getByText(/Unsupported file type "\.txt"/)).toBeInTheDocument();
  });

  it('handles successful code analysis and displays summary, issues, and diff prompt', async () => {
    vi.spyOn(api, 'debugCode').mockResolvedValueOnce(mockDebugResponse);

    renderPage();
    const editor = screen.getByTestId('mock-monaco-editor');
    fireEvent.change(editor, { target: { value: 'def find_max(numbers):\n    max_val = 0\n    return max_val' } });

    const analyzeBtn = screen.getByTestId('analyze-btn');
    fireEvent.click(analyzeBtn);

    await waitFor(() => {
      expect(screen.getByTestId('results-panel')).toBeInTheDocument();
    });

    expect(screen.getByTestId('summary-text')).toHaveTextContent('Fixed initialisation bug for negative numbers.');
    expect(screen.getByText('max_val initialised to 0')).toBeInTheDocument();
    expect(screen.getByTestId('view-diff-prompt-btn')).toBeInTheDocument();
  });

  it('displays recoverable error banner when API call fails', async () => {
    vi.spyOn(api, 'debugCode').mockRejectedValueOnce(new Error('OpenRouter API rate limit exceeded'));

    renderPage();
    const editor = screen.getByTestId('mock-monaco-editor');
    fireEvent.change(editor, { target: { value: 'some code' } });

    fireEvent.click(screen.getByTestId('analyze-btn'));

    expect(await screen.findByTestId('error-banner')).toBeInTheDocument();
    expect(screen.getByText('OpenRouter API rate limit exceeded')).toBeInTheDocument();
  });

  it('renders IssuesPanel with severity badges, category, line numbers, and remaining concerns', () => {
    render(
      <IssuesPanel
        issues={sampleIssues}
        remaining_concerns={['Check memory limits.']}
      />
    );

    expect(screen.getByText('Detected Issues')).toBeInTheDocument();
    expect(screen.getByText('max_val initialised to 0')).toBeInTheDocument();
    expect(screen.getByText('Logic')).toBeInTheDocument();
    expect(screen.getByText('High')).toBeInTheDocument();
    expect(screen.getByText('Line 17')).toBeInTheDocument();
    expect(screen.getByText('Remaining Concerns')).toBeInTheDocument();
    expect(screen.getByText('Check memory limits.')).toBeInTheDocument();

    // Expand issue card
    fireEvent.click(screen.getByTestId('issue-title-0'));
    expect(screen.getByText('Initialising max_val to 0 fails when all numbers are negative.')).toBeInTheDocument();
    expect(screen.getByText('max_val = numbers[0]')).toBeInTheDocument();
  });

  it('renders DiffViewer and allows Apply Fix requiring explicit user action, persisting decision', async () => {
    const onApply = vi.fn().mockResolvedValue(undefined);
    const onReject = vi.fn().mockResolvedValue(undefined);
    const onRestore = vi.fn();

    render(
      <DiffViewer
        originalCode="original"
        fixedCode="fixed"
        language="python"
        decision="Pending"
        onApply={onApply}
        onReject={onReject}
        onRestore={onRestore}
      />
    );

    expect(screen.getByTestId('mock-diff-original')).toHaveTextContent('original');
    expect(screen.getByTestId('mock-diff-modified')).toHaveTextContent('fixed');

    const applyBtn = screen.getByTestId('apply-fix-btn');
    const rejectBtn = screen.getByTestId('reject-fix-btn');
    expect(applyBtn).not.toBeDisabled();
    expect(rejectBtn).not.toBeDisabled();

    await act(async () => {
      fireEvent.click(applyBtn);
    });
    expect(onApply).toHaveBeenCalledTimes(1);
  });

  it('DiffViewer rejects fix and preserves original code', async () => {
    const onApply = vi.fn().mockResolvedValue(undefined);
    const onReject = vi.fn().mockResolvedValue(undefined);
    const onRestore = vi.fn();

    render(
      <DiffViewer
        originalCode="original code content"
        fixedCode="fixed code content"
        language="python"
        decision="Pending"
        onApply={onApply}
        onReject={onReject}
        onRestore={onRestore}
      />
    );

    const rejectBtn = screen.getByTestId('reject-fix-btn');
    await act(async () => {
      fireEvent.click(rejectBtn);
    });
    expect(onReject).toHaveBeenCalledTimes(1);

    const restoreBtn = screen.getByTestId('restore-original-btn');
    fireEvent.click(restoreBtn);
    expect(onRestore).toHaveBeenCalledTimes(1);
  });

  it('DiffViewer disables Apply and Reject once decision is Accepted or Rejected', () => {
    const { rerender } = render(
      <DiffViewer
        originalCode="original"
        fixedCode="fixed"
        language="python"
        decision="Accepted"
        onApply={vi.fn()}
        onReject={vi.fn()}
        onRestore={vi.fn()}
      />
    );

    expect(screen.getByTestId('apply-fix-btn')).toBeDisabled();
    expect(screen.getByTestId('reject-fix-btn')).toBeDisabled();
    expect(screen.getByTestId('decision-accepted-banner')).toHaveTextContent('Fix applied and accepted.');

    rerender(
      <DiffViewer
        originalCode="original"
        fixedCode="fixed"
        language="python"
        decision="Rejected"
        onApply={vi.fn()}
        onReject={vi.fn()}
        onRestore={vi.fn()}
      />
    );

    expect(screen.getByTestId('apply-fix-btn')).toBeDisabled();
    expect(screen.getByTestId('reject-fix-btn')).toBeDisabled();
    expect(screen.getByTestId('decision-rejected-banner')).toHaveTextContent('Fix rejected. Original code preserved.');
  });
});

describe('DebuggerPage - layout & scroll regression', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(api, 'debugCode').mockResolvedValue(mockDebugResponse);
    vi.spyOn(api, 'updateDecision').mockImplementation((_id, decision) =>
      Promise.resolve(decision === 'Accepted' ? acceptedResult : rejectedResult)
    );
  });

  it('monaco wrapper is not overflow-hidden on initial render', () => {
    renderPage();
    const style = window.getComputedStyle(
      screen.getByTestId('monaco-editor-wrapper')
    );
    expect(style.overflow).not.toBe('hidden');
  });

  it('Apply Fix: diff unmounts and editor receives fixed code', async () => {
    renderPage();
    const editor = screen.getByTestId('mock-monaco-editor');
    fireEvent.change(editor, { target: { value: mockDebugResponse.original_code } });
    fireEvent.click(screen.getByTestId('analyze-btn'));
    await waitFor(() => screen.getByTestId('results-panel'));

    fireEvent.click(screen.getByTestId('view-diff-prompt-btn'));
    await waitFor(() => screen.getByTestId('diff-viewer'));

    await act(async () => {
      fireEvent.click(screen.getByTestId('apply-fix-btn'));
    });

    await waitFor(() =>
      expect(screen.queryByTestId('diff-viewer')).not.toBeInTheDocument()
    );

    expect(
      (screen.getByTestId('mock-monaco-editor') as HTMLTextAreaElement).value
    ).toBe(mockDebugResponse.fixed_code);
  });

  it('Reject Fix: editor keeps original code', async () => {
    renderPage();
    const editor = screen.getByTestId('mock-monaco-editor');
    fireEvent.change(editor, { target: { value: mockDebugResponse.original_code } });
    fireEvent.click(screen.getByTestId('analyze-btn'));
    await waitFor(() => screen.getByTestId('results-panel'));

    fireEvent.click(screen.getByTestId('view-diff-prompt-btn'));
    await waitFor(() => screen.getByTestId('diff-viewer'));

    await act(async () => {
      fireEvent.click(screen.getByTestId('reject-fix-btn'));
    });

    expect(
      (screen.getByTestId('mock-monaco-editor') as HTMLTextAreaElement).value
    ).toBe(mockDebugResponse.original_code);
  });

  it('Restore Original puts original code back after Apply', async () => {
    renderPage();
    const editor = screen.getByTestId('mock-monaco-editor');
    fireEvent.change(editor, { target: { value: mockDebugResponse.original_code } });
    fireEvent.click(screen.getByTestId('analyze-btn'));
    await waitFor(() => screen.getByTestId('results-panel'));

    fireEvent.click(screen.getByTestId('view-diff-prompt-btn'));
    await waitFor(() => screen.getByTestId('diff-viewer'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('apply-fix-btn'));
    });
    await waitFor(() =>
      expect(screen.queryByTestId('diff-viewer')).not.toBeInTheDocument()
    );

    // Re-open diff to access Restore button
    fireEvent.click(screen.getByTestId('view-diff-btn'));
    await waitFor(() => screen.getByTestId('diff-viewer'));

    fireEvent.click(screen.getByTestId('restore-original-btn'));

    expect(
      (screen.getByTestId('mock-monaco-editor') as HTMLTextAreaElement).value
    ).toBe(mockDebugResponse.original_code);
  });

  it('editor wrapper is not overflow-hidden after Apply Fix', async () => {
    renderPage();
    const editor = screen.getByTestId('mock-monaco-editor');
    fireEvent.change(editor, { target: { value: mockDebugResponse.original_code } });
    fireEvent.click(screen.getByTestId('analyze-btn'));
    await waitFor(() => screen.getByTestId('results-panel'));

    fireEvent.click(screen.getByTestId('view-diff-prompt-btn'));
    await waitFor(() => screen.getByTestId('diff-viewer'));
    await act(async () => {
      fireEvent.click(screen.getByTestId('apply-fix-btn'));
    });
    await waitFor(() =>
      expect(screen.queryByTestId('diff-viewer')).not.toBeInTheDocument()
    );

    const style = window.getComputedStyle(
      screen.getByTestId('monaco-editor-wrapper')
    );
    expect(style.overflow).not.toBe('hidden');
  });

  it('allows user to run Analyze Code again after Accept', async () => {
    const debugCodeSpy = vi.spyOn(api, 'debugCode').mockResolvedValue(mockDebugResponse);
    renderPage();
    const editor = screen.getByTestId('mock-monaco-editor');
    fireEvent.change(editor, { target: { value: mockDebugResponse.original_code } });
    fireEvent.click(screen.getByTestId('analyze-btn'));
    await waitFor(() => screen.getByTestId('results-panel'));

    fireEvent.click(screen.getByTestId('view-diff-prompt-btn'));
    await waitFor(() => screen.getByTestId('diff-viewer'));

    await act(async () => {
      fireEvent.click(screen.getByTestId('apply-fix-btn'));
    });

    const analyzeBtn = screen.getByTestId('analyze-btn');
    expect(analyzeBtn).not.toBeDisabled();

    // Trigger analysis again
    const secondResponse: DebugResponse = {
      ...mockDebugResponse,
      id: 'second-session-456',
      summary: 'Second pass analysis.',
    };
    debugCodeSpy.mockResolvedValueOnce(secondResponse);

    await act(async () => {
      fireEvent.click(analyzeBtn);
    });

    await waitFor(() => {
      expect(screen.getByTestId('summary-text')).toHaveTextContent('Second pass analysis.');
    });
  });

  it('allows user to run Analyze Code again after Reject', async () => {
    const debugCodeSpy = vi.spyOn(api, 'debugCode').mockResolvedValue(mockDebugResponse);
    renderPage();
    const editor = screen.getByTestId('mock-monaco-editor');
    fireEvent.change(editor, { target: { value: mockDebugResponse.original_code } });
    fireEvent.click(screen.getByTestId('analyze-btn'));
    await waitFor(() => screen.getByTestId('results-panel'));

    fireEvent.click(screen.getByTestId('view-diff-prompt-btn'));
    await waitFor(() => screen.getByTestId('diff-viewer'));

    await act(async () => {
      fireEvent.click(screen.getByTestId('reject-fix-btn'));
    });

    const analyzeBtn = screen.getByTestId('analyze-btn');
    expect(analyzeBtn).not.toBeDisabled();

    const secondResponse: DebugResponse = {
      ...mockDebugResponse,
      id: 'rejected-reanalyze-789',
      summary: 'Re-analyzed after rejection.',
    };
    debugCodeSpy.mockResolvedValueOnce(secondResponse);

    await act(async () => {
      fireEvent.click(analyzeBtn);
    });

    await waitFor(() => {
      expect(screen.getByTestId('summary-text')).toHaveTextContent('Re-analyzed after rejection.');
    });
  });

  it('provides New Analysis action that resets session and results', async () => {
    renderPage();
    const editor = screen.getByTestId('mock-monaco-editor');
    fireEvent.change(editor, { target: { value: mockDebugResponse.original_code } });
    fireEvent.click(screen.getByTestId('analyze-btn'));
    await waitFor(() => screen.getByTestId('results-panel'));

    const startOverBtn = screen.getByTestId('start-over-btn');
    expect(startOverBtn).toBeInTheDocument();

    fireEvent.click(startOverBtn);
    expect(screen.queryByTestId('results-panel')).not.toBeInTheDocument();
  });
});

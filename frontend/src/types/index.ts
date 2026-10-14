export interface HealthStatus {
  status: string;
  timestamp: string;
  version: string;
  service: string;
}

export type SupportedLanguage = 'python' | 'java' | 'c' | 'cpp' | 'javascript';

export interface Issue {
  title: string;
  severity: 'Critical' | 'High' | 'Medium' | 'Low';
  category: 'Syntax' | 'Logic' | 'Runtime' | 'Code Quality';
  line?: number | null;
  line_end?: number | null;
  explanation: string;
  suggestion: string;
}

export interface CodeChange {
  description: string;
  reason: string;
}

export interface DebugResponse {
  id: string;
  timestamp: string;
  language: string;
  original_code: string;
  fixed_code: string;
  summary: string;
  issues: Issue[];
  changes: CodeChange[];
  remaining_concerns: string[];
  decision: 'Pending' | 'Accepted' | 'Rejected';
  model_name: string;
}

// Language metadata helpers
export const LANGUAGE_LABELS: Record<SupportedLanguage, string> = {
  python: 'Python',
  java: 'Java',
  c: 'C',
  cpp: 'C++',
  javascript: 'JavaScript',
};

export const LANGUAGE_EXTENSIONS: Record<SupportedLanguage, string> = {
  python: '.py',
  java: '.java',
  c: '.c',
  cpp: '.cpp',
  javascript: '.js',
};

/** Map upload file extensions to supported language identifiers */
export const EXTENSION_TO_LANGUAGE: Record<string, SupportedLanguage> = {
  '.py': 'python',
  '.java': 'java',
  '.c': 'c',
  '.cpp': 'cpp',
  '.h': 'cpp',
  '.hpp': 'cpp',
  '.js': 'javascript',
};

/** Monaco editor language identifiers */
export const LANGUAGE_TO_MONACO: Record<SupportedLanguage, string> = {
  python: 'python',
  java: 'java',
  c: 'c',
  cpp: 'cpp',
  javascript: 'javascript',
};

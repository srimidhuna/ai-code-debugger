import React from 'react';
import { SupportedLanguage, LANGUAGE_LABELS } from '../types';
import { ChevronDown } from 'lucide-react';

const LANGUAGES: SupportedLanguage[] = ['python', 'java', 'c', 'cpp', 'javascript'];

interface Props {
  value: SupportedLanguage;
  onChange: (lang: SupportedLanguage) => void;
  disabled?: boolean;
}

export const LanguageSelector: React.FC<Props> = ({ value, onChange, disabled = false }) => {
  return (
    <div className="language-selector-wrapper">
      <label htmlFor="language-select" className="language-label">
        Language
      </label>
      <div className="language-select-container">
        <select
          id="language-select"
          data-testid="language-select"
          className="language-select"
          value={value}
          onChange={(e) => onChange(e.target.value as SupportedLanguage)}
          disabled={disabled}
        >
          {LANGUAGES.map((lang) => (
            <option key={lang} value={lang}>
              {LANGUAGE_LABELS[lang]}
            </option>
          ))}
        </select>
        <ChevronDown size={16} className="language-select-chevron" />
      </div>
    </div>
  );
};

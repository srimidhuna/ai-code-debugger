import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

// Initialize theme from localStorage before render
const savedTheme = localStorage.getItem('app_theme') || 'vs-dark';
if (savedTheme === 'light') {
  document.documentElement.classList.add('light');
  document.documentElement.setAttribute('data-theme', 'light');
} else {
  document.documentElement.classList.remove('light');
  document.documentElement.setAttribute('data-theme', 'vs-dark');
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

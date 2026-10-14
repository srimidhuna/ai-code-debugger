# AI Code Debugger

Full-stack AI-powered code debugging and automatic fix generation web application built with FastAPI, React, TypeScript, and OpenRouter.

## Configuration & Environment Variables

Create a `.env` file in the project root:

```ini
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_MODEL=qwen/qwen-2.5-coder-32b-instruct
OPENROUTER_TIMEOUT=60
MAX_SOURCE_BYTES=102400
MAX_SOURCE_LINES=3000
DATABASE_URL=sqlite:///./debugger.db
FRONTEND_ORIGIN=http://localhost:5173

# Provider routing order for OpenRouter (e.g. Cloudflare). Leave empty for default.
OPENROUTER_PROVIDER_ORDER=Cloudflare

# Set to true to log raw AI responses for debugging (never logs API keys)
DEBUG_AI_RESPONSES=false
```

### Provider Routing & Endpoint Information
- The configured model identifier is `qwen/qwen-2.5-coder-32b-instruct`.
- On OpenRouter, the active endpoint serving this model is **Cloudflare**.
- You can pin or order providers using `OPENROUTER_PROVIDER_ORDER=Cloudflare`. When specified, fallbacks outside the list are disabled.

## Running Locally

### Backend
```powershell
cd backend
.\venv\Scripts\uvicorn app.main:app --reload --port 8000
```

### Frontend
```powershell
cd frontend
npm run dev
```

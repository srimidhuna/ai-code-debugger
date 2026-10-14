from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.health import router as health_router
from app.api.debug import router as debug_router
from app.api.history import router as history_router
from app.api.settings_api import router as settings_router
from app.api.dashboard import router as dashboard_router
from app.core.config import settings
from app.core.exceptions import DebuggerException
from app.database import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on startup
    init_db()
    yield

app = FastAPI(
    title="AI Code Debugger API",
    description="Backend service for AI Code Debugger application",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Handle custom DebuggerException
@app.exception_handler(DebuggerException)
async def debugger_exception_handler(request: Request, exc: DebuggerException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )

# Global fallback error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred.", "error": str(exc)},
    )

# Register Routers
app.include_router(health_router)
app.include_router(debug_router)
app.include_router(history_router)
app.include_router(settings_router)
app.include_router(dashboard_router)

@app.get("/")
def root():
    return {
        "name": "AI Code Debugger API",
        "version": "1.0.0",
        "status": "operational",
        "model": settings.OPENROUTER_MODEL,
        "docs_url": "/docs",
    }

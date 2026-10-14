from fastapi import APIRouter
from app.core.config import settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/model")
def get_model_settings() -> dict:
    """Return safe model configuration information without exposing credentials."""
    api_key_configured = bool(settings.OPENROUTER_API_KEY and settings.OPENROUTER_API_KEY.strip())
    return {
        "model": settings.OPENROUTER_MODEL,
        "timeout_seconds": settings.OPENROUTER_TIMEOUT,
        "max_tokens": settings.OPENROUTER_MAX_TOKENS,
        "api_key_configured": api_key_configured,
        "provider_order": settings.OPENROUTER_PROVIDER_ORDER or None,
        "max_source_bytes": settings.MAX_SOURCE_BYTES,
        "max_source_lines": settings.MAX_SOURCE_LINES,
    }

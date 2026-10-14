import logging
import os

# Configure a module-level logger for AI responses (never logs API keys)
_ai_logger = logging.getLogger("app.ai_responses")

def _is_ai_debug_enabled() -> bool:
    return os.environ.get("DEBUG_AI_RESPONSES", "").lower() in ("1", "true", "yes")

def log_raw_ai_response(stage: str, content: str) -> None:
    """Log raw AI response content when DEBUG_AI_RESPONSES=true.
    Safe: never logs the API key or Authorization headers.
    """
    if _is_ai_debug_enabled():
        _ai_logger.debug(
            "[AI DEBUG] Stage=%s | Length=%d chars\n---BEGIN RAW---\n%s\n---END RAW---",
            stage,
            len(content),
            content,
        )

def log_ai_parse_error(stage: str, error: str, raw_content: str) -> None:
    """Log AI parse/validation error when DEBUG_AI_RESPONSES=true."""
    if _is_ai_debug_enabled():
        _ai_logger.debug(
            "[AI DEBUG] Parse error at stage=%s | Error: %s\n---BEGIN RAW---\n%s\n---END RAW---",
            stage,
            error,
            raw_content,
        )

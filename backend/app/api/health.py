from datetime import datetime, timezone
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["health"])

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    service: str

@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """Check health and status of the backend API."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version="1.0.0",
        service="ai-code-debugger-backend"
    )

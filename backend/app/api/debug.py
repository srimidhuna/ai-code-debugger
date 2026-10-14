from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.debug import DebugRequest, SessionResponse
from app.services.debugging_service import DebuggingService
from app.core.exceptions import DebuggerException

router = APIRouter(prefix="/api", tags=["debug"])

@router.post("/debug", response_model=SessionResponse, status_code=status.HTTP_200_OK)
async def analyze_code(
    request: DebugRequest,
    db: Session = Depends(get_db),
) -> SessionResponse:
    """Analyze buggy source code, generate automated fixes, and create a pending debugging session."""
    service = DebuggingService()
    try:
        session_record = await service.analyze_code(request, db)
        return SessionResponse.model_validate(session_record)
    except DebuggerException as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during code analysis: {str(exc)}",
        )

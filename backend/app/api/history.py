from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.session import SessionModel
from app.schemas.debug import DecisionUpdateRequest, SessionResponse, SessionListResponse

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("", response_model=SessionListResponse)
def list_sessions(
    q: Optional[str] = Query(None, description="Search in summary (case-insensitive)"),
    language: Optional[str] = Query(None, description="Filter by language"),
    decision: Optional[str] = Query(None, description="Filter by decision"),
    sort: str = Query("desc", description="Date sort: 'asc' or 'desc'"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
) -> SessionListResponse:
    """List debugging sessions with optional search, filter, and pagination."""
    query = db.query(SessionModel)
    if q:
        query = query.filter(SessionModel.summary.ilike(f"%{q}%"))
    if language:
        query = query.filter(SessionModel.language == language.lower())
    if decision:
        query = query.filter(SessionModel.decision == decision)
    total = query.count()
    if sort == "asc":
        query = query.order_by(SessionModel.timestamp.asc())
    else:
        query = query.order_by(SessionModel.timestamp.desc())
    offset = (page - 1) * page_size
    sessions = query.offset(offset).limit(page_size).all()
    return SessionListResponse(
        total=total,
        page=page,
        page_size=page_size,
        sessions=[SessionResponse.model_validate(s) for s in sessions],
    )


@router.get("/{session_id}", response_model=SessionResponse)
def get_session(session_id: str, db: Session = Depends(get_db)) -> SessionResponse:
    """Retrieve an existing debugging session by ID."""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Debugging session '{session_id}' not found.",
        )
    return SessionResponse.model_validate(session)


@router.patch("/{session_id}", response_model=SessionResponse)
def update_session_decision(
    session_id: str,
    update: DecisionUpdateRequest,
    db: Session = Depends(get_db),
) -> SessionResponse:
    """Update decision (Accepted or Rejected) for a debugging session."""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Debugging session '{session_id}' not found.",
        )
    try:
        session.decision = update.decision
        db.commit()
        db.refresh(session)
        return SessionResponse.model_validate(session)
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error updating decision: {str(exc)}",
        )


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(session_id: str, db: Session = Depends(get_db)) -> None:
    """Delete a debugging session by ID."""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Debugging session '{session_id}' not found.",
        )
    try:
        db.delete(session)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error deleting session: {str(exc)}",
        )

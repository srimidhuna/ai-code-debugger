from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.session import SessionModel
from app.schemas.debug import DashboardStats

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)) -> DashboardStats:
    """Return real database-backed dashboard statistics."""
    total_sessions = db.query(SessionModel).count()
    total_issues = 0
    accepted = 0
    rejected = 0
    recent_sessions = []

    sessions = db.query(SessionModel).order_by(SessionModel.timestamp.desc()).all()
    for s in sessions:
        issues_list = s.issues if isinstance(s.issues, list) else []
        total_issues += len(issues_list)
        if s.decision == "Accepted":
            accepted += 1
        elif s.decision == "Rejected":
            rejected += 1

    # Recent activity: last 5 sessions (summary info only, no source code)
    for s in sessions[:5]:
        recent_sessions.append({
            "id": s.id,
            "timestamp": s.timestamp.isoformat(),
            "language": s.language,
            "summary": s.summary,
            "decision": s.decision,
            "issues_count": len(s.issues) if isinstance(s.issues, list) else 0,
        })

    return DashboardStats(
        total_sessions=total_sessions,
        total_issues=total_issues,
        accepted_fixes=accepted,
        rejected_fixes=rejected,
        recent_sessions=recent_sessions,
    )

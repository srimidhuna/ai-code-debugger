import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, JSON
from app.database import Base

class SessionModel(Base):
    __tablename__ = "debugging_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    language = Column(String(32), nullable=False, index=True)
    original_code = Column(Text, nullable=False)
    fixed_code = Column(Text, nullable=False)
    summary = Column(Text, nullable=False)
    issues = Column(JSON, nullable=False, default=list)
    changes = Column(JSON, nullable=False, default=list)
    remaining_concerns = Column(JSON, nullable=False, default=list)
    decision = Column(String(16), nullable=False, default="Pending", index=True)
    model_name = Column(String(128), nullable=False)

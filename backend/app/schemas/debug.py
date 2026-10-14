from datetime import datetime
from typing import Any, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator

ALLOWED_LANGUAGES = {"python", "java", "c", "cpp", "javascript"}
SeverityType = Literal["Critical", "High", "Medium", "Low"]
CategoryType = Literal["Syntax", "Logic", "Runtime", "Code Quality"]
DecisionType = Literal["Pending", "Accepted", "Rejected"]

class DebugRequest(BaseModel):
    code: str = Field(..., description="The raw source code to analyze")
    language: str = Field(..., description="The programming language of the source code")

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        lang = v.strip().lower()
        if lang not in ALLOWED_LANGUAGES:
            raise ValueError(
                f"Unsupported language '{v}'. Supported languages: {', '.join(sorted(ALLOWED_LANGUAGES))}"
            )
        return lang

    @field_validator("code")
    @classmethod
    def validate_code_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Source code cannot be empty.")
        return v

class IssueItem(BaseModel):
    title: str = Field(..., description="Short description of the problem")
    severity: SeverityType = Field(..., description="Severity level of the issue")
    category: CategoryType = Field(..., description="Category of the issue")
    line: Optional[int] = Field(None, description="Starting 1-based line number if identifiable")
    line_end: Optional[int] = Field(None, description="Ending 1-based line number if identifiable")
    explanation: str = Field(..., description="Detailed explanation of why the issue occurs")
    suggestion: str = Field(..., description="Guidance on how to correct the issue")

class ChangeItem(BaseModel):
    description: str = Field(..., description="What was modified or corrected")
    reason: str = Field(default="", description="Why the change was necessary")

class AIAnalysisResult(BaseModel):
    summary: str = Field(..., description="Brief summary of overall code health and findings")
    issues: List[IssueItem] = Field(default_factory=list, description="List of detected code issues")
    fixed_code: str = Field(..., description="Complete corrected source code without truncation")
    changes: List[ChangeItem] = Field(default_factory=list, description="List of applied fixes and rationale")
    remaining_concerns: List[str] = Field(default_factory=list, description="Uncertainties or remaining notices")

    @field_validator("changes", mode="before")
    @classmethod
    def normalize_changes(cls, v: Any) -> list:
        if not v:
            return []
        if not isinstance(v, list):
            if isinstance(v, str):
                return [{"description": v, "reason": ""}]
            return []
        normalized = []
        for item in v:
            if isinstance(item, str):
                normalized.append({"description": item, "reason": ""})
            elif isinstance(item, dict):
                desc = item.get("description") or item.get("desc") or item.get("change") or ""
                reas = item.get("reason") or item.get("why") or ""
                if not desc:
                    # If model put entire text as single key or similar
                    desc = next((str(val) for val in item.values() if val), "")
                normalized.append({"description": str(desc), "reason": str(reas)})
            else:
                normalized.append({"description": str(item), "reason": ""})
        return normalized

    @field_validator("fixed_code")
    @classmethod
    def validate_fixed_code_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Fixed code returned by AI cannot be empty.")
        return v

class SessionResponse(BaseModel):
    id: str
    timestamp: datetime
    language: str
    original_code: str
    fixed_code: str
    summary: str
    issues: List[IssueItem]
    changes: List[ChangeItem]
    remaining_concerns: List[str]
    decision: DecisionType
    model_name: str

    model_config = {"from_attributes": True}

class DecisionUpdateRequest(BaseModel):
    decision: Literal["Accepted", "Rejected"] = Field(..., description="Decision must be 'Accepted' or 'Rejected'")


# ---------------------------------------------------------------------------
# Phase 4 schemas
# ---------------------------------------------------------------------------

class SessionListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    sessions: List[SessionResponse]


class DashboardStats(BaseModel):
    total_sessions: int
    total_issues: int
    accepted_fixes: int
    rejected_fixes: int
    recent_sessions: List[dict]

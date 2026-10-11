from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Literal
from app.schemas.post import AIPrediction

class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    include_explanation: bool = True

    @field_validator("text")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Text cannot be empty.")
        return value

class AnalyzeResponse(BaseModel):
    text: str
    detected_language: str
    language_supported: bool = False
    language_notice: Optional[str] = None
    prediction: AIPrediction
    action_recommendation: str  # "APPROVED", "FLAGGED_FOR_REVIEW", "BLOCKED"

class AdminReviewAction(BaseModel):
    action: str  # APPROVED, BLOCKED, FLAGGED_FOR_REVIEW, MARK_REVIEWED (+ aliases)
    confirm_action: bool = False

class AuditLogResponse(BaseModel):
    id: str
    actor_id: str
    actor_role: str
    event_type: str
    resource_id: Optional[str] = None
    timestamp: str

class ConsentRequest(BaseModel):
    analytics_cookies: bool = False
    policy_version: str = Field("1.0", max_length=20)

class PrivacyRequestCreate(BaseModel):
    request_type: Literal["CORRECT", "DELETE", "WITHDRAW_CONSENT", "PROCESSING_QUESTION", "PRIVACY_CONCERN"]
    description: Optional[str] = Field(None, max_length=2000)

class PrivacyRequestResponse(BaseModel):
    id: str
    request_type: str
    description: Optional[str] = None
    status: str
    response: Optional[str] = None
    created_at: str
    resolved_at: Optional[str] = None

class PrivacyRequestStatusUpdate(BaseModel):
    status: Literal["RESOLVED", "DECLINED"]
    response: str = Field(..., min_length=2, max_length=1000)

class DeleteAccountRequest(BaseModel):
    confirm_deletion: bool = False

class AppealRequest(BaseModel):
    reason: str = Field(..., min_length=5, max_length=1000)

from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from app.schemas.post import PostResponse
from app.schemas.comment import CommentResponse


class ModerationHistoryItem(BaseModel):
    content_id: str
    content_type: str
    ai_label: str
    confidence: float
    recommendation: Optional[str] = None
    action_taken: str
    timestamp: str
    human_review: Optional[Dict[str, Any]] = None


class UserDashboardStats(BaseModel):
    total_posts: int
    total_comments: int
    approved_posts: int
    pending_review_posts: int
    blocked_posts: int
    pending_review_comments: int


class UserDashboardResponse(BaseModel):
    stats: UserDashboardStats
    posts: List[PostResponse]
    comments: List[CommentResponse]
    moderation_history: List[ModerationHistoryItem]
    pending_items: List[Dict[str, Any]]


class AdminUserSummary(BaseModel):
    id: str
    username: str
    role: str
    is_active: bool
    created_at: str


class ConfidenceBucket(BaseModel):
    label: str
    count: int


class AnalyticsResponse(BaseModel):
    total_moderation_items: int
    total_posts: int
    total_comments: int
    approved_count: int
    flagged_count: int
    blocked_count: int
    hate_speech_count: int
    offensive_count: int
    normal_count: int
    override_count: int
    confidence_distribution: List[ConfidenceBucket]
    moderation_history_count: int
    pending_manual_reviews: int
    model_evaluation: Dict[str, Any]
    model_information: Dict[str, Any]


class AdminContentResponse(BaseModel):
    """Moderation context without author identifiers or account details."""
    id: str
    content_type: str
    content: str
    ai_prediction: Optional[Dict[str, Any]] = None
    moderation_recommendation: Optional[str] = None
    moderation_status: str
    moderation_explanation: Optional[str] = None
    created_at: str

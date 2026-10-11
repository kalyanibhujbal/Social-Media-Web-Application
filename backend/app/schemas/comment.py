from pydantic import BaseModel, Field
from typing import Optional, List
from app.schemas.post import AIPrediction

class CommentCreate(BaseModel):
    post_id: str = Field(..., description="Target post ID")
    content: str = Field(..., min_length=1, max_length=1000, description="Comment text content")

class CommentResponse(BaseModel):
    id: str
    post_id: str
    author_id: str
    author_username: str
    author_full_name: Optional[str] = None
    content: str
    language: str
    language_supported: Optional[bool] = None
    language_notice: Optional[str] = None
    moderation_recommendation: Optional[str] = None
    moderation_status: str
    moderation_explanation: Optional[str] = None
    ai_prediction: AIPrediction
    created_at: str
    like_count: int = 0
    liked_by_me: bool = False

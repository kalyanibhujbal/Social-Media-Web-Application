from pydantic import BaseModel, Field
from typing import Literal, Optional, List, Dict, Any

class PostCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000, description="Post text content for moderation and publishing")

class PostMedia(BaseModel):
    filename: str
    url: str
    media_type: Literal["image", "video"]
    mime_type: str
    size_bytes: int = Field(ge=1)

class EventDetails(BaseModel):
    title: str
    event_date: str
    event_time: str
    location: str

class ArticleDetails(BaseModel):
    title: str

class WordAttribution(BaseModel):
    word: str
    matched_rule: str = "Keyword rule"

class XAIExplanation(BaseModel):
    method: str = "Keyword Rule Highlights"
    top_words: List[WordAttribution] = []

class AIPrediction(BaseModel):
    label: str  # "Hate Speech", "Offensive", "Normal"
    predicted_class: str
    confidence: float
    confidence_level: str = "HIGH"  # "HIGH", "MEDIUM", "LOW"
    probabilities: Dict[str, float]
    is_low_confidence: bool
    model_name: Optional[str] = "xlm-roberta-base"
    model_version: Optional[str] = "1.0.0"
    inference_timestamp: Optional[str] = None
    explanation: Optional[XAIExplanation] = None

class PostResponse(BaseModel):
    id: str
    author_id: str
    author_username: str
    author_full_name: Optional[str] = None
    author_avatar_url: Optional[str] = None
    content: str = ""
    content_type: Literal["POST", "EVENT", "ARTICLE"] = "POST"
    media: List[PostMedia] = Field(default_factory=list)
    event: Optional[EventDetails] = None
    article: Optional[ArticleDetails] = None
    language: str = "en"
    language_supported: Optional[bool] = None
    language_notice: Optional[str] = None
    moderation_recommendation: Optional[str] = "Publish"  # "Publish", "Manual Review", "Block"
    moderation_status: str  # "APPROVED", "FLAGGED_FOR_REVIEW", "BLOCKED"
    moderation_explanation: Optional[str] = None
    ai_prediction: Optional[AIPrediction] = None
    created_at: str
    like_count: int = 0
    liked_by_me: bool = False
    saved_by_me: bool = False

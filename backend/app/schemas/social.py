from typing import List, Optional

from pydantic import BaseModel, Field


class PublicProfile(BaseModel):
    id: str
    username: str
    full_name: Optional[str] = None
    headline: Optional[str] = None
    location: Optional[str] = None
    about: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    created_at: str
    connection_count: int = 0
    follower_count: int = 0
    following_count: int = 0
    relationship: str = "NONE"


class ConnectionRequestCreate(BaseModel):
    target_user_id: str = Field(..., min_length=1, max_length=80)


class ConnectionSummary(BaseModel):
    id: str
    requester_id: str
    recipient_id: str
    status: str
    created_at: str
    updated_at: str
    other_user: PublicProfile


class NotificationResponse(BaseModel):
    id: str
    kind: str
    actor_id: Optional[str] = None
    actor_username: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    is_read: bool = False
    created_at: str


class ConversationCreate(BaseModel):
    participant_id: str = Field(..., min_length=1, max_length=80)


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    sender_id: str
    recipient_id: str
    content: str
    created_at: str
    is_read: bool = False


class ConversationSummary(BaseModel):
    id: str
    other_user: PublicProfile
    last_message: Optional[str] = None
    last_message_at: Optional[str] = None
    unread_count: int = 0

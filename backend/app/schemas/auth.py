from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List

class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=30, description="Unique username")
    email: EmailStr = Field(..., description="Valid user email address")
    full_name: Optional[str] = Field(None, min_length=1, max_length=80)
    password: str = Field(..., min_length=8, max_length=100, description="Password min 8 characters")
    terms_accepted: bool = Field(..., description="Must explicitly accept Terms & Privacy Policy")

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError("Username must contain at least 3 characters.")
        if not value.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username may contain letters, numbers, underscores, and hyphens only.")
        return value

    @field_validator("password")
    @classmethod
    def require_password_strength(cls, value: str) -> str:
        if not any(char.isalpha() for char in value) or not any(char.isdigit() for char in value):
            raise ValueError("Password must include at least one letter and one number.")
        return value

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str
    terms_accepted: bool
    created_at: str
    full_name: Optional[str] = None
    headline: Optional[str] = None
    location: Optional[str] = None
    about: Optional[str] = None
    skills: List[str] = Field(default_factory=list)

class ProfileUpdateRequest(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=30)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, min_length=1, max_length=80)
    headline: Optional[str] = Field(None, max_length=120)
    location: Optional[str] = Field(None, max_length=120)
    about: Optional[str] = Field(None, max_length=1000)
    skills: Optional[List[str]] = Field(None, max_length=20)
    current_password: str = Field(..., min_length=8, max_length=100)

    @field_validator("skills")
    @classmethod
    def normalize_skills(cls, value: Optional[List[str]]) -> Optional[List[str]]:
        if value is None:
            return None
        cleaned = [item.strip()[:40] for item in value if item.strip()]
        if len(cleaned) > 20:
            raise ValueError("A profile can include at most 20 skills.")
        return list(dict.fromkeys(cleaned))

class SessionResponse(BaseModel):
    user: UserResponse

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime, timezone

class User(BaseModel):
    id: str = Field(..., description="Unique user identifier (e.g., generated UUID or from OAuth provider)")
    email: EmailStr = Field(..., description="User's email address (used as primary key in Redis)")
    name: Optional[str] = Field(None, description="User's display name")
    password_hash: Optional[str] = Field(None, description="Hashed password for email/password auth")
    google_id: Optional[str] = Field(None, description="Google OAuth user ID")
    email_verified: bool = Field(False, description="Flag indicating if the email address is verified")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp of user creation")
    picture: Optional[str] = Field(None, description="URL to user's profile picture")
    credits: Optional[int] = Field(0, description="User's credit balance")
    # Add other fields as needed, e.g., verification tokens, password reset tokens

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

# You might add more models here for different API request/response structures

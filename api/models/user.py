from pydantic import BaseModel, EmailStr, Field
from typing import Optional
import datetime

class User(BaseModel):
    id: str = Field(..., description="Unique user identifier (e.g., generated UUID or from OAuth provider)")
    email: EmailStr = Field(..., description="User's email address (used as primary key in Redis)")
    name: Optional[str] = Field(None, description="User's display name")
    password_hash: Optional[str] = Field(None, description="Hashed password for email/password auth")
    google_id: Optional[str] = Field(None, description="Google OAuth user ID")
    email_verified: bool = Field(False, description="Flag indicating if the email address is verified")
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow, description="Timestamp of user creation")
    # Add other fields as needed, e.g., verification tokens, password reset tokens

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

# You might add more models here for different API request/response structures

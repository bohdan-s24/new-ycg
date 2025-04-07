import redis
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
import uuid
from typing import Optional, Dict, Any
import logging

# Google Auth libraries for ID token verification
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from ..config import Config # Use Config class directly
from ..models.user import User, UserCreate
from ..utils.db import get_redis_connection # Import from the new db utility file
from . import credits_service # Import credits service for initialization

# Password Hashing Context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Settings (adjust expiry as needed)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hashes a plain password."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Creates a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    if not Config.JWT_SECRET_KEY:
        raise ValueError("JWT_SECRET_KEY not configured")
    encoded_jwt = jwt.encode(to_encode, Config.JWT_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decodes a JWT access token."""
    if not Config.JWT_SECRET_KEY:
        # Log this error, as it shouldn't happen in a configured environment
        print("ERROR: JWT_SECRET_KEY not configured for decoding.") 
        return None
    try:
        payload = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

async def get_user_by_email(email: str) -> Optional[User]:
    """Retrieves a user from Redis by email."""
    r = await get_redis_connection()
    user_data_json = await r.get(f"user:{email}")
    if user_data_json:
        user_data = User.parse_raw(user_data_json)
        return user_data
    return None

async def create_user(user_data: UserCreate) -> Optional[User]:
    """Creates a new user in Redis."""
    r = await get_redis_connection()
    existing_user = await r.exists(f"user:{user_data.email}")
    if existing_user:
        return None # User already exists

    hashed_password = get_password_hash(user_data.password)
    user_id = str(uuid.uuid4())
    
    new_user = User(
        id=user_id,
        email=user_data.email,
        name=user_data.name,
        password_hash=hashed_password,
        created_at=datetime.utcnow()
        # Initialize other fields as needed
    )

    await r.set(f"user:{new_user.email}", new_user.json())
    # Consider setting an index for user ID if needed: await r.set(f"userid:{user_id}", new_user.email)
    
    return new_user

# --- Google ID Token Verification ---

async def verify_google_id_token(token: str) -> Optional[Dict[str, Any]]:
    """Verifies a Google ID token and returns the payload if valid."""
    try:
        if not Config.GOOGLE_CLIENT_ID:
            logging.error("GOOGLE_CLIENT_ID is not configured.")
            return None
            
        # Specify the CLIENT_ID of the app that accesses the backend:
        idinfo = id_token.verify_oauth2_token(
            token, 
            google_requests.Request(), 
            Config.GOOGLE_CLIENT_ID
        )
        
        # ID token is valid. Get the user's Google Account ID from the decoded token.
        # Other fields available: name, email, picture, etc.
        # See: https://developers.google.com/identity/sign-in/web/backend-auth#verify-the-integrity-of-the-id-token
        return idinfo

    except ValueError as e:
        # Invalid token
        logging.error(f"Google ID token verification failed: {e}")
        return None
    except Exception as e:
        # Other potential errors
        logging.error(f"An unexpected error occurred during Google token verification: {e}")
        return None


async def get_user_by_google_id(google_id: str) -> Optional[User]:
    """Retrieves a user from Redis by their Google ID."""
    # This requires an index like 'googleid:<google_id>' -> 'user_email' or storing google_id directly in user data
    # For simplicity, let's assume we store google_id in the user object and search by email first
    # A more robust solution might involve a secondary index.
    # This function might not be strictly necessary if get_or_create handles it.
    logging.warning("get_user_by_google_id is not fully implemented - relies on email lookup primarily.")
    return None # Placeholder - implement if needed with proper indexing


async def get_or_create_google_user(idinfo: Dict[str, Any]) -> Optional[User]:
    """
    Retrieves an existing user based on Google ID info (email or google_id) 
    or creates a new user if one doesn't exist.
    """
    r = await get_redis_connection()
    user_email = idinfo.get('email')
    google_user_id = idinfo.get('sub') # 'sub' is the Google User ID
    user_name = idinfo.get('name')
    # picture = idinfo.get('picture') # Can store this too if needed

    if not user_email or not google_user_id:
        logging.error("Google ID token payload missing email or sub (google_id).")
        return None

    # 1. Check if user exists by email
    user = await get_user_by_email(user_email)

    if user:
        # User found by email. Check if Google ID needs linking.
        if not user.google_id:
            logging.info(f"Linking Google ID {google_user_id} to existing user {user_email}")
            user.google_id = google_user_id
            # Update user data in Redis
            await r.set(f"user:{user.email}", user.json())
            # Consider adding/updating the google_id index if you implement one
        elif user.google_id != google_user_id:
            # This case is problematic: same email, different Google ID. Log an error.
            logging.error(f"User email {user_email} exists but with a different Google ID ({user.google_id}) than the one provided ({google_user_id}).")
            # Decide how to handle this - maybe return None or raise an exception?
            return None 
        return user
    else:
        # 2. User not found by email, create a new user
        logging.info(f"Creating new user from Google login: {user_email}")
        new_user_id = str(uuid.uuid4()) # Generate our own internal ID
        
        new_user = User(
            id=new_user_id,
            email=user_email,
            name=user_name,
            google_id=google_user_id,
            email_verified=idinfo.get('email_verified', False), # Use verification status from Google
            created_at=datetime.utcnow()
            # No password_hash needed for Google-only users
        )

        await r.set(f"user:{new_user.email}", new_user.json())
        # Consider setting indexes: await r.set(f"userid:{new_user_id}", new_user.email)
        # await r.set(f"googleid:{google_user_id}", new_user.email) # If implementing google_id index

        # Initialize credits for the new user
        try:
            await credits_service.initialize_credits(new_user.id)
        except Exception as e:
            logging.error(f"Failed to initialize credits for new Google user {new_user.id}: {e}")
            # Continue user creation even if credit init fails

        return new_user

# --- Placeholder for Email Verification ---
# async def generate_verification_token(user_email: str) -> str:
#     # 1. Check if user exists by google_id or email
#     # 2. If exists, return user
#     # 3. If not exists, create a new user record
#     # 4. Return the user
#     pass

# --- Placeholder for Email Verification ---
# async def generate_verification_token(user_email: str) -> str:
#     pass
# async def verify_email_token(token: str) -> Optional[str]: # returns user email if valid
#     pass

# --- Placeholder for Password Reset ---
# async def generate_password_reset_token(user_email: str) -> str:
#     pass
# async def reset_password_with_token(token: str, new_password: str) -> bool:
#     pass

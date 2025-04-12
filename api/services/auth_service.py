import redis
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
import uuid
from typing import Optional, Dict, Any, Tuple
import logging

import httpx # Use httpx for async requests
import logging

# Google Auth libraries (we might not need id_token verification anymore if using OAuth token)
# from google.oauth2 import id_token
# from google.auth.transport import requests as google_requests

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
        expire = datetime.now(datetime.timezone.utc) + expires_delta
    else:
        expire = datetime.now(datetime.timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
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
        user_data = User.model_validate_json(user_data_json)
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
        created_at=datetime.now(datetime.timezone.utc)
        # Initialize other fields as needed
    )

    await r.set(f"user:{new_user.email}", new_user.model_dump_json())
    # Consider setting an index for user ID if needed: await r.set(f"userid:{user_id}", new_user.email)

    return new_user

# --- Google OAuth Token Verification (using userinfo endpoint) ---

async def verify_google_oauth_token(token: str) -> Optional[Dict[str, Any]]:
    """Verifies a Google OAuth token by fetching user info and returns it if valid."""
    # Google's userinfo endpoint
    userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"
    headers = {"Authorization": f"Bearer {token}"}

    # Log token prefix for debugging (not the full token for security)
    token_prefix = token[:10] if token else "None"
    logging.info(f"Verifying Google OAuth token (prefix: {token_prefix}...) using userinfo endpoint")

    try:
        async with httpx.AsyncClient() as client:
            logging.info(f"Sending request to {userinfo_url}")
            # Add timeout to prevent hanging requests
            response = await client.get(userinfo_url, headers=headers, timeout=10.0)

        logging.info(f"Google userinfo response status: {response.status_code}")

        if response.status_code == 200:
            userinfo = response.json()
            logging.info(f"Google userinfo response: {userinfo}")

            # Basic validation: check for 'sub' (Google ID) and 'email'
            if 'sub' in userinfo and 'email' in userinfo:
                 # Add email_verified if present, default to False otherwise
                userinfo['email_verified'] = userinfo.get('email_verified', False)
                logging.info(f"Successfully verified Google OAuth token for email: {userinfo.get('email')}")
                return userinfo
            else:
                logging.error(f"Google userinfo response missing 'sub' or 'email': {userinfo}")
                return None
        else:
            response_text = await response.text()
            logging.error(f"Failed to verify Google OAuth token. Status: {response.status_code}, Response: {response_text}")
            return None

    except httpx.RequestError as e:
        logging.error(f"HTTP error during Google OAuth token verification: {e}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred during Google OAuth token verification: {e}")
        return None


async def get_user_by_google_id(google_id: str) -> Optional[User]:
    """Retrieves a user from Redis by their Google ID."""
    # This requires an index like 'googleid:<google_id>' -> 'user_email' or storing google_id directly in user data
    # For simplicity, let's assume we store google_id in the user object and search by email first
    # A more robust solution might involve a secondary index.
    """Retrieves a user from Redis by their Google ID using the secondary index."""
    r = await get_redis_connection()
    google_id_key = f"googleid:{google_id}"
    user_key = await r.get(google_id_key) # Get the primary user key (e.g., user:email@example.com)

    if not user_key:
        logging.info(f"No user found for Google ID index: {google_id_key}")
        return None

    # Now retrieve the actual user data using the primary key
    user_data_json = await r.get(user_key)
    if user_data_json:
        try:
            user_data = User.model_validate_json(user_data_json)
            logging.info(f"Retrieved user {user_key} using Google ID {google_id}")
            return user_data
        except Exception as e:
            logging.error(f"Failed to parse user data for key {user_key} retrieved via Google ID {google_id}: {e}")
            return None
    else:
        # This indicates an inconsistency, the index exists but the user data doesn't
        logging.error(f"Inconsistency: Google ID index {google_id_key} points to non-existent user key {user_key}")
        # Optionally, clean up the stale index
        # await r.delete(google_id_key)
        return None


async def get_or_create_google_user(userinfo: Dict[str, Any]) -> Tuple[Optional[User], bool]:
    """
    Retrieves an existing user based on Google userinfo (email or google_id)
    or creates a new user if one doesn't exist.

    Returns:
        A tuple (user, is_new_user) where:
        - user: The User object or None if an error occurred
        - is_new_user: Boolean indicating whether this was a new user registration
    """
    r = await get_redis_connection()
    user_email = userinfo.get('email')
    google_user_id = userinfo.get('sub') # 'sub' is the Google User ID
    user_name = userinfo.get('name')
    picture = userinfo.get('picture') # Can store this too if needed

    if not user_email or not google_user_id:
        logging.error("Google userinfo missing email or sub (google_id).")
        return None, False

    # 1. Check if user exists by email
    user = await get_user_by_email(user_email)

    if user:
        # User found by email. Check if Google ID needs linking.
        if not user.google_id:
            logging.info(f"Linking Google ID {google_user_id} to existing user {user_email}")
            user.google_id = google_user_id
            # Update user data in Redis
            await r.set(f"user:{user.email}", user.model_dump_json())
            # Set the secondary index googleid:<google_id> -> user:<email>
            await r.set(f"googleid:{google_user_id}", f"user:{user.email}")
            logging.info(f"Set Google ID index for {google_user_id} to {f'user:{user.email}'}")
        elif user.google_id != google_user_id:
            # This case is problematic: same email, different Google ID. Log an error.
            logging.error(f"User email {user_email} exists but with a different Google ID ({user.google_id}) than the one provided ({google_user_id}).")
            # Decide how to handle this - maybe return None or raise an exception?
            return None, False
        return user, False
    else:
        # 2. User not found by email, create a new user
        logging.info(f"Creating new user from Google login: {user_email}")
        new_user_id = str(uuid.uuid4()) # Generate our own internal ID

        new_user = User(
            id=new_user_id,
            email=user_email,
            name=user_name,
            google_id=google_user_id,
            email_verified=userinfo.get('email_verified', False), # Use verification status from Google
            created_at=datetime.now(datetime.timezone.utc)
            # No password_hash needed for Google-only users
            # Add picture field to User model if you want to store it
        )

        # Store primary user data and secondary indexes
        user_key = f"user:{new_user.email}"
        google_id_key = f"googleid:{google_user_id}"
        # Store user data and indexes
        # Note: Upstash Redis client might not support transactions in pipeline
        # so we'll use individual commands
        try:
            # Store the user data
            await r.set(user_key, new_user.model_dump_json())
            logging.info(f"Stored user data at {user_key}")

            # Store the Google ID index
            await r.set(google_id_key, user_key) # Map googleid to primary user key
            logging.info(f"Stored Google ID index at {google_id_key}")

            # Consider setting userid index too if needed
            # await r.set(f"userid:{new_user_id}", user_key)
        except Exception as e:
            logging.error(f"Error storing user data: {e}")
            raise

        logging.info(f"Stored new user {user_key} and index {google_id_key}")

        # Initialize credits for the new user
        try:
            await credits_service.initialize_credits(new_user.id)
        except Exception as e:
            logging.error(f"Failed to initialize credits for new Google user {new_user.id}: {e}")
            # Continue user creation even if credit init fails

        return new_user, True

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

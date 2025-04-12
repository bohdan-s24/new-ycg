"""
User service for handling user-related operations.
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

from pydantic import ValidationError

from ..models.user import User
from ..utils.db import redis_operation
from ..utils.exceptions import ResourceNotFoundError, ValidationError as AppValidationError
from ..services import credits_service


# Redis key prefixes
USER_KEY_PREFIX = "user:"
GOOGLE_ID_KEY_PREFIX = "google:"
EMAIL_KEY_PREFIX = "email:"


async def get_user_by_id(user_id: str) -> Optional[User]:
    """
    Retrieves a user by ID.
    
    Args:
        user_id: The user's ID
        
    Returns:
        User object if found, None otherwise
    """
    key = f"{USER_KEY_PREFIX}{user_id}"
    
    async def _get_user(redis, user_id):
        user_data_json = await redis.get(key)
        if not user_data_json:
            return None
        try:
            return User.model_validate_json(user_data_json)
        except ValidationError as e:
            logging.error(f"Error parsing user data for {user_id}: {e}")
            return None
    
    return await redis_operation("get_user_by_id", _get_user, user_id)


async def get_user_by_email(email: str) -> Optional[User]:
    """
    Retrieves a user by email.
    
    Args:
        email: The user's email
        
    Returns:
        User object if found, None otherwise
    """
    email_key = f"{EMAIL_KEY_PREFIX}{email}"
    
    async def _get_user_by_email(redis, email):
        # Get the user key from the email index
        user_key = await redis.get(email_key)
        if not user_key:
            return None
            
        # Get the user data
        user_data_json = await redis.get(user_key)
        if not user_data_json:
            return None
            
        try:
            return User.model_validate_json(user_data_json)
        except ValidationError as e:
            logging.error(f"Error parsing user data for email {email}: {e}")
            return None
    
    return await redis_operation("get_user_by_email", _get_user_by_email, email)


async def get_user_by_google_id(google_id: str) -> Optional[User]:
    """
    Retrieves a user by Google ID.
    
    Args:
        google_id: The user's Google ID
        
    Returns:
        User object if found, None otherwise
    """
    google_id_key = f"{GOOGLE_ID_KEY_PREFIX}{google_id}"
    
    async def _get_user_by_google_id(redis, google_id):
        # Get the user key from the Google ID index
        user_key = await redis.get(google_id_key)
        if not user_key:
            return None
            
        # Get the user data
        user_data_json = await redis.get(user_key)
        if not user_data_json:
            return None
            
        try:
            return User.model_validate_json(user_data_json)
        except ValidationError as e:
            logging.error(f"Error parsing user data for Google ID {google_id}: {e}")
            return None
    
    return await redis_operation("get_user_by_google_id", _get_user_by_google_id, google_id)


async def create_user(user_data: Dict[str, Any]) -> User:
    """
    Creates a new user.
    
    Args:
        user_data: Dictionary containing user data
        
    Returns:
        The created User object
        
    Raises:
        ValidationError: If the user data is invalid
    """
    try:
        # Generate a unique user ID
        user_id = str(uuid.uuid4())
        
        # Create the user object
        new_user = User(
            id=user_id,
            email=user_data.get("email"),
            name=user_data.get("name"),
            picture=user_data.get("picture"),
            created_at=datetime.now(datetime.timezone.utc),
            google_id=user_data.get("google_id"),
            credits=0  # Will be initialized with free credits later
        )
        
        # Store the user
        await save_user(new_user)
        
        # Initialize credits for the new user
        await credits_service.initialize_credits(user_id)
        
        return new_user
    except ValidationError as e:
        logging.error(f"Error creating user: {e}")
        raise AppValidationError("Invalid user data", errors=e.errors())


async def save_user(user: User) -> bool:
    """
    Saves a user to the database.
    
    Args:
        user: The User object to save
        
    Returns:
        True if successful, False otherwise
    """
    user_key = f"{USER_KEY_PREFIX}{user.id}"
    email_key = f"{EMAIL_KEY_PREFIX}{user.email}"
    
    async def _save_user(redis, user):
        # Store the user data
        await redis.set(user_key, user.model_dump_json())
        
        # Store the email index
        if user.email:
            await redis.set(email_key, user_key)
            
        # Store the Google ID index if available
        if user.google_id:
            google_id_key = f"{GOOGLE_ID_KEY_PREFIX}{user.google_id}"
            await redis.set(google_id_key, user_key)
            
        return True
    
    try:
        return await redis_operation("save_user", _save_user, user)
    except Exception as e:
        logging.error(f"Error saving user {user.id}: {e}")
        return False


async def update_user(user_id: str, update_data: Dict[str, Any]) -> User:
    """
    Updates a user's information.
    
    Args:
        user_id: The user's ID
        update_data: Dictionary containing fields to update
        
    Returns:
        The updated User object
        
    Raises:
        ResourceNotFoundError: If the user is not found
        ValidationError: If the update data is invalid
    """
    # Get the current user
    user = await get_user_by_id(user_id)
    if not user:
        raise ResourceNotFoundError("User", user_id)
        
    # Update the user object
    user_dict = user.model_dump()
    for key, value in update_data.items():
        if hasattr(user, key):
            user_dict[key] = value
            
    try:
        # Create a new user object with the updated data
        updated_user = User(**user_dict)
        
        # Save the updated user
        success = await save_user(updated_user)
        if not success:
            raise Exception("Failed to save updated user")
            
        return updated_user
    except ValidationError as e:
        logging.error(f"Error updating user {user_id}: {e}")
        raise AppValidationError("Invalid user data", errors=e.errors())


async def get_or_create_google_user(google_user_info: Dict[str, Any]) -> Tuple[User, bool]:
    """
    Gets or creates a user based on Google user info.
    
    Args:
        google_user_info: Dictionary containing Google user information
        
    Returns:
        Tuple containing (User object, bool indicating if user was created)
        
    Raises:
        ValidationError: If the user data is invalid
    """
    google_id = google_user_info.get("sub")
    if not google_id:
        raise AppValidationError("Google user info missing 'sub' field")
        
    # Try to find the user by Google ID
    user = await get_user_by_google_id(google_id)
    if user:
        # User exists, update their information if needed
        update_needed = False
        update_data = {}
        
        # Check if any fields need updating
        if user.name != google_user_info.get("name"):
            update_data["name"] = google_user_info.get("name")
            update_needed = True
            
        if user.picture != google_user_info.get("picture"):
            update_data["picture"] = google_user_info.get("picture")
            update_needed = True
            
        if update_needed:
            user = await update_user(user.id, update_data)
            
        return user, False
        
    # User doesn't exist, create a new one
    user_data = {
        "email": google_user_info.get("email"),
        "name": google_user_info.get("name"),
        "picture": google_user_info.get("picture"),
        "google_id": google_id
    }
    
    new_user = await create_user(user_data)
    return new_user, True

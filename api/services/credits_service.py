import logging
import json
import datetime
from typing import Optional

from ..utils.db import redis_operation
# User model import removed - will be added back when needed

# Constants for credit plans (can be moved to config if needed)
FREE_CREDITS_ON_SIGNUP = 3
DEFAULT_GENERATION_COST = 1 # Cost per chapter generation

# Constants for chapter generation limits
MAX_GENERATIONS_PER_CREDIT = 3  # Initial + 2 regenerations
MAX_TOTAL_GENERATIONS = 6  # Maximum total generations (initial + 5 regenerations)

# Redis key prefixes
CREDIT_BALANCE_KEY_PREFIX = "credits:"
TRANSACTION_LOG_KEY_PREFIX = "transactions:" # Using a Redis List for transaction log
VIDEO_GENERATIONS_KEY_PREFIX = "video_generations:"  # Track generations per video per user

async def initialize_credits(user_id: str):
    """Sets the initial free credits for a new user."""
    key = f"{CREDIT_BALANCE_KEY_PREFIX}{user_id}"

    # Define the operation function
    async def _initialize_credits(redis, user_id):
        # Use SETNX to avoid overwriting if called multiple times accidentally
        await redis.setnx(key, FREE_CREDITS_ON_SIGNUP)
        logging.info(f"Initialized credits for user {user_id} with {FREE_CREDITS_ON_SIGNUP} credits.")
        return True

    # Execute the operation
    await redis_operation("initialize_credits", _initialize_credits, user_id)

    # Log the initial transaction
    await add_transaction(user_id, FREE_CREDITS_ON_SIGNUP, "signup_bonus", "Initial free credits")


async def get_credit_balance(user_id: str) -> int:
    """Retrieves the current credit balance for a user."""
    key = f"{CREDIT_BALANCE_KEY_PREFIX}{user_id}"

    async def _get_balance(redis, _):
        balance = await redis.get(key)
        logging.info(f"[DEBUG] get_credit_balance: Redis key={key}, raw value={balance}")
        return int(balance) if balance is not None else 0

    return await redis_operation("get_credit_balance", _get_balance, user_id)

async def has_sufficient_credits(user_id: str, amount_needed: int = DEFAULT_GENERATION_COST) -> bool:
    """
    Checks if the user has enough credits.

    If amount_needed is 0, always returns True.
    """
    # If no credits are needed, always return True
    if amount_needed == 0:
        return True

    current_balance = await get_credit_balance(user_id)
    return current_balance >= amount_needed

async def deduct_credits(user_id: str, amount: int = DEFAULT_GENERATION_COST, description: str = "Chapter generation") -> bool:
    """
    Deducts credits from a user's balance. Returns True if successful, False otherwise.
    Implements atomic check-and-decrement operation.

    If amount is 0, no credits are deducted but the transaction is still logged.
    """
    key = f"{CREDIT_BALANCE_KEY_PREFIX}{user_id}"

    # If amount is 0, just log the transaction and return True
    if amount == 0:
        logging.info(f"No credits needed for user {user_id} for operation: {description}")

        # Log the free transaction
        await add_transaction(user_id, 0, "free_operation", description)
        return True

    async def _deduct_credits(redis, user_id, amount, description):
        # First, get the current balance
        current_balance = await redis.get(key)
        current_balance = int(current_balance) if current_balance is not None else 0

        # Check if there are enough credits
        if current_balance < amount:
            logging.warning(f"Insufficient credits for user {user_id}. Has {current_balance}, needs {amount}.")
            return False

        # Deduct the credits
        new_balance = await redis.decrby(key, amount)
        logging.info(f"Deducted {amount} credits from user {user_id}. New balance: {new_balance}")

        # Log the transaction (using the same redis connection)
        transaction_key = f"{TRANSACTION_LOG_KEY_PREFIX}{user_id}"
        transaction_data = {
            "timestamp": datetime.datetime.now().isoformat(),
            "amount": -amount,
            "type": "deduction",
            "description": description
        }
        await redis.lpush(transaction_key, json.dumps(transaction_data))

        return True

    try:
        return await redis_operation("deduct_credits", _deduct_credits, user_id, amount, description)
    except Exception as e:
        logging.error(f"Error deducting credits for user {user_id}: {e}")
        return False


async def add_credits(user_id: str, amount: int, transaction_type: str = "purchase", description: str = "Credit purchase") -> Optional[int]:
    """Adds credits to a user's balance. Returns the new balance or None on error."""
    if amount <= 0:
        logging.warning(f"Attempted to add non-positive credit amount ({amount}) for user {user_id}")
        return None

    key = f"{CREDIT_BALANCE_KEY_PREFIX}{user_id}"

    async def _add_credits(redis, user_id, amount, transaction_type, description):
        # Add the credits
        new_balance = await redis.incrby(key, amount)
        logging.info(f"Added {amount} credits to user {user_id}. New balance: {new_balance}")

        # Log the transaction (using the same redis connection)
        transaction_key = f"{TRANSACTION_LOG_KEY_PREFIX}{user_id}"
        transaction_data = {
            "timestamp": datetime.datetime.now().isoformat(),
            "amount": amount,
            "type": transaction_type,
            "description": description
        }
        await redis.lpush(transaction_key, json.dumps(transaction_data))

        return new_balance

    try:
        return await redis_operation("add_credits", _add_credits, user_id, amount, transaction_type, description)
    except Exception as e:
        logging.error(f"Error adding credits for user {user_id}: {e}")
        return None

async def add_transaction(user_id: str, amount: int, type: str, description: str):
    """Adds a transaction record to the user's log (using a Redis List)."""
    key = f"{TRANSACTION_LOG_KEY_PREFIX}{user_id}"
    async def _add_transaction(redis, _, amount, type, description):
        transaction_data = {
            "timestamp": datetime.datetime.now().isoformat(),
            "amount": amount,
            "type": type,
            "description": description
        }
        # LPUSH adds to the beginning of the list
        await redis.lpush(key, json.dumps(transaction_data))
        # Trim the list to keep only the last N transactions
        await redis.ltrim(key, 0, 999)  # Keep latest 1000 transactions
        return True

    try:
        await redis_operation("add_transaction", _add_transaction, user_id, amount, type, description)
    except Exception as e:
        logging.error(f"Failed to log transaction for user {user_id}: {e}")

async def get_transactions(user_id: str, offset: int = 0, limit: int = 20):
    """Retrieves the paginated transactions for a user."""
    key = f"{TRANSACTION_LOG_KEY_PREFIX}{user_id}"

    async def _get_transactions(redis, _, offset, limit):
        start = offset
        end = offset + limit - 1
        transactions_json = await redis.lrange(key, start, end)
        transactions = [json.loads(t) for t in transactions_json]
        total = await redis.llen(key)
        return transactions, total

    try:
        return await redis_operation("get_transactions", _get_transactions, user_id, offset, limit)
    except Exception as e:
        logging.error(f"Failed to retrieve transactions for user {user_id}: {e}")
        return [], 0

async def get_video_generation_count(user_id: str, video_id: str) -> int:
    """
    Get the number of times a user has generated chapters for a specific video.

    Args:
        user_id: The user ID
        video_id: The YouTube video ID

    Returns:
        The number of generations for this video
    """
    key = f"{VIDEO_GENERATIONS_KEY_PREFIX}{user_id}:{video_id}"

    async def _get_count(redis, _):
        count = await redis.get(key)
        return int(count) if count is not None else 0

    try:
        return await redis_operation("get_video_generation_count", _get_count, user_id)
    except Exception as e:
        logging.error(f"Failed to get generation count for user {user_id}, video {video_id}: {e}")
        return 0

async def increment_video_generation_count(user_id: str, video_id: str) -> int:
    """
    Increment the generation count for a specific video.

    Args:
        user_id: The user ID
        video_id: The YouTube video ID

    Returns:
        The new count after incrementing
    """
    key = f"{VIDEO_GENERATIONS_KEY_PREFIX}{user_id}:{video_id}"

    async def _increment_count(redis, _):
        new_count = await redis.incr(key)
        # Set expiry to 30 days to avoid keeping this data forever
        await redis.expire(key, 60 * 60 * 24 * 30)
        return int(new_count)

    try:
        return await redis_operation("increment_video_generation_count", _increment_count, user_id)
    except Exception as e:
        logging.error(f"Failed to increment generation count for user {user_id}, video {video_id}: {e}")
        return 0

async def calculate_credits_needed(user_id: str, video_id: str) -> int:
    """
    Calculate how many credits are needed for the next generation based on current count.

    Args:
        user_id: The user ID
        video_id: The YouTube video ID

    Returns:
        Number of credits needed (0 or 1) or -1 if max generations reached
    """
    current_count = await get_video_generation_count(user_id, video_id)

    # If we've reached the maximum total generations, return -1
    if current_count >= MAX_TOTAL_GENERATIONS:
        return -1

    # First generation (count = 0) always costs 1 credit
    if current_count == 0:
        return DEFAULT_GENERATION_COST

    # For regenerations within the first credit's limit (count = 1 or 2)
    # No additional credit is needed
    if current_count < MAX_GENERATIONS_PER_CREDIT:
        return 0

    # For regenerations beyond the first credit's limit (count = 3)
    # We need a new credit for the 4th generation (count = 3)
    if current_count == MAX_GENERATIONS_PER_CREDIT:
        return DEFAULT_GENERATION_COST

    # For regenerations within the second credit's limit (count = 4 or 5)
    # No additional credit is needed
    return 0

async def has_reached_max_generations(user_id: str, video_id: str) -> bool:
    """
    Check if a user has reached the maximum number of generations for a video.

    Args:
        user_id: The user ID
        video_id: The YouTube video ID

    Returns:
        True if the user has reached the maximum generations, False otherwise
    """
    current_count = await get_video_generation_count(user_id, video_id)
    return current_count >= MAX_TOTAL_GENERATIONS

async def get_remaining_generations(user_id: str, video_id: str) -> int:
    """
    Get the number of remaining generations for a video.

    Args:
        user_id: The user ID
        video_id: The YouTube video ID

    Returns:
        Number of remaining generations (0 to MAX_TOTAL_GENERATIONS)
    """
    current_count = await get_video_generation_count(user_id, video_id)
    remaining = max(0, MAX_TOTAL_GENERATIONS - current_count)
    return remaining

async def can_regenerate_for_free(user_id: str, video_id: str) -> bool:
    """
    Determines if a user can regenerate chapters for free based on their generation count.

    Args:
        user_id: The user ID
        video_id: The YouTube video ID

    Returns:
        True if the user can regenerate for free, False otherwise
    """
    current_count = await get_video_generation_count(user_id, video_id)

    # If current count is 1 or 2, they can regenerate for free (within first credit's limit)
    if 0 < current_count < MAX_GENERATIONS_PER_CREDIT:
        return True

    # If current count is 4 or 5, they can regenerate for free (within second credit's limit)
    if MAX_GENERATIONS_PER_CREDIT < current_count < MAX_TOTAL_GENERATIONS:
        return True

    return False

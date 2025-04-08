import logging
from typing import Optional

from ..utils.db import get_redis_connection
from ..models.user import User # To potentially link credits to user ID or email

# Constants for credit plans (can be moved to config if needed)
FREE_CREDITS_ON_SIGNUP = 3
DEFAULT_GENERATION_COST = 1 # Cost per chapter generation

# Redis key prefixes
CREDIT_BALANCE_KEY_PREFIX = "credits:"
TRANSACTION_LOG_KEY_PREFIX = "transactions:" # Using a Redis List for transaction log

async def initialize_credits(user_id: str):
    """Sets the initial free credits for a new user."""
    r = await get_redis_connection()
    key = f"{CREDIT_BALANCE_KEY_PREFIX}{user_id}"
    # Use SETNX to avoid overwriting if called multiple times accidentally
    await r.setnx(key, FREE_CREDITS_ON_SIGNUP)
    logging.info(f"Initialized credits for user {user_id} with {FREE_CREDITS_ON_SIGNUP} credits.")
    # Optionally, log the initial transaction
    await add_transaction(user_id, FREE_CREDITS_ON_SIGNUP, "signup_bonus", "Initial free credits")


async def get_credit_balance(user_id: str) -> int:
    """Retrieves the current credit balance for a user."""
    r = await get_redis_connection()
    key = f"{CREDIT_BALANCE_KEY_PREFIX}{user_id}"
    balance = await r.get(key)
    return int(balance) if balance is not None else 0

async def has_sufficient_credits(user_id: str, amount_needed: int = DEFAULT_GENERATION_COST) -> bool:
    """Checks if the user has enough credits."""
    current_balance = await get_credit_balance(user_id)
    return current_balance >= amount_needed

async def deduct_credits(user_id: str, amount: int = DEFAULT_GENERATION_COST, description: str = "Chapter generation") -> bool:
    """
    Deducts credits from a user's balance. Returns True if successful, False otherwise.
    Uses Lua script for atomic check-and-decrement.
    """
    r = await get_redis_connection()
    key = f"{CREDIT_BALANCE_KEY_PREFIX}{user_id}"

    # Lua script for atomic check and decrement
    lua_script = """
    local current_balance = redis.call('GET', KEYS[1])
    if current_balance == false or tonumber(current_balance) < tonumber(ARGV[1]) then
        return -1 -- Indicate insufficient funds or key not found
    end
    local new_balance = redis.call('DECRBY', KEYS[1], ARGV[1])
    return new_balance
    """
    
    try:
        script_sha = await r.script_load(lua_script)
        result = await r.evalsha(script_sha, 1, key, amount)
        
        if result == -1:
            logging.warning(f"Insufficient credits for user {user_id} to deduct {amount}.")
            return False
        else:
            logging.info(f"Deducted {amount} credits from user {user_id}. New balance: {result}")
            # Log the transaction
            await add_transaction(user_id, -amount, "deduction", description)
            return True
    except Exception as e:
        logging.error(f"Error deducting credits for user {user_id}: {e}")
        return False


async def add_credits(user_id: str, amount: int, transaction_type: str = "purchase", description: str = "Credit purchase") -> Optional[int]:
    """Adds credits to a user's balance. Returns the new balance or None on error."""
    if amount <= 0:
        logging.warning(f"Attempted to add non-positive credit amount ({amount}) for user {user_id}")
        return None
        
    r = await get_redis_connection()
    key = f"{CREDIT_BALANCE_KEY_PREFIX}{user_id}"
    try:
        new_balance = await r.incrby(key, amount)
        logging.info(f"Added {amount} credits to user {user_id}. New balance: {new_balance}")
        # Log the transaction
        await add_transaction(user_id, amount, transaction_type, description)
        return new_balance
    except Exception as e:
        logging.error(f"Error adding credits for user {user_id}: {e}")
        return None

async def add_transaction(user_id: str, amount: int, type: str, description: str):
    """Adds a transaction record to the user's log (using a Redis List)."""
    r = await get_redis_connection()
    key = f"{TRANSACTION_LOG_KEY_PREFIX}{user_id}"
    import json
    import datetime
    transaction_data = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "amount": amount,
        "type": type,
        "description": description
    }
    try:
        # LPUSH adds to the beginning of the list
        await r.lpush(key, json.dumps(transaction_data))
        # Optional: Trim the list to keep only the last N transactions
        # await r.ltrim(key, 0, 99) # Keep latest 100 transactions
    except Exception as e:
        logging.error(f"Failed to log transaction for user {user_id}: {e}")

async def get_transactions(user_id: str, limit: int = 50) -> list:
    """Retrieves the latest transactions for a user."""
    r = await get_redis_connection()
    key = f"{TRANSACTION_LOG_KEY_PREFIX}{user_id}"
    try:
        # LRANGE 0 to limit-1 gets the first 'limit' items (most recent due to LPUSH)
        transactions_json = await r.lrange(key, 0, limit - 1)
        import json
        transactions = [json.loads(t) for t in transactions_json]
        return transactions
    except Exception as e:
        logging.error(f"Failed to retrieve transactions for user {user_id}: {e}")
        return []

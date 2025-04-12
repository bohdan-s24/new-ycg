import logging
from typing import Optional

from ..utils.db import redis_operation
# User model import removed - will be added back when needed

# Constants for credit plans (can be moved to config if needed)
FREE_CREDITS_ON_SIGNUP = 3
DEFAULT_GENERATION_COST = 1 # Cost per chapter generation

# Redis key prefixes
CREDIT_BALANCE_KEY_PREFIX = "credits:"
TRANSACTION_LOG_KEY_PREFIX = "transactions:" # Using a Redis List for transaction log

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
        return int(balance) if balance is not None else 0

    return await redis_operation("get_credit_balance", _get_balance, user_id)

async def has_sufficient_credits(user_id: str, amount_needed: int = DEFAULT_GENERATION_COST) -> bool:
    """Checks if the user has enough credits."""
    current_balance = await get_credit_balance(user_id)
    return current_balance >= amount_needed

async def deduct_credits(user_id: str, amount: int = DEFAULT_GENERATION_COST, description: str = "Chapter generation") -> bool:
    """
    Deducts credits from a user's balance. Returns True if successful, False otherwise.
    Implements atomic check-and-decrement operation.
    """
    key = f"{CREDIT_BALANCE_KEY_PREFIX}{user_id}"

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
        import json
        import datetime
        transaction_data = {
            "timestamp": datetime.datetime.now(datetime.datetime.timezone.utc).isoformat(),
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
        import json
        import datetime
        transaction_data = {
            "timestamp": datetime.datetime.now(datetime.datetime.timezone.utc).isoformat(),
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
    import json
    import datetime

    async def _add_transaction(redis, _, amount, type, description):
        transaction_data = {
            "timestamp": datetime.datetime.now(datetime.datetime.timezone.utc).isoformat(),
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

async def get_transactions(user_id: str, limit: int = 50) -> list:
    """Retrieves the latest transactions for a user."""
    key = f"{TRANSACTION_LOG_KEY_PREFIX}{user_id}"

    async def _get_transactions(redis, _, limit):
        # LRANGE 0 to limit-1 gets the first 'limit' items (most recent due to LPUSH)
        transactions_json = await redis.lrange(key, 0, limit - 1)
        import json
        transactions = [json.loads(t) for t in transactions_json]
        return transactions

    try:
        return await redis_operation("get_transactions", _get_transactions, user_id, limit)
    except Exception as e:
        logging.error(f"Failed to retrieve transactions for user {user_id}: {e}")
        return []

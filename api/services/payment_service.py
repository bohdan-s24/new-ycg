import logging
import stripe
from typing import Dict, Any, Optional, List
import json
from datetime import datetime

from ..config import Config
from ..utils.db import get_redis_connection
from . import credits_service

# Remove top-level initialization:
# stripe.api_key = Config.STRIPE_SECRET_KEY 

# Redis key prefixes
PAYMENT_PLANS_KEY = "payment:plans"
CHECKOUT_SESSION_KEY_PREFIX = "checkout:"

# Define the available plans
DEFAULT_PLANS = [
    {
        "id": "free",
        "name": "Free",
        "credits": 3,
        "price": 0,
        "description": "3 free credits after registration"
    },
    {
        "id": "basic",
        "name": "Basic",
        "credits": 10,
        "price": 9,
        "description": "10 credits for $9"
    },
    {
        "id": "premium",
        "name": "Premium",
        "credits": 50,
        "price": 29,
        "description": "50 credits for $29"
    }
]

async def initialize_payment_plans():
    """Initialize the payment plans in Redis if they don't exist."""
    r = await get_redis_connection()
    
    # Check if plans already exist
    plans_exist = await r.exists(PAYMENT_PLANS_KEY)
    if not plans_exist:
        # Store the default plans
        await r.set(PAYMENT_PLANS_KEY, json.dumps(DEFAULT_PLANS))
        logging.info("Initialized default payment plans in Redis")

async def get_payment_plans() -> List[Dict[str, Any]]:
    """Get the available payment plans."""
    r = await get_redis_connection()
    
    # Get plans from Redis
    plans_json = await r.get(PAYMENT_PLANS_KEY)
    if plans_json:
        return json.loads(plans_json)
    
    # If plans don't exist, initialize and return default plans
    await initialize_payment_plans()
    return DEFAULT_PLANS

async def create_checkout_session(user_id: str, plan_id: str, success_url: str, cancel_url: str) -> Optional[Dict[str, Any]]:
    """
    Create a Stripe checkout session for a specific plan.
    
    Args:
        user_id: The ID of the user making the purchase
        plan_id: The ID of the plan being purchased
        success_url: URL to redirect to on successful payment
        cancel_url: URL to redirect to if payment is cancelled
        
    Returns:
        Dictionary with checkout session details or None if error
    """
    try:
        # Get the plan details
        plans = await get_payment_plans()
        plan = next((p for p in plans if p["id"] == plan_id), None)
        
        if not plan:
            logging.error(f"Plan with ID {plan_id} not found")
            return None
            
        # Create a Stripe checkout session
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": f"{plan['name']} - {plan['credits']} Credits",
                            "description": plan["description"],
                        },
                        "unit_amount": int(plan["price"] * 100),  # Convert to cents
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "user_id": user_id,
                "plan_id": plan_id,
                "credits": plan["credits"]
            }
        )
        
        # Store the session in Redis for verification later
        r = await get_redis_connection()
        session_data = {
            "id": session.id,
            "user_id": user_id,
            "plan_id": plan_id,
            "credits": plan["credits"],
            "amount": plan["price"],
            "created_at": datetime.utcnow().isoformat(),
            "status": "pending"
        }
        await r.set(f"{CHECKOUT_SESSION_KEY_PREFIX}{session.id}", json.dumps(session_data))
        
        return {
            "id": session.id,
            "url": session.url
        }
    except Exception as e:
        logging.error(f"Error creating checkout session: {e}")
        return None

async def handle_checkout_completed(session_id: str) -> bool:
    """
    Handle a completed checkout session from Stripe webhook.
    
    Args:
        session_id: The ID of the completed checkout session
        
    Returns:
        True if credits were added successfully, False otherwise
    """
    try:
        # Get the session data from Redis
        r = await get_redis_connection()
        session_data_json = await r.get(f"{CHECKOUT_SESSION_KEY_PREFIX}{session_id}")
        
        if not session_data_json:
            logging.error(f"Checkout session {session_id} not found in Redis")
            return False
            
        session_data = json.loads(session_data_json)
        
        # Verify the session with Stripe
        stripe_session = stripe.checkout.Session.retrieve(session_id)
        
        if stripe_session.payment_status != "paid":
            logging.warning(f"Checkout session {session_id} not paid. Status: {stripe_session.payment_status}")
            return False
            
        # Add credits to the user
        user_id = session_data["user_id"]
        credits = session_data["credits"]
        description = f"Purchase of {credits} credits for ${session_data['amount']}"
        
        new_balance = await credits_service.add_credits(
            user_id, 
            credits, 
            "purchase", 
            description
        )
        
        if new_balance is None:
            logging.error(f"Failed to add credits for user {user_id} after payment")
            return False
            
        # Update session status in Redis
        session_data["status"] = "completed"
        session_data["completed_at"] = datetime.utcnow().isoformat()
        await r.set(f"{CHECKOUT_SESSION_KEY_PREFIX}{session_id}", json.dumps(session_data))
        
        logging.info(f"Successfully added {credits} credits to user {user_id}. New balance: {new_balance}")
        return True
    except Exception as e:
        logging.error(f"Error handling checkout completion: {e}")
        return False

async def get_user_purchases(user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get the purchase history for a user.
    
    Args:
        user_id: The ID of the user
        limit: Maximum number of purchases to return
        
    Returns:
        List of purchase records
    """
    try:
        # Get transactions of type "purchase" from credits service
        transactions = await credits_service.get_transactions(user_id)
        purchases = [t for t in transactions if t["type"] == "purchase"]
        
        # Sort by timestamp (newest first) and limit
        purchases.sort(key=lambda x: x["timestamp"], reverse=True)
        return purchases[:limit]
    except Exception as e:
        logging.error(f"Error getting purchase history for user {user_id}: {e}")
        return []

import logging
import stripe
from typing import Dict, Any, Optional, List
import json
from datetime import datetime

from ..config import Config
from ..utils.db import get_redis_connection
from . import credits_service

# Stripe Product/Price mapping for credits
STRIPE_PRICE_ID_TO_CREDITS = {
    # One-time purchases
    'price_1RHh4dF7Kryr2ZRbrm1f0zt4': 10,   # 10 Credits One-Time ($9)
    'price_1RHh4RF7Kryr2ZRbL5HZLqj8': 50,   # 50 Credits One-Time ($29)
    # Subscriptions (monthly)
    'price_1RHh4dF7Kryr2ZRbZwLlf2bT': 10,   # 10 Credits Recurring ($9/month)
    'price_1RHh4RF7Kryr2ZRbmHnwUnq4': 50,   # 50 Credits Recurring ($29/month)
}

# Stripe API key setup
stripe.api_key = Config.STRIPE_SECRET_KEY

# Redis key prefixes
CHECKOUT_SESSION_KEY_PREFIX = "checkout:"

import asyncio

async def create_checkout_session(user_id: str, price_id: str, mode: str, timeout: int = 30):
    """
    Create a Stripe checkout session for a specific price ID and mode.
    Args:
        user_id: The ID of the user making the purchase.
        price_id: The Stripe Price ID being purchased.
        mode: 'payment' for one-time, 'subscription' for recurring.
        timeout: Timeout for the Stripe API call in seconds.
    Returns:
        Stripe Checkout Session dict (id, url) or None if error.
    """
    try:
        async def create_session():
            return stripe.checkout.Session.create(
                line_items=[{"price": price_id, "quantity": 1}],
                mode=mode,
                success_url=f"https://ycg-frontend.vercel.app/payment-success.html",
                cancel_url=f"https://ycg-frontend.vercel.app/payment-cancel.html",
                client_reference_id=user_id,
            )
        session = await asyncio.wait_for(create_session(), timeout=timeout)
        return {"id": session.id, "url": session.url}
    except asyncio.TimeoutError:
        logging.error("Stripe checkout session creation timed out")
        return None
    except Exception as e:
        logging.error(f"Error creating checkout session: {e}")
        return None

async def handle_webhook_event(event):
    event_type = event['type']
    data_object = event['data']['object']
    logging.info(f"Handling webhook event: {event['id']} ({event_type})")
    if event_type == 'checkout.session.completed':
        session = data_object
        user_id = session.get('client_reference_id')
        price_id = None
        credits = 0
        mode = session.get('mode')
        # For one-time payment, add credits now
        if 'subscription' == mode:
            # For subscriptions, credits are added on invoice.paid
            pass
        else:
            # For one-time payment, add credits now
            if session.get('line_items'):
                price_id = session['line_items'][0]['price']['id']
            if not price_id and session.get('metadata', {}):
                price_id = session['metadata'].get('price_id')
            if not price_id:
                logging.error(f"No price_id found in session {session['id']}")
                return
            credits = STRIPE_PRICE_ID_TO_CREDITS.get(price_id, 0)
            if credits > 0 and user_id:
                await credits_service.add_credits(user_id, credits, "purchase", f"Stripe purchase: {credits} credits")
    elif event_type == 'invoice.paid':
        invoice = data_object
        stripe_customer_id = invoice.get('customer')
        price_id = invoice['lines']['data'][0]['price']['id'] if invoice.get('lines', {}).get('data') else None
        credits = STRIPE_PRICE_ID_TO_CREDITS.get(price_id, 0)
        if credits > 0 and stripe_customer_id:
            from ..services import user_service
            user = await user_service.get_user_by_stripe_customer_id(stripe_customer_id)
            if user:
                await credits_service.add_credits(user.id, credits, "subscription_renewal", f"Stripe subscription renewal: {credits} credits")
    else:
        logging.warning(f"Unhandled webhook event type: {event_type}")

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
        purchases = [t for t in transactions if t["type"] in ["purchase", "subscription_renewal"]]
        
        # Sort by timestamp (newest first) and limit
        purchases.sort(key=lambda x: x["timestamp"], reverse=True)
        return purchases[:limit]
    except Exception as e:
        logging.error(f"Error getting purchase history for user {user_id}: {e}")
        return []

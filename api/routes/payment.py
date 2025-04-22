import logging
import stripe
import json
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, constr, HttpUrl
from ..utils.responses import success_response, error_response
from ..utils.decorators import token_required_fastapi
from ..services import payment_service
from ..config import Config
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi import Limiter
from ..models.user import User

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

class CreateCheckoutSessionRequest(BaseModel):
    price_id: constr(min_length=10)
    mode: str  # 'payment' or 'subscription'

class CheckoutRequest(BaseModel):
    plan_id: constr(min_length=3, max_length=32)
    success_url: HttpUrl
    cancel_url: HttpUrl

@router.get('/plans')
async def get_plans():
    """
    Get available payment plans.
    """
    plans = await payment_service.get_payment_plans()
    return success_response({"plans": plans})

@router.post('/create-checkout-session')
async def create_checkout_session_route(body: CreateCheckoutSessionRequest, user: User = Depends(token_required_fastapi)):
    """
    Create a Stripe Checkout Session for a one-time payment or subscription.
    Requires authentication.
    """
    session = await payment_service.create_checkout_session(
        user_id=user.id,
        price_id=body.price_id,
        mode=body.mode
    )
    if not session:
        return error_response("Failed to create checkout session", 500)
    return success_response({"sessionId": session["id"], "url": session["url"]})

@router.post('/webhook')
async def webhook(request: Request):
    """
    Handle Stripe webhook events.
    """
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    if not sig_header:
        return error_response("Missing Stripe signature", 400)
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, Config.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logging.error(f"Invalid Stripe payload: {e}")
        return error_response("Invalid payload", 400)
    except stripe.error.SignatureVerificationError as e:
        logging.error(f"Invalid Stripe signature: {e}")
        return error_response("Invalid signature", 400)
    # Pass event to service
    try:
        await payment_service.handle_webhook_event(event)
    except Exception as e:
        logging.error(f"Error handling webhook event: {e}")
    return success_response({"received": True})

@router.get('/purchases')
async def get_purchases(user: User = Depends(token_required_fastapi)):
    """
    Get purchase history for the authenticated user.
    """
    purchases = await payment_service.get_user_purchases(user.id)
    return success_response({"purchases": purchases})

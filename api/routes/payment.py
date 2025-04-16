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

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

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

@router.post('/checkout')
@limiter.limit("10/minute")
async def create_checkout(body: CheckoutRequest, user_id: str = Depends(token_required_fastapi)):
    """
    Create a checkout session for a plan.
    Requires authentication.
    """
    checkout_session = await payment_service.create_checkout_session(
        user_id,
        body.plan_id,
        str(body.success_url),
        str(body.cancel_url)
    )
    if not checkout_session:
        return error_response("Failed to create checkout session", 500)
    return success_response(checkout_session)

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
    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        session_id = session['id']
        success = await payment_service.handle_checkout_completed(session_id)
        if success:
            logging.info(f"Successfully processed payment for session {session_id}")
        else:
            logging.error(f"Failed to process payment for session {session_id}")
    return success_response({"received": True})

@router.get('/purchases')
@limiter.limit("10/minute")
async def get_purchases(user_id: str = Depends(token_required_fastapi)):
    """
    Get purchase history for the authenticated user.
    """
    purchases = await payment_service.get_user_purchases(user_id)
    return success_response({"purchases": purchases})

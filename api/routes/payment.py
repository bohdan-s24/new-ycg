import logging
import stripe
import json
from fastapi import APIRouter, Request, Depends
from ..utils.responses import success_response, error_response
from ..utils.decorators import token_required_fastapi
from ..services import payment_service
from ..config import Config

router = APIRouter()

@router.get('/plans')
async def get_plans():
    """
    Get available payment plans.
    """
    try:
        plans = await payment_service.get_payment_plans()
        return success_response({"plans": plans})
    except Exception as e:
        logging.error(f"Error retrieving payment plans: {e}")
        return error_response("Failed to retrieve payment plans.", 500)

@router.post('/checkout')
async def create_checkout(request: Request, user_id: str = Depends(token_required_fastapi)):
    """
    Create a checkout session for a plan.
    Requires authentication.
    """
    try:
        data = await request.json()
        plan_id = data.get('plan_id')
        success_url = data.get('success_url')
        cancel_url = data.get('cancel_url')

        if not plan_id:
            return error_response("Missing plan_id in request", 400)
        if not success_url or not cancel_url:
            return error_response("Missing success_url or cancel_url in request", 400)

        checkout_session = await payment_service.create_checkout_session(
            user_id,
            plan_id,
            success_url,
            cancel_url
        )
        if not checkout_session:
            return error_response("Failed to create checkout session", 500)
        return success_response(checkout_session)
    except Exception as e:
        logging.error(f"Error creating checkout session: {e}")
        return error_response(f"Failed to create checkout session: {str(e)}", 500)

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
async def get_purchases(user_id: str = Depends(token_required_fastapi)):
    """
    Get purchase history for the authenticated user.
    """
    try:
        purchases = await payment_service.get_user_purchases(user_id)
        return success_response({"purchases": purchases})
    except Exception as e:
        logging.error(f"Error retrieving purchase history: {e}")
        return error_response("Failed to retrieve purchase history.", 500)

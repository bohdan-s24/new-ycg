from sanic import Blueprint
from sanic.request import Request
import logging

from ..services import credits_service
from ..utils.decorators import token_required
from ..utils.responses import success_response, error_response

# Create a blueprint
credits_bp = Blueprint('credits', url_prefix='/credits')

@credits_bp.route('/balance')
@token_required
async def get_balance(request: Request):
    """
    Retrieves the credit balance for the authenticated user.
    """
    user_id = getattr(request.ctx, 'current_user_id', None)
    if not user_id:
        logging.error("User ID not found in request.ctx after token_required.")
        return error_response("Authentication error.", 500)
    try:
        balance = await credits_service.get_credit_balance(user_id)
        return success_response({"balance": balance})
    except Exception as e:
        logging.error(f"Error retrieving balance for user {user_id}: {e}")
        return error_response("Failed to retrieve credit balance.", 500)

@credits_bp.route('/transactions')
@token_required
async def get_transaction_history(request: Request):
    """
    Retrieves the transaction history for the authenticated user.
    """
    user_id = getattr(request.ctx, 'current_user_id', None)
    if not user_id:
        logging.error("User ID not found in request.ctx after token_required.")
        return error_response("Authentication error.", 500)
    try:
        transactions = await credits_service.get_transactions(user_id)
        return success_response({"transactions": transactions})
    except Exception as e:
        logging.error(f"Error retrieving transactions for user {user_id}: {e}")
        return error_response("Failed to retrieve transaction history.", 500)

from flask import g # Import g to access user info set by decorator
import logging

from ..services import credits_service
from ..utils.decorators import token_required
from ..utils.responses import success_response, error_response
from ..utils.versioning import VersionedBlueprint

# Create a versioned blueprint
credits_bp = VersionedBlueprint('credits', __name__, url_prefix='/credits')

@credits_bp.route('/balance', methods=['GET'])
@token_required
async def get_balance():
    """
    Retrieves the credit balance for the authenticated user.
    """
    user_id = getattr(g, 'current_user_id', None)
    if not user_id:
        # This shouldn't happen if token_required works correctly, but good practice
        logging.error("User ID not found in g context after token_required.")
        return error_response("Authentication error.", 500)

    try:
        balance = await credits_service.get_credit_balance(user_id)
        return success_response({"balance": balance})
    except Exception as e:
        logging.error(f"Error retrieving balance for user {user_id}: {e}")
        return error_response("Failed to retrieve credit balance.", 500)

@credits_bp.route('/transactions', methods=['GET'])
@token_required
async def get_transaction_history():
    """
    Retrieves the transaction history for the authenticated user.
    """
    user_id = getattr(g, 'current_user_id', None)
    if not user_id:
        logging.error("User ID not found in g context after token_required.")
        return error_response("Authentication error.", 500)

    try:
        # Add optional query parameter for limit later if needed
        transactions = await credits_service.get_transactions(user_id)
        return success_response({"transactions": transactions})
    except Exception as e:
        logging.error(f"Error retrieving transactions for user {user_id}: {e}")
        return error_response("Failed to retrieve transaction history.", 500)

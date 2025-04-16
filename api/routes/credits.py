import logging
from fastapi import APIRouter, Depends, Query, Request
from ..services import credits_service
from ..utils.decorators import token_required_fastapi
from ..utils.responses import success_response, error_response
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi import Limiter
from ..models import User  # Assuming User model is defined in models.py

# Create a router
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

@router.get('/balance')
async def get_balance(request: Request, user: User = Depends(token_required_fastapi)):
    """
    Retrieves the credit balance for the authenticated user.
    """
    balance = await credits_service.get_credit_balance(user.id)
    return success_response({"balance": balance})

@router.get('/transactions')
async def get_transaction_history(
    request: Request,
    user: User = Depends(token_required_fastapi),
    offset: int = Query(0, ge=0, description="Pagination offset (start index)"),
    limit: int = Query(20, ge=1, le=100, description="Page size (max 100)")
):
    """
    Retrieves the transaction history for the authenticated user, paginated.
    """
    transactions, total = await credits_service.get_transactions(user.id, offset=offset, limit=limit)
    return success_response({
        "transactions": transactions,
        "total": total,
        "offset": offset,
        "limit": limit
    })

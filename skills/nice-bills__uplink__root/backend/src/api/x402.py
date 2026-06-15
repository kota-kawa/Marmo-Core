"""x402 Payment API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.payments.x402 import confirm_payment, process_payment


router = APIRouter(prefix="/payments/x402", tags=["x402-payments"])


class PaymentRequest(BaseModel):
    """Request model for x402 payment."""
    amount: float = Field(..., gt=0, description="Payment amount")
    token_type: str = Field(..., min_length=1, max_length=10, description="Token type (e.g., MON, USDC)")
    recipient_address: str = Field(..., min_length=42, max_length=42, description="Recipient wallet address")
    donor_address: str = Field(..., min_length=42, max_length=42, description="Donor wallet address")
    campaign_id: UUID | None = Field(None, description="Optional campaign ID for tracking")


class PaymentResponse(BaseModel):
    """Response model for x402 payment."""
    success: bool
    tx_hash: str | None
    message: str


class PaymentStatusResponse(BaseModel):
    """Response model for payment status check."""
    tx_hash: str
    confirmed: bool
    status: str


@router.post("", response_model=PaymentResponse)
async def create_payment(
    request: PaymentRequest,
    db: AsyncSession = Depends(get_db),
) -> PaymentResponse:
    """
    Process a payment via x402 protocol.
    
    This endpoint initiates a payment through the x402 payment service
    which handles the HTTP 402 payment flow for crypto micropayments.
    """
    try:
        tx_hash = await process_payment(
            amount=request.amount,
            token_type=request.token_type,
            recipient_address=request.recipient_address,
            donor_address=request.donor_address,
        )
        
        return PaymentResponse(
            success=True,
            tx_hash=tx_hash,
            message="Payment processed successfully",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment failed: {str(e)}",
        )


@router.get("/{tx_hash}/status", response_model=PaymentStatusResponse)
async def get_payment_status(tx_hash: str) -> PaymentStatusResponse:
    """
    Check the status of a payment by transaction hash.
    """
    try:
        confirmed = await confirm_payment(tx_hash)
        
        return PaymentStatusResponse(
            tx_hash=tx_hash,
            confirmed=confirmed,
            status="confirmed" if confirmed else "pending",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check payment status: {str(e)}",
        )

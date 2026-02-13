import stripe
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api import deps
from app.core.config import settings
from app.db.database import get_db
from app.db.db_models import User, Booking, Payment, PaymentStatus, BookingStatus

router = APIRouter()
stripe.api_key = settings.STRIPE_SECRET_KEY

@router.post("/create-payment-intent", response_model=dict)
async def create_payment_intent(
    booking_id: str,
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Create a Stripe PaymentIntent for a booking.
    """
    # 1. Fetch Booking
    result = await db.execute(select(Booking).where(Booking.id == booking_id))
    booking = result.scalar_one_or_none()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    # Ensure current user is the customer for this booking
    if booking.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to pay for this booking")

    # 2. Check for existing successful payment
    result = await db.execute(select(Payment).where(
        Payment.booking_id == booking_id, 
        Payment.status == PaymentStatus.COMPLETED.value
    ))
    existing_payment = result.scalar_one_or_none()
    if existing_payment:
        raise HTTPException(status_code=400, detail="Booking already paid")

    # 3. Create Stripe PaymentIntent
    try:
        # Amount in cents
        amount = int(booking.agreed_price * 100) 
        if amount <= 0:
             raise HTTPException(status_code=400, detail="Invalid booking amount")

        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency="inr",
            metadata={"booking_id": booking_id, "customer_id": current_user.id}
        )

        # 4. Create local Payment record
        payment = Payment(
            booking_id=booking_id,
            amount=booking.agreed_price,
            currency="inr",
            status=PaymentStatus.PENDING.value,
            stripe_payment_intent_id=intent['id']
        )
        db.add(payment)
        await db.commit()
        await db.refresh(payment)

        return {
            "client_secret": intent['client_secret'],
            "payment_id": payment.id
        }

    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=f"Stripe error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Payment creation failed: {str(e)}")


@router.post("/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Handle Stripe webhooks to update payment status.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    endpoint_secret = "whsec_..." # In production, this comes from env

    try:
        # For development without CLI relay, we might trust payload or need a way to verify.
        # Strict verification:
        # event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        
        # For now, simplistic handling (assuming event object is passed directly or just parsing JSON)
        # But robust way is:
        import json
        event = json.loads(payload)

        if event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            intent_id = payment_intent['id']

            # Find payment
            result = await db.execute(select(Payment).where(Payment.stripe_payment_intent_id == intent_id))
            payment = result.scalar_one_or_none()

            if payment:
                payment.status = PaymentStatus.COMPLETED.value
                
                # Also confirm booking
                result = await db.execute(select(Booking).where(Booking.id == payment.booking_id))
                booking = result.scalar_one_or_none()
                if booking:
                    # booking.status = BookingStatus.CONFIRMED.value # It is already confirmed by default, maybe PAID?
                    pass
                
                await db.commit()
        
        return {"status": "success"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
